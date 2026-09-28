"""Assembly with FFmpeg.

  render_video     long video (16:9): one gently moving clip per shot → concat → narration + music → -14 LUFS
  render_shorts    vertical 9:16 cut-downs: a shot range, blurred backdrop, title band
  compile_videos   long "for sleep" compilation of several finished videos of a channel
  describe         description.txt with chapters (from paragraph timing) + sources
  contact_sheet    grid of shot thumbnails for review
"""
from __future__ import annotations

import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import ASSETS, Config
from .project import Project


def _run(args: list[str]) -> None:
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])


def _font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arialbd.ttf", "arial.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _measure_lufs(path: Path) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    vals = [ln for ln in r.stderr.splitlines() if ln.strip().startswith("I:")]
    return float(vals[-1].split()[1]) if vals else -23.0


def placeholder(text: str, out: Path, size=(1920, 1080)) -> None:
    """A plain card showing the narration text, used when a shot has no image yet."""
    img = Image.new("RGB", size, "#efe6d2")
    d = ImageDraw.Draw(img)
    d.multiline_text((size[0] // 2, size[1] // 2), text, fill="#555", font=_font(64), anchor="mm", align="center")
    img.save(out)


def _camera_modes(shots: list[dict], cfg: Config) -> list[str]:
    """Explicit shot.camera wins. Otherwise the zoom direction stays the same within a run of shots on one
    background (no jitter across continuity cuts) and alternates when the scene changes. Chart shots hold still."""
    from .fx import animated_visuals
    start = object()
    modes, cur, prev_bg = [], "out", start
    for s in shots:
        v = s.get("visual")
        bg = v.get("bg") if isinstance(v, dict) else None
        if bg != prev_bg:
            cur = "in" if (cur == "out" or prev_bg is start) else "out"
            prev_bg = bg
        cam = (s.get("camera") or {}).get("zoom") if isinstance(s.get("camera"), dict) else s.get("camera")
        if cam in ("in", "out", "none"):
            modes.append(cam)
        elif animated_visuals(v):
            modes.append("none")
        else:
            modes.append(cur)
    return modes


def _zexpr(mode: str, zoom: float, frames: int) -> str:
    n = max(frames - 1, 1)
    if mode == "in":
        return f"1+{zoom}*(1-pow(1-on/{n},2))"          # eased
    if mode == "out":
        return f"1+{zoom}-{zoom}*(1-pow(1-on/{n},2))"
    return "1"


def _end_zoom(mode: str, zoom: float) -> str:
    return str(1 + zoom) if mode == "in" else "1"


def _clip(img: Path, out: Path, frames: int, fps: int, zoom: float, mode: str, w: int, h: int, crf: int,
          prev: Path | None = None, prev_mode: str = "none", anim: list[Path] | None = None, xfade: int = 0) -> None:
    """One clip per shot. Optional: a short cross-fade from the previous shot (continuity runs) and a chart
    intro sequence (anim frames) before the hold."""
    zoom = zoom if mode != "none" else 0
    args, graph, inputs = [], [], 0

    def still(path: Path, z: str, d: int) -> str:
        nonlocal inputs
        args.extend(["-loop", "1", "-framerate", "1", "-t", "1", "-i", str(path)])
        i = inputs
        inputs += 1
        graph.append(f"[{i}:v]scale={w * 2}:{h * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                     f":d={d}:s={w}x{h}:fps={fps},setsar=1,format=yuv420p[s{i}]")
        return f"[s{i}]"

    anim = [a for a in (anim or []) if a.exists()]
    use_x = prev is not None and xfade > 0 and frames > xfade * 2
    frames_out = frames
    frames = frames + (1 if use_x else 0)       # xfade drops one frame; -frames:v below keeps the exact length
    if anim and frames > len(anim) + 2:
        lst = out.with_suffix(".anim.txt")
        lst.write_text("".join(f"file '{a.resolve().as_posix()}'\nduration {1 / fps:.5f}\n" for a in anim)
                       + f"file '{anim[-1].resolve().as_posix()}'\n")
        args.extend(["-f", "concat", "-safe", "0", "-i", str(lst)])
        i = inputs
        inputs += 1
        graph.append(f"[{i}:v]fps={fps},scale={w}:{h},setsar=1,format=yuv420p,trim=end_frame={len(anim)}[a{i}]")
        hold = still(img, "1", frames - len(anim))
        graph.append(f"[a{i}]{hold}concat=n=2:v=1[main]")
    else:
        m = still(img, _zexpr(mode, zoom, frames), frames)
        graph.append(f"{m}null[main]")
    last = "[main]"
    if use_x:
        p = still(prev, _end_zoom(prev_mode, zoom), xfade + 1)
        graph.append(f"{p}settb=AVTB,fps={fps}[pp];{last}settb=AVTB,fps={fps}[mm];"
                     f"[pp][mm]xfade=transition=fade:duration={xfade / fps:.4f}:offset=0[xf]")
        last = "[xf]"
    _run([*args, "-filter_complex", ";".join(graph), "-map", last, "-frames:v", str(frames_out), "-r", str(fps),
          "-c:v", "libx264", "-preset", "veryfast", "-tune", "animation", "-crf", str(crf), "-pix_fmt", "yuv420p",
          str(out)])


def _mix_and_mux(silent: Path, narration: Path, out: Path, cfg: Config, work: Path, start: float = 0.0,
                 duration: float | None = None, total: float | None = None, sfx: Path | None = None) -> None:
    """Narration (+ music ducked under the voice, + sound effects) → exact loudness → true-peak limit → mux."""
    mixed = work / "mix.wav"
    lufs = float(cfg.get_path("audio.target_lufs", -14))
    music_name = cfg.get_path("audio.music", "") or ""
    music = ASSETS / "music" / music_name if music_name else None
    trim = ["-ss", f"{start:.3f}"] + (["-t", f"{duration:.3f}"] if duration else [])
    comp = "acompressor=threshold=-20dB:ratio=3:attack=5:release=120"
    pad = f",apad=whole_dur={total:.3f}" if total else ""
    inputs = [*trim, "-i", str(narration)]
    chains = [f"[0:a]{comp},aresample=48000{pad},asplit=2[v][key]"]
    mixes = ["[v]"]
    n, key_used = 1, False
    if music and music.exists():
        vol = float(cfg.get_path("audio.music_volume", 0.07))
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        if cfg.get_path("audio.duck", True):
            chains.append(f"[{n}:a]aresample=48000,volume={vol * 2.2:.3f}[m0];"
                          f"[m0][key]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=450[m]")
            key_used = True
        else:
            chains.append(f"[{n}:a]aresample=48000,volume={vol}[m]")
        mixes.append("[m]")
        n += 1
    if sfx and sfx.exists():
        inputs += ["-i", str(sfx)]
        chains.append(f"[{n}:a]aresample=48000,volume={float(cfg.get_path('audio.sfx_volume', 0.35)):.3f}[fx]")
        mixes.append("[fx]")
        n += 1
    if not key_used:
        chains.append("[key]anullsink")
    if len(mixes) == 1:
        graph = ";".join(chains) + ";[v]anull[a]"
    else:
        graph = ";".join(chains) + f";{''.join(mixes)}amix=inputs={len(mixes)}:duration=first:dropout_transition=0:normalize=0[a]"
    if total:
        graph = graph[:-3] + f",afade=t=out:st={max(0.0, total - 1.5):.3f}:d=1.5[a]"
    _run([*inputs, "-filter_complex", graph, "-map", "[a]", "-ar", "48000", str(mixed)])
    gain = lufs - _measure_lufs(mixed)
    _run(["-i", str(silent), "-i", str(mixed), "-filter_complex",
          f"[1:a]volume={gain:.2f}dB,alimiter=limit=0.84:level=false[a]",
          "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])


def _frames(timing: list[dict], fps: int) -> list[int]:
    return [max(1, round(t["end"] * fps) - round(t["start"] * fps)) for t in timing]


def _overlay_for(shot: dict, auto: dict) -> dict | None:
    return shot.get("overlay") or auto.get(shot["id"])


def outro_image(project: Project, cfg: Config, lang: str, size=(1920, 1080)) -> Path | None:
    oc = cfg.get_path("channel.outro") or {}
    if oc.get("enabled") is False or float(oc.get("seconds", 18) or 0) <= 0:
        return None
    from .fx import draw_outro, outro_visual
    from .images.svg_engine import SvgEngine
    from .svgkit import render_svg
    from .svgkit.style import use_palette
    base = project.build / "outro_base.png"
    if not base.exists():
        with SvgEngine(cfg) as eng, use_palette(cfg.get_path("channel.style.palette") or {}):
            eng.svg_to_png(render_svg(outro_visual(cfg.get_path("channel.mascot") or {})), base)
    def pick(v, default):
        if isinstance(v, dict):
            return v.get(lang) or v.get(project.primary_lang()) or default
        return v or default
    text = pick(oc.get("text"), {"tr": "Sıradaki video"}.get(lang, "Watch next"))
    sub = pick(oc.get("sub"), cfg.get_path("channel.name", ""))
    out = project.lang_dir(lang) / "outro.png"
    draw_outro(Image.open(base), text, sub).resize(size).save(out)
    return out


def render_video(project: Project, cfg: Config, lang: str | None = None) -> Path:
    from .fx import apply_overlay, auto_overlays, build_sfx_track, sfx_events
    lang = lang or project.primary_lang()
    primary = project.primary_lang()
    shots = {s["id"]: s for s in project.load_storyboard()["shots"]}
    tpath = project.timing_path(lang)
    if not tpath.exists():
        raise SystemExit(f"[{lang}] zamanlama yok. Önce 'voice' ve 'align' adımlarını çalıştır.")
    timing = project.read_json(tpath)
    fps = int(cfg.get_path("video.fps", 30))
    w, h = int(cfg.get_path("video.width", 1920)), int(cfg.get_path("video.height", 1080))
    zoom = float(cfg.get_path("video.zoom", 0.06))
    crf = int(cfg.get_path("video.crf", 20))
    xfade = int(cfg.get_path("video.xfade_frames", 6)) if cfg.get_path("video.transitions", True) else 0
    work = project.lang_dir(lang) / "clips"
    work.mkdir(exist_ok=True)
    ordered = [shots[t["id"]] for t in timing]
    modes = _camera_modes(ordered, cfg)
    auto = auto_overlays(project)

    jobs, prev_img, prev_bg = [], None, None
    for i, (t, frames) in enumerate(zip(timing, _frames(timing, fps))):
        shot = shots[t["id"]]
        img = project.shots_dir / f"{t['id']}.png"
        if not img.exists():
            img = work / f"{t['id']}_placeholder.png"
            placeholder(shot["text"], img, (w, h))
        ov = _overlay_for(shot, auto)
        img_ov = apply_overlay(img, ov, lang, primary, work / f"{t['id']}_ov.png")
        anim = sorted(project.shots_dir.glob(f"{t['id']}_a[0-9][0-9].png"))
        if ov and anim:
            anim = [apply_overlay(a, ov, lang, primary, work / f"{a.stem}_ov.png") for a in anim]
        v = shot.get("visual")
        bg = v.get("bg") if isinstance(v, dict) else None
        same_scene = i > 0 and bg is not None and bg == prev_bg
        jobs.append(dict(img=img_ov, out=work / f"{i:04d}.mp4", frames=frames, mode=modes[i], anim=anim,
                         prev=prev_img if same_scene else None, prev_mode=modes[i - 1] if i else "none"))
        prev_img, prev_bg = img_ov, bg

    outro = outro_image(project, cfg, lang, (w, h))
    outro_frames = int(float(cfg.get_path("channel.outro.seconds", 18) or 18) * fps) if outro else 0
    if outro:
        jobs.append(dict(img=outro, out=work / f"{len(jobs):04d}.mp4", frames=outro_frames, mode="in", anim=[],
                         prev=None, prev_mode="none"))

    print(f"  [{lang}] {len(jobs)} klip hazırlanıyor...")
    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        for _ in ex.map(lambda j: _clip(j["img"], j["out"], j["frames"], fps, zoom * (0.5 if j is jobs[-1] and outro else 1),
                                        j["mode"], w, h, crf, j["prev"], j["prev_mode"], j["anim"], xfade), jobs):
            done += 1
            if done % 25 == 0 or done == len(jobs):
                print(f"  klip {done}/{len(jobs)}")
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{j['out'].name}'\n" for j in jobs))
    silent = work / "video_silent.mp4"
    _run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)])
    total = sum(_frames(timing, fps)) / fps + outro_frames / fps
    sfx = None
    if cfg.get_path("audio.sfx", True):
        sfx = build_sfx_track(sfx_events(ordered, timing), total, ASSETS, work / "sfx.wav")
    out = project.video_path(lang)
    _mix_and_mux(silent, project.audio_dir(lang) / "narration.wav", out, cfg, work, total=total, sfx=sfx)
    describe(project, cfg, lang)
    print(f"  video hazır: {out} ({total:.0f} sn{', kapanış ' + str(outro_frames // fps) + ' sn' if outro else ''})")
    return out


# ---------------------------------------------------------------- shorts
def _cover(img: Image.Image, W: int, H: int) -> Image.Image:
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)))
    l, t = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((l, t, l + W, t + H))


