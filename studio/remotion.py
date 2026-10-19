"""Motion scenes (Remotion): code-drawn, animated scenes in the channel's look — free, local, the same in every
language. The case-file card, the verdict stamp, charts that draw themselves, counters, timelines, typed quotes.

A storyboard shot uses one instead of a painting:

  - id: s179
    text: "Verdict: wrong."
    visual: {comp: verdict, word: WRONG, belief: "Eight glasses of water a day"}

The scene's shots become `beats`: the frame where each shot starts, so the card writes "Subject:" exactly when
it is read. Text in the props may be per language ({en: "...", tr: "..."}) or overridden in `i18n: {tr: {...}}`.
The catalogue and every prop: docs/REMOTION.md. The components: remotion/src/comps/.

Steps:
  images   renders a poster frame per motion scene into shots/ (contact sheet, Shorts, end screen)
  render   renders each motion scene as a clip of the scene's real length (+ the cross-fade tail) and uses it
           instead of a still picture. Cached by props + length + component code.
Needs Node.js (https://nodejs.org, `winget install OpenJS.NodeJS.LTS`). The npm packages are installed on first
use (and by `guncelle.bat` when they change); Remotion downloads its own headless Chrome once.
Settings: config.yaml → remotion; look: channel.yaml → remotion (theme, colours).
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from .config import CHANNELS, Config

ROOT = Path(__file__).resolve().parent.parent
RDIR = ROOT / "remotion"
COMPS = ("case-file", "verdict", "bars", "counter", "timeline", "quote")
CHARTLIKE = ("bars", "counter", "timeline")        # get the channel's "chart" sound (pen)
ENGINE_VERSION = "rm1"
POSTER_SECONDS = 7.0
POSTER_HOLD = 4.0  # posters: the shots are spread over POSTER_SECONDS, the still is taken after this much more time,
                   # so the last field / note is fully written in the picture
NODE_HINT = ("Hareketli sahneler için Node.js gerekli. Kur: winget install OpenJS.NodeJS.LTS "
             "(sonra bu pencereyi kapatıp yeniden aç).")


# ------------------------------------------------------------------ storyboard helpers
def comp_of(visual) -> str | None:
    if isinstance(visual, dict) and visual.get("comp") and "prompt" not in visual:
        return str(visual["comp"])
    return None


def is_motion_shot(shot: dict) -> bool:
    return shot.get("engine") == "remotion" or comp_of(shot.get("visual")) is not None


_LANG = re.compile(r"^[a-z]{2}(-[A-Za-z]{2})?$")


def _pick(v, lang: str, primary: str):
    """{en: "...", tr: "..."} → the text for lang (else the primary language's)."""
    if isinstance(v, dict) and v and all(_LANG.match(str(k)) for k in v):
        return v.get(lang, v.get(primary, next(iter(v.values()))))
    if isinstance(v, dict):
        return {k: _pick(x, lang, primary) for k, x in v.items()}
    if isinstance(v, list):
        return [_pick(x, lang, primary) for x in v]
    return v


def _deep_merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = _deep_merge(a.get(k), v) if k in a else v
        return out
    if isinstance(a, list) and isinstance(b, list) and all(isinstance(x, dict) for x in a + b):
        return [_deep_merge(x, y) for x, y in zip(a, b)] + a[len(b):]   # i18n lists patch item by item
    return copy.deepcopy(b)


def scene_props(visual: dict, lang: str, primary: str) -> dict:
    """The component props of a motion visual for one language."""
    v = {k: x for k, x in visual.items() if k not in ("comp", "i18n", "same")}
    if lang != primary and isinstance((visual.get("i18n") or {}).get(lang), dict):
        v = _deep_merge(v, visual["i18n"][lang])
    return _pick(v, lang, primary)


def validate(visual) -> str | None:
    """Problem with a motion visual (unknown component, missing required props), or None."""
    c = comp_of(visual)
    if c is None:
        return None
    if c not in COMPS:
        return f"bilinmeyen hareketli sahne '{c}' (seçenekler: {', '.join(COMPS)})"
    need = {"case-file": ["number"], "bars": ["bars"], "counter": ["value"], "timeline": ["events"],
            "quote": ["text"]}.get(c, [])
    missing = [k for k in need if k not in visual]
    return f"{c}: eksik alan {', '.join(missing)}" if missing else None


# ------------------------------------------------------------------ installation
def node_bin() -> str | None:
    return shutil.which("node")


def installed() -> bool:
    nm = RDIR / "node_modules"
    return (nm / "remotion").exists() and (nm / "@remotion" / "renderer").exists() and (nm / "@remotion" / "bundler").exists()


def available() -> bool:
    return bool(node_bin()) and installed()


def install(quiet: bool = False) -> bool:
    """npm install in remotion/ (first use, or after package.json changed)."""
    npm = shutil.which("npm")
    if not node_bin() or not npm:
        if not quiet:
            print(f"  {NODE_HINT}")
        return False
    print("  hareketli sahneler: Remotion paketleri kuruluyor (bir kerelik, ~1 dk)...")
    r = subprocess.run([npm, "install", "--no-audit", "--no-fund", "--loglevel=error"], cwd=RDIR,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"  [!] npm install başarısız:\n{(r.stderr or r.stdout)[-800:]}")
        return False
    (RDIR / "node_modules" / ".fabrika-package.json").write_bytes((RDIR / "package.json").read_bytes())
    return True


def needs_install() -> bool:
    """Packages missing or package.json changed since the last install."""
    if not installed():
        return True
    stamp = RDIR / "node_modules" / ".fabrika-package.json"
    return stamp.exists() and stamp.read_bytes() != (RDIR / "package.json").read_bytes()


def ensure() -> bool:
    """True when motion scenes can be rendered (installs the packages if Node.js is there)."""
    if not node_bin():
        return False
    if needs_install():
        return install()
    return True


def status() -> tuple[bool, str]:
    if not node_bin():
        return False, NODE_HINT
    if not installed():
        return True, "Node.js var; Remotion paketleri ilk hareketli sahnede kurulacak"
    return True, "Remotion hazır"


_SRC_HASH: str | None = None


def src_hash() -> str:
    """Hash of the component code: a change re-renders every motion scene."""
    global _SRC_HASH
    if _SRC_HASH is None:
        h = hashlib.sha1(ENGINE_VERSION.encode())
        files = [RDIR / "package.json", RDIR / "render.mjs", *sorted((RDIR / "src").rglob("*.ts*"))]
        for f in files:
            if f.exists():
                h.update(f.relative_to(RDIR).as_posix().encode())
                h.update(f.read_bytes())
        _SRC_HASH = h.hexdigest()[:10]
    return _SRC_HASH


# ------------------------------------------------------------------ the channel's look
PRESETS = ("ledger", "museum")             # remotion/src/lib/theme.ts


def theme(cfg: Config, copy_assets: bool = True) -> dict:
    """channel.yaml → remotion: {theme: ledger|museum, ink, accent, wash, wash2, muted, boil, paper, paper_rules, scenes}
    Defaults: ink/accent from the thumbnail look, paper from chart_paper."""
    ch = cfg.get_path("channel") or {}
    rm = dict(ch.get("remotion") or {})
    th = ch.get("thumbnails") or {}
    name = rm.pop("theme", None) or ("ledger" if th.get("paper") else "museum")
    out = {"name": name if name in PRESETS else "ledger"}
    if th.get("ink"):
        out["ink"] = th["ink"]
    if th.get("accent"):
        out["accent"] = th["accent"]
    paper_rel = rm.pop("paper", None) or ch.get("chart_paper")
    for k in ("ink", "accent", "wash", "wash2", "muted", "bg", "boil", "fonts"):
        if k in rm:
            out[k] = rm[k]
    # `paper_rules` = the paper's ruled lines in 1920×1080 px ({first, step, margin}); `scenes` is the motion rules
    pr = rm.get("paper_rules")
    if isinstance(pr, dict) and "step" in pr:
        out["rules"] = pr
    out["paper"] = None
    if paper_rel:
        src = CHANNELS / str(ch.get("id", "")) / str(paper_rel)
        if src.exists():
            digest = hashlib.sha1(src.read_bytes()).hexdigest()[:12]
            name_ = f"_assets/paper-{digest}{src.suffix.lower()}"
            if copy_assets:
                dst = RDIR / "public" / name_
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
            out["paper"] = name_
    return out


def cache_key(visual: dict, cfg: Config) -> dict:
    """What a poster depends on (images/__init__._key)."""
    return {"theme": theme(cfg, copy_assets=False), "src": src_hash()}


# ------------------------------------------------------------------ rendering
def _run(jobs: list[dict], cfg: Config, work: Path) -> set[str]:
    """Runs remotion/render.mjs once for all jobs. Returns the ids that failed."""
    if not jobs:
        return set()
    work.mkdir(parents=True, exist_ok=True)
    spec = {"jobs": jobs, "concurrency": int(cfg.get_path("remotion.concurrency", 0) or 0) or None,
            "browser": str(cfg.get_path("remotion.browser", "") or "") or None}
    jf = work / "remotion_jobs.json"
    jf.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ)
    env.setdefault("REMOTION_DISABLE_TELEMETRY", "1")
    proc = subprocess.Popen([node_bin() or "node", str(RDIR / "render.mjs"), str(jf)], cwd=RDIR, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace")
    ok, failed, tail = set(), set(), []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line.startswith("OK "):
            ok.add(line[3:].strip())
            print(f"  hareketli sahne {len(ok)}/{len(jobs)}: {line[3:].strip()}")
        elif line.startswith("FAIL "):
            failed.add(line.split()[1])
            print(f"  HATA {line[5:]}")
        elif line.startswith("remotion:"):
            print(f"  {line}")
        elif line and "memory" not in line.lower():
            tail.append(line)
    proc.wait()
    missing = {j["id"] for j in jobs} - ok - failed
    if missing:
        print("  [!] Remotion beklenmedik şekilde durdu:\n    " + "\n    ".join(tail[-12:]))
    return failed | missing


def _job(jid: str, visual: dict, lang: str, primary: str, th: dict, out: Path, kind: str, frames: int, fps: int,
         size: tuple[int, int], beats: list[int], hold: int = 0, seed: int = 1, crf: int = 18,
         frame: int | None = None, extra: dict | None = None) -> dict:
    props = {**(extra or {}), **scene_props(visual, lang, primary), "theme": th, "beats": beats, "hold": hold,
             "seed": int(visual.get("seed", seed))}
    j = {"id": jid, "comp": comp_of(visual), "kind": kind, "props": props, "frames": int(frames), "fps": int(fps),
         "width": int(size[0]), "height": int(size[1]), "out": str(out), "crf": int(crf)}
    if frame is not None:
        j["frame"] = int(frame)
    return j


def _key(job: dict) -> str:
    blob = json.dumps({k: job[k] for k in ("comp", "kind", "props", "frames", "fps", "width", "height", "crf")},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha1((blob + src_hash()).encode()).hexdigest()[:12]


def _seed(sid: str, default: int = 1) -> int:
    return int(sid[1:]) % 97 + 1 if sid[1:].isdigit() else default


def scene_item(group: list[dict], timing: dict[str, dict], fps: int, tail: int) -> dict:
    """One motion scene as render and preview both see it: frames per shot exactly as the render cuts them,
    beats = where each shot starts, and the verdict stamp on the spoken word "wrong" (or "right")."""
    per = [max(1, round(timing[s["id"]]["end"] * fps) - round(timing[s["id"]]["start"] * fps)) for s in group]
    beats, acc = [], 0
    for f in per:
        beats.append(acc)
        acc += f
    item = {"head": group[0], "beats": beats, "frames": acc, "tail": tail}
    v = group[0].get("visual") or {}
    if v.get("comp") == "verdict" and "hit" not in v and "hit_beat" not in v:
        from .sound.designer import _word_time      # the stamp lands with the word, like its sound
        for s in group:
            if re.match(r"\s*verdict\b", s.get("text") or "", re.I):
                t0, t1 = timing[s["id"]]["start"], timing[s["id"]]["end"]
                said = _word_time(s, t0, t1, "wrong") or _word_time(s, t0, t1, "right")
                if said is not None:
                    item["extra"] = {"hit": round(said - timing[group[0]["id"]]["start"], 3)}
                break
    return item


def render_settings(cfg: Config) -> tuple[int, int]:
    """(crf, tail) the long-video render uses, so a preview clip is the very clip the render reuses."""
    xfade = int(cfg.get_path("video.xfade_frames", 10)) if cfg.get_path("video.transitions", True) else 0
    return int(cfg.get_path("video.crf", 20)), xfade + 2


def even_beats(n_shots: int, fps: int, seconds: float = POSTER_SECONDS) -> list[int]:
    """Without timing (before voice/align): shots spread evenly over a nominal scene."""
    n = max(1, n_shots)
    return [round(i * seconds * fps / n) for i in range(n)]


def render_scene_clips(project, cfg: Config, scenes: list[dict], fps: int, size: tuple[int, int], crf: int,
                       lang: str) -> dict[str, Path]:
    """scenes: [{head, beats, frames, tail}] → {scene id: mp4}. The clip is `frames + tail` long; the tail holds
    the final state for the cross-fade into the next scene. Cached by props + length + component code."""
    if not scenes:
        return {}
    if not ensure():
        print(f"  [!] {NODE_HINT}\n      Hareketli sahneler bu render'da poster karesi (yoksa metin kartı) olarak duruyor.")
        return {}
    th = theme(cfg)
    primary = project.primary_lang()
    out_dir = project.build / "remotion" / lang
    out_dir.mkdir(parents=True, exist_ok=True)
    todo, result = [], {}
    for k, s in enumerate(scenes):
        head = s["head"]
        j = _job(head["id"], head["visual"], lang, primary, th, out_dir / "x.mp4", "video", s["frames"] + s["tail"],
                 fps, size, s["beats"], hold=s["tail"], seed=_seed(head["id"], k + 1), crf=max(12, crf - 2),
                 extra=s.get("extra"))
        path = out_dir / f"{head['id']}-{_key(j)}.mp4"
        j["out"] = str(path)
        result[head["id"]] = path
        if not path.exists():
            todo.append(j)
    if todo:
        print(f"  hareketli sahneler: {len(todo)} klip üretiliyor ({len(scenes) - len(todo)} önbellekte)...")
        failed = _run(todo, cfg, out_dir)
        for f in failed:
            result.pop(f, None)
    return {k: v for k, v in result.items() if v.exists()}


def render_posters(project, cfg: Config, items: list[tuple[dict, str]], out_dir: Path,
                   size: tuple[int, int] = (1920, 1080)) -> dict[str, str]:
    """items: [(head shot, cache key)] → writes out_dir/<id>.png (the scene's final state). Returns {id: key} done."""
    if not items:
        return {}
    if not ensure():
        print(f"  [!] {NODE_HINT}")
        return {}
    th = theme(cfg)
    fps = int(cfg.get_path("video.fps", 30))
    primary = project.primary_lang()
    shots = project.load_storyboard()["shots"]
    from .images import scene_map
    heads = scene_map(shots)
    jobs, keys = [], {}
    for head, key in items:
        n = sum(1 for s in shots if heads[s["id"]] == head["id"])
        frames = round((POSTER_SECONDS + POSTER_HOLD) * fps)
        jobs.append(_job(head["id"], head["visual"], primary, primary, th, out_dir / f"{head['id']}.png", "still",
                         frames, fps, size, even_beats(n, fps), frame=frames - 1, seed=_seed(head["id"])))
        keys[head["id"]] = key
    print(f"  hareketli sahneler: {len(jobs)} poster karesi")
    failed = _run(jobs, cfg, project.build / "remotion")
    return {k: v for k, v in keys.items() if k not in failed and (out_dir / f"{k}.png").exists()}


def render_vertical(project, cfg: Config, head: dict, out: Path, lang: str | None = None) -> bool:
    """9:16 still of a motion scene for Shorts (the components lay themselves out for a tall page)."""
    if not ensure():
        return False
    fps = int(cfg.get_path("video.fps", 30))
    primary = project.primary_lang()
    frames = round((POSTER_SECONDS + POSTER_HOLD) * fps)
    j = _job(head["id"], head["visual"], lang or primary, primary, theme(cfg), out, "still", frames, fps,
             (1080, 1920), even_beats(1, fps), frame=frames - 1, seed=_seed(head["id"]))
    return not _run([j], cfg, project.build / "remotion") and out.exists()


def preview(project, cfg: Config, only: set[str] | None, lang: str | None = None) -> list[Path]:
    """build/remotion_preview/<id>.mp4 for the chosen motion scenes, with real timing when the voice exists."""
    from .images import scenes as group
    lang = lang or project.primary_lang()
    fps = int(cfg.get_path("video.fps", 30))
    shots = project.load_storyboard()["shots"]
    tp = project.timing_path(lang)
    timing = {t["id"]: t for t in project.read_json(tp)} if tp.exists() else {}
    items = []
    for g in group(shots):
        head = g[0]
        if not is_motion_shot(head) or (only and head["id"] not in only):
            continue
        crf, tail = render_settings(cfg)
        if all(s["id"] in timing for s in g):
            items.append(scene_item(g, timing, fps, tail))     # exactly the clip `render` will use (cached)
        else:
            items.append({"head": head, "beats": even_beats(len(g), fps), "frames": round((POSTER_SECONDS + 2) * fps),
                          "tail": tail})
    if not items:
        raise SystemExit("Seçilen sahnelerde hareketli sahne yok (visual: {comp: ...}).")
    crf, _ = render_settings(cfg)
    clips = render_scene_clips(project, cfg, items, fps, (int(cfg.get_path("video.width", 1920)),
                                                          int(cfg.get_path("video.height", 1080))), crf, lang)
    out_dir = project.build / "remotion_preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    outs = []
    for sid, path in clips.items():
        dst = out_dir / f"{sid}.mp4"
        shutil.copyfile(path, dst)
        outs.append(dst)
    return outs
