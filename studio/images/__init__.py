"""Renders one PNG per scene.

A scene starts at a shot with its own visual and runs over the following shots whose visual is
`{same: true}`: they share the image while the camera keeps moving (6-8 s per picture instead of 2 s).

  gemini  AI illustration from visual.prompt (+ characters, + ref)  — the default
  svg     code-drawn chart from a recipe {bg, props: [{type: bar_chart, ...}]} — numbers as pictures

Results are cached by content hash: a scene is only re-rendered when its prompt/recipe or the engine
settings change, so re-running never re-spends money on unchanged scenes.
"""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

from ..config import Config
from ..project import Project
from .style_prompt import build_prompt


def is_same(visual) -> bool:
    return isinstance(visual, dict) and bool(visual.get("same"))


def drop_orphans(shots: list[dict]) -> int:
    """A `{same: true}` with no picture before it (its scene's first shot changed or lost its plan) becomes
    unplanned again, so the planner picks it up. Returns how many were reset."""
    n, has_picture = 0, False
    for s in shots:
        v = s.get("visual")
        if is_same(v):
            if not has_picture:
                s["visual"] = None
                n += 1
        else:
            has_picture = bool(v)
    return n


def scene_map(shots: list[dict]) -> dict[str, str]:
    """shot id → id of the shot whose image it shows (itself, or the head of its scene)."""
    out, head = {}, None
    for s in shots:
        v = s.get("visual")
        if is_same(v) and head:
            out[s["id"]] = head
        else:
            head = s["id"] if v and not is_same(v) else None
            out[s["id"]] = s["id"]
    return out


def scenes(shots: list[dict]) -> list[list[dict]]:
    """Consecutive shots grouped by the image they share."""
    m, groups = scene_map(shots), []
    for s in shots:
        if groups and m[s["id"]] == m[groups[-1][0]["id"]] and m[s["id"]] != s["id"]:
            groups[-1].append(s)
        else:
            groups.append([s])
    return groups


def engine_name(shot: dict, cfg: Config) -> str:
    """Explicit shot.engine wins; a chart recipe (bg/props) is svg; a prompt is gemini."""
    if shot.get("engine"):
        return shot["engine"]
    v = shot.get("visual")
    if isinstance(v, dict) and any(k in v for k in ("bg", "props", "figures")) and "prompt" not in v:
        return "svg"
    return "gemini"


def _key(shot: dict, engine: str, cfg: Config) -> str:
    payload = {"engine": engine, "visual": shot.get("visual")}
    if engine == "svg":
        payload["palette"] = cfg.get_path("channel.style.palette") or {}
        payload["paper"] = cfg.get_path("channel.chart_paper") or ""
    if engine == "gemini":
        payload["model"] = cfg.get_path("images.gemini.model")
        payload["size"] = cfg.get_path("images.gemini.image_size", "")
        payload["prompt"] = build_prompt(shot.get("visual"), cfg.get_path("channel.visual_style", ""),
                                         cfg.get_path("channel.characters") or {})
    return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12]


def forget_image(project: Project, sid: str) -> None:
    """Delete a scene's picture (and chart intro frames) after its plan changed, so nothing stale is shown."""
    d = project.shots_dir
    for f in [d / f"{sid}.png", d / f"{sid}.svg", *d.glob(f"{sid}_a[0-9][0-9].png")]:
        f.unlink(missing_ok=True)


def prune_stale(project: Project, cfg: Config, shots: list[dict], index: dict) -> int:
    """Remove pictures that no longer belong to a scene's current plan (old plans, merged scenes)."""
    heads = scene_map(shots)
    by_id = {s["id"]: s for s in shots}
    n = 0
    for png in project.shots_dir.glob("s[0-9][0-9][0-9].png"):
        sid = png.stem
        shot = by_id.get(sid)
        ok = (shot is not None and heads[sid] == sid and shot.get("visual") and not is_same(shot["visual"])
              and index.get(sid) == _key(shot, engine_name(shot, cfg), cfg))
        if not ok:
            forget_image(project, sid)
            index.pop(sid, None)
            n += 1
    return n


def render_images(project: Project, cfg: Config, only: set[str] | None = None, force: bool = False) -> dict:
    shots = project.load_storyboard()["shots"]
    heads = scene_map(shots)
    out_dir = project.shots_dir
    index_path = out_dir / "index.json"
    index = project.read_json(index_path) if index_path.exists() else {}
    if prune_stale(project, cfg, shots, index):
        project.write_json(index_path, index)
    if only:                                   # asking for any shot of a scene re-renders the scene image
        only = {heads.get(i, i) for i in only}

    todo: dict[str, list[tuple[dict, str]]] = {"svg": [], "gemini": []}
    missing = []
    for shot in shots:
        if heads[shot["id"]] != shot["id"]:
            continue
        if only and shot["id"] not in only:
            continue
        if not shot.get("visual") or is_same(shot.get("visual")):
            missing.append(shot["id"])
            continue
        eng = engine_name(shot, cfg)
        key = _key(shot, eng, cfg)
        png = out_dir / f"{shot['id']}.png"
        if not force and png.exists() and index.get(shot["id"]) == key:
            continue
        todo.setdefault(eng, []).append((shot, key))

    if missing:
        print(f"  uyarı: {len(missing)} sahnenin görsel planı yok (ilk: {missing[0]}) → metin kartı kullanılacak")

    done, failed = 0, []
    if todo.get("svg"):
        from .svg_engine import SvgEngine
        with SvgEngine(cfg) as eng:
            for shot, key in todo["svg"]:
                eng.render(shot, out_dir / f"{shot['id']}.png", seed=int(shot["id"][1:]) % 50 + 1)
                index[shot["id"]] = key
                done += 1
                project.write_json(index_path, index)
    if todo.get("gemini"):
        from .gemini_engine import GeminiEngine
        eng = GeminiEngine(cfg)
        workers = int(cfg.get_path("images.concurrency", 4))
        print(f"  gemini: {len(todo['gemini'])} sahne çiziliyor ({eng.model})")

        def job(item):
            shot, key = item
            try:
                eng.render(shot, out_dir / f"{shot['id']}.png", out_dir)
                return shot["id"], key, None
            except RuntimeError as e:
                return shot["id"], key, str(e)

        # scenes that use another scene as reference wait until that one is drawn
        pending = list(todo["gemini"])
        pending_ids = {s["id"] for s, _ in pending}
        while pending:
            ready = [it for it in pending if (it[0]["visual"] or {}).get("ref") not in pending_ids]
            if not ready:
                ready = pending
            with ThreadPoolExecutor(max_workers=workers) as ex:
                for sid, key, err in ex.map(job, ready):
                    pending_ids.discard(sid)
                    if err:
                        failed.append(err)
                        print(f"  HATA {err}")
                        continue
                    index[sid] = key
                    done += 1
                    project.write_json(index_path, index)
                    print(f"  gemini: {sid} hazır")
            pending = [it for it in pending if it not in ready]
    total = sum(len(v) for v in todo.values())
    n_scenes = sum(1 for s in shots if heads[s["id"]] == s["id"])
    drawn = sum(1 for s in shots if heads[s["id"]] == s["id"] and (out_dir / f"{s['id']}.png").exists())
    print(f"  resimler: {done}/{total} yeni çizildi · {drawn}/{n_scenes} sahnenin resmi hazır "
          f"({len(shots)} cümle parçası)")
    if failed:
        raise SystemExit(f"{len(failed)} sahne üretilemedi. Bunları düzeltip tekrar çalıştır (hazır olanlar korunur).")
    return index