def _short_frame_fallback(img_path: Path, out: Path, size=(1080, 1920)) -> None:
    """For AI (gemini) shots without a vector recipe: blurred cover + centred 4:3 crop."""
    W, H = size
    src = Image.open(img_path).convert("RGB")
    canvas = _cover(src, W, H).filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * 0.72))
    cw = min(src.width, round(src.height * 4 / 3))
    left = (src.width - cw) // 2
    fg = src.crop((left, 0, left + cw, src.height)).resize((W, round(src.height * W / cw)))
    canvas.paste(fg, (0, (H - fg.height) // 2))
    canvas.save(out)


def render_shorts(project: Project, cfg: Config, lang: str | None = None) -> list[Path]:
    """project.yaml → shorts: [{title: "...", from: s012, to: s030, hook: "optional first line on screen"}].
    Drawings are re-rendered natively in 9:16 (vector crop around the action) with burned-in captions."""
    from .fx import caption_frame, focus_x
    from .images.svg_engine import SvgEngine
    from .project import shot_text
    from .svgkit import crop_vertical, render_svg
    from .svgkit.style import use_palette
    lang = lang or project.primary_lang()
    cuts = project.meta.get("shorts") or []
    if not cuts:
        raise SystemExit("project.yaml → shorts listesi boş. Örnek: shorts: [{title: 'Hook', from: s001, to: s018}]")
    timing = project.read_json(project.timing_path(lang))
    ids = [t["id"] for t in timing]
    shots = {s["id"]: s for s in project.load_storyboard()["shots"]}
    fps = int(cfg.get_path("video.fps", 30))
    out_dir = project.lang_dir(lang) / "shorts"
    out_dir.mkdir(exist_ok=True)
    vdir = project.build / "shots_9x16"
    vdir.mkdir(exist_ok=True)
    made = []
    palette = cfg.get_path("channel.style.palette") or {}
    with SvgEngine(cfg) as eng:
        for n, cut in enumerate(cuts, 1):
            if cut.get("from") not in ids or cut.get("to") not in ids:
                print(f"  short {n}: {cut.get('from')}–{cut.get('to')} bulunamadı (atlandı)")
                continue
            a, b = ids.index(cut["from"]), ids.index(cut["to"])
            seg = timing[a:b + 1]
            work = out_dir / f"work{n}"
            work.mkdir(exist_ok=True)
            base = seg[0]["start"]
            rel = [{"id": t["id"], "start": t["start"] - base, "end": t["end"] - base} for t in seg]
            rel[-1]["end"] = min(rel[-1]["end"], rel[-1]["start"] + 3.0)
            total = rel[-1]["end"]
            if total > 60:
                print(f"  uyarı: short {n} {total:.0f} sn (60 sn üstü Shorts sayılmayabilir)")
            clips = []
            for i, (t, frames) in enumerate(zip(rel, _frames(rel, fps))):
                shot = shots[t["id"]]
                v = shot.get("visual")
                vert = vdir / f"{t['id']}.png"
                src16 = project.shots_dir / f"{t['id']}.png"
                if isinstance(v, dict) and any(k in v for k in ("bg", "figures", "props")):
                    stale = not vert.exists() or (src16.exists() and vert.stat().st_mtime < src16.stat().st_mtime)
                    if stale:
                        vis = {k: x for k, x in v.items() if k != "frame"}
                        with use_palette(palette):
                            svg = crop_vertical(render_svg(vis), focus_x(v))
                        eng.svg_to_png(svg, vert, size=(1080, 1920))
                else:
                    src = project.shots_dir / f"{t['id']}.png"
                    if not src.exists():
                        placeholder(shot["text"], work / f"{t['id']}_ph.png")
                        src = work / f"{t['id']}_ph.png"
                    _short_frame_fallback(src, vert)
                title = cut.get("hook") if (cut.get("hook") and t["start"] < 2.5) else cut.get("title", "")
                frame = work / f"{t['id']}.png"
                caption_frame(Image.open(vert), title, shot_text(shot, lang, project.primary_lang())).save(frame)
                clip = work / f"{i:04d}.mp4"
                _clip(frame, clip, frames, fps, float(cfg.get_path("video.zoom", 0.06)), "in", 1080, 1920, 21)
                clips.append(clip)
            (work / "list.txt").write_text("".join(f"file '{c.name}'\n" for c in clips))
            silent = work / "silent.mp4"
            _run(["-f", "concat", "-safe", "0", "-i", str(work / "list.txt"), "-c", "copy", str(silent)])
            out = out_dir / f"short{n:02d}.mp4"
            _mix_and_mux(silent, project.audio_dir(lang) / "narration.wav", out, cfg, work, start=base, duration=total)
            made.append(out)
            print(f"  short hazır: {out.name} ({total:.0f} sn, dikey çizim + altyazı)")
    return made


# ---------------------------------------------------------------- compilation
def compile_videos(channel: str, slugs: list[str], cfg: Config, lang: str, title: str) -> Path:
    """Joins finished videos (same language) into one long upload, e.g. a 1-2 h 'for sleep' version."""
    from .channel import Channel
    ch = Channel(channel)
    out_dir = ch.dir / "compilations"
    out_dir.mkdir(exist_ok=True)
    vids = [Project(channel, s).video_path(lang) for s in slugs]
    missing = [str(v) for v in vids if not v.exists()]
    if missing:
        raise SystemExit(f"Önce bu videoları üret: {missing}")
    safe = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "compilation"
    lst = out_dir / f"{safe}.txt"
    lst.write_text("".join(f"file '{v.resolve().as_posix()}'\n" for v in vids))
    out = out_dir / f"{safe}.{lang}.mp4"
    _run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out)])
    t, lines = 0.0, []
    for s, v in zip(slugs, vids):
        lines.append(f"{_ts(t)} {Project(channel, s).meta.get('title', s)}")
        t += _duration(v)
    (out_dir / f"{safe}.{lang}.chapters.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"  derleme hazır: {out} ({t / 60:.0f} dk)")
    return out


def _duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def _ts(sec: float) -> str:
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ---------------------------------------------------------------- description
def describe(project: Project, cfg: Config, lang: str | None = None) -> Path:
    """description.txt: title, chapters (project.yaml chapters: {paragraph index: label}) and sources."""
    lang = lang or project.primary_lang()
    sb = project.load_storyboard()
    timing = {t["id"]: t for t in project.read_json(project.timing_path(lang))}
    meta = project.meta
    chapters = meta.get("chapters") or {}
    lines = [meta.get("title", project.slug), ""]
    if (meta.get("description") or "").strip():
        lines += [meta["description"].strip(), ""]
    seen, chap, last = set(), [], -99.0
    for s in sb["shots"]:
        if s["para"] in seen or s["id"] not in timing:
            continue
        seen.add(s["para"])
        label = chapters.get(s["para"]) or chapters.get(str(s["para"]))
        if isinstance(label, dict):                    # {en: "...", tr: "..."}
            label = label.get(lang) or next(iter(label.values()), "")
        start = timing[s["id"]]["start"]
        if label and (start - last >= 10 or not chap):  # YouTube rejects chapters shorter than 10 s
            chap.append(f"{_ts(start)} {label}")
            last = start
    if len(chap) >= 3:
        if not chap[0].startswith("0:00 "):
            chap.insert(0, "0:00 Intro")
        lines += ["Chapters:", *chap, ""]
    from .claims import cited_sources, format_source
    cited = cited_sources(project)
    src = "" if cited else (project.sources_path.read_text(encoding="utf-8") if project.sources_path.exists() else "")
    links, head = [format_source(s) for s in cited], ""
    for ln in src.splitlines():
        raw = ln.strip()
        if not raw or raw.startswith(("#", "<!--")):
            continue
        is_item = raw.startswith(("-", "*"))
        t = raw.lstrip("-* ").replace("*", "").strip()
        if is_item:
            head = t
        if "http" in t:
            if t.startswith("http") and head and head != t:
                t = f"{head.split(' — ')[0].split(' - ')[0].strip()}: {t}"
            links.append(t)
            head = ""
    if links:
        lines += ["Sources:", *[f"- {ln}" for ln in links], ""]
    out = project.lang_dir(lang) / "description.txt"
    out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    write_srt(project, lang)
    return out


def _srt_ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(project: Project, lang: str | None = None, max_chars: int = 84, max_dur: float = 6.0) -> Path:
    """captions.<lang>.srt from shot timing: upload to YouTube (accessibility + search), burn into Shorts."""
    from .project import shot_text
    lang = lang or project.primary_lang()
    shots = {s["id"]: s for s in project.load_storyboard()["shots"]}
    timing = project.read_json(project.timing_path(lang))
    cues, cur = [], None
    for t in timing:
        text = shot_text(shots[t["id"]], lang, project.primary_lang()).strip()
        if cur and (len(cur["text"]) + 1 + len(text) <= max_chars and t["end"] - cur["start"] <= max_dur
                    and not cur["text"].endswith((".", "!", "?"))):
            cur["text"] += " " + text
            cur["end"] = t["end"]
        else:
            if cur:
                cues.append(cur)
            cur = {"start": t["start"], "end": t["end"], "text": text}
    if cur:
        cues.append(cur)
    audio_end = timing[-1]["end"] - 0.6 if timing else 0
    blocks = []
    for i, c in enumerate(cues, 1):
        text = c["text"]
        if len(text) > 42:                              # two balanced lines
            words, best = text.split(), None
            for k in range(1, len(words)):
                a, b = " ".join(words[:k]), " ".join(words[k:])
                score = max(len(a), len(b))
                if best is None or score < best[0]:
                    best = (score, f"{a}\n{b}")
            text = best[1] if best else text
        end = min(c["end"], max(audio_end, c["start"] + 0.5)) if i == len(cues) else c["end"]
        blocks.append(f"{i}\n{_srt_ts(c['start'])} --> {_srt_ts(end)}\n{text}\n")
    out = project.lang_dir(lang) / f"captions.{lang}.srt"
    out.write_text("\n".join(blocks), encoding="utf-8")
    return out


def contact_sheet(project: Project, cols: int = 6, limit: int = 400) -> Path:
    shots = project.load_storyboard()["shots"][:limit]
    tw, th = 320, 180
    rows = max(1, (len(shots) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 30)), "white")
    d = ImageDraw.Draw(sheet)
    font = _font(16)
    for i, s in enumerate(shots):
        x, y = (i % cols) * tw, (i // cols) * (th + 30)
        p = project.shots_dir / f"{s['id']}.png"
        if p.exists():
            sheet.paste(Image.open(p).convert("RGB").resize((tw, th)), (x, y))
        else:
            d.rectangle([x, y, x + tw - 1, y + th - 1], fill="#eee")
        d.text((x + 6, y + th + 6), f"{s['id']} {s['text'][:32]}", fill="black", font=font)
    out = project.build / "contact_sheet.png"
    sheet.save(out)
    return out
