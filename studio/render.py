"""Assembly with FFmpeg.

  render_video     long video (16:9): one picture per scene with one continuous camera move (zoom or pan) across
                   all of the scene's shots, cross-fades between scenes → narration + music → -14 LUFS
  render_shorts    vertical 9:16 cut-downs: a shot range, blurred backdrop, title band
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
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
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
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    vals = [ln for ln in r.stderr.splitlines() if ln.strip().startswith("I:")]
    return float(vals[-1].split()[1]) if vals else -23.0


def placeholder(text: str, out: Path, size=(1920, 1080)) -> None:
    """A plain card showing the narration text, used when a shot has no image yet."""
    img = Image.new("RGB", size, "#efe6d2")
    d = ImageDraw.Draw(img)
    d.multiline_text((size[0] // 2, size[1] // 2), text, fill="#555", font=_font(64), anchor="mm", align="center")
    img.save(out)


CAMERA_CYCLE = ("in", "right", "out", "left")


def _scene_modes(groups: list[list[dict]]) -> list[str]:
    """One camera move per scene. Explicit `camera` on the scene's first shot wins; charts hold still;
    otherwise the moves rotate (in → pan right → out → pan left) so consecutive pictures never move alike."""
    from .fx import animated_visuals
    from .images import engine_name
    modes, k = [], 0
    for g in groups:
        head = g[0]
        cam = head.get("camera")
        cam = cam.get("zoom") if isinstance(cam, dict) else cam
        v = head.get("visual")
        if cam in ("in", "out", "left", "right", "none"):
            modes.append(cam)
        elif animated_visuals(v) or (isinstance(v, dict) and engine_name(head, Config()) == "svg"):
            modes.append("none")
        else:
            modes.append(CAMERA_CYCLE[k % len(CAMERA_CYCLE)])
            k += 1
    return modes


def _cam_expr(mode: str, zoom: float, start: int, total: int) -> tuple[str, str, str]:
    """zoompan z/x/y for frames [start, ...) of a scene that lasts `total` frames: the move is continuous over
    the whole scene even though every shot inside it is a separate clip. Eased in and out (smoothstep)."""
    n = max(total - 1, 1)
    p = f"min(1,({start}+on)/{n})"
    s = f"({p})*({p})*(3-2*({p}))"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if mode == "in":
        return f"1+{zoom}*{s}", cx, cy
    if mode == "out":
        return f"1+{zoom}-{zoom}*{s}", cx, cy
    if mode == "right":
        return f"{1 + zoom}", f"(iw-iw/zoom)*{s}", cy
    if mode == "left":
        return f"{1 + zoom}", f"(iw-iw/zoom)*(1-{s})", cy
    return "1", cx, cy


def _clip(img: Path, out: Path, frames: int, fps: int, cam: tuple, w: int, h: int, crf: int,
          prev: Path | None = None, prev_cam: tuple | None = None, anim: list[Path] | None = None,
          xfade: int = 0) -> None:
    """One clip per shot. cam = (mode, zoom, start frame in the scene, scene length).
    Optional: a cross-fade from the previous scene's last frame, and a chart intro (anim frames) before the hold."""
    args, graph, inputs = [], [], 0

    def still(path: Path, c: tuple, d: int) -> str:
        nonlocal inputs
        z, x, y = _cam_expr(*c)
        args.extend(["-loop", "1", "-framerate", "1", "-t", "1", "-i", str(path)])
        i = inputs
        inputs += 1
        graph.append(f"[{i}:v]scale={w * 2}:{h * 2},zoompan=z='{z}':x='{x}':y='{y}'"
                     f":d={d}:s={w}x{h}:fps={fps},setsar=1,format=yuv420p[s{i}]")
        return f"[s{i}]"

    anim = [a for a in (anim or []) if a.exists()]
    use_x = prev is not None and prev_cam is not None and xfade > 0 and frames > xfade * 2
    frames_out = frames
    frames = frames + (1 if use_x else 0)       # xfade drops one frame; -frames:v below keeps the exact length
    if anim and frames > len(anim) + 2:
        lst = out.with_suffix(".anim.txt")
        lst.write_text("".join(f"file '{a.resolve().as_posix()}'\nduration {1 / fps:.5f}\n" for a in anim)
                       + f"file '{anim[-1].resolve().as_posix()}'\n", encoding="utf-8")
        args.extend(["-f", "concat", "-safe", "0", "-i", str(lst)])
        i = inputs
        inputs += 1
        graph.append(f"[{i}:v]fps={fps},scale={w}:{h},setsar=1,format=yuv420p,trim=end_frame={len(anim)}[a{i}]")
        hold = still(img, ("none", 0, 0, 1), frames - len(anim))
        graph.append(f"[a{i}]{hold}concat=n=2:v=1[main]")
    else:
        m = still(img, cam, frames)
        graph.append(f"{m}null[main]")
    last = "[main]"
    if use_x:
        p = still(prev, prev_cam, xfade + 1)
        graph.append(f"{p}settb=AVTB,fps={fps}[pp];{last}settb=AVTB,fps={fps}[mm];"
                     f"[pp][mm]xfade=transition=fade:duration={xfade / fps:.4f}:offset=0[xf]")
        last = "[xf]"
    _run([*args, "-filter_complex", ";".join(graph), "-map", last, "-frames:v", str(frames_out), "-r", str(fps),
          "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p", str(out)])


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


def outro_image(project: Project, cfg: Config, lang: str, last_scene: Path | None, size=(1920, 1080)) -> Path | None:
    """End screen on a soft, darkened copy of the video's last picture."""
    oc = cfg.get_path("channel.outro") or {}
    if oc.get("enabled") is False or float(oc.get("seconds", 18) or 0) <= 0:
        return None
    from .fx import draw_outro
    if last_scene and last_scene.exists():
        base = Image.open(last_scene).convert("RGB").resize(size).filter(ImageFilter.GaussianBlur(14))
        base = base.point(lambda v: int(v * 0.55))
    else:
        base = Image.new("RGB", size, "#2b2620")

    def pick(v, default):
        if isinstance(v, dict):
            return v.get(lang) or v.get(project.primary_lang()) or default
        return v or default
    text = pick(oc.get("text"), {"tr": "Sıradaki video"}.get(lang, "Watch next"))
    sub = pick(oc.get("sub"), cfg.get_path("channel.name", ""))
    out = project.lang_dir(lang) / "outro.png"
    draw_outro(base, text, sub).resize(size).save(out)
    return out


def _scene_image(project: Project, head: dict, texts: list[str], work: Path, size: tuple[int, int]) -> Path:
    img = project.shots_dir / f"{head['id']}.png"
    if not img.exists():
        img = work / f"{head['id']}_placeholder.png"
        placeholder(_wrap_text(" ".join(texts)), img, size)
    return img


def _wrap_text(text: str, width: int = 42) -> str:
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return "\n".join(lines + [cur])


def render_video(project: Project, cfg: Config, lang: str | None = None) -> Path:
    from .fx import apply_overlay, auto_overlays, build_sfx_track, sfx_events
    from .images import scenes
    lang = lang or project.primary_lang()
    primary = project.primary_lang()
    shots = {s["id"]: s for s in project.load_storyboard()["shots"]}
    tpath = project.timing_path(lang)
    if not tpath.exists():
        raise SystemExit(f"[{lang}] zamanlama yok. Önce 'voice' ve 'align' adımlarını çalıştır.")
    timing = project.read_json(tpath)
    fps = int(cfg.get_path("video.fps", 30))
    w, h = int(cfg.get_path("video.width", 1920)), int(cfg.get_path("video.height", 1080))
    zoom = float(cfg.get_path("video.zoom", 0.08))
    crf = int(cfg.get_path("video.crf", 20))
    xfade = int(cfg.get_path("video.xfade_frames", 10)) if cfg.get_path("video.transitions", True) else 0
    work = project.lang_dir(lang) / "clips"
    work.mkdir(exist_ok=True)
    ordered = [shots[t["id"]] for t in timing]
    frames_of = dict(zip((t["id"] for t in timing), _frames(timing, fps)))
    groups = scenes(ordered)
    modes = _scene_modes(groups)
    auto = auto_overlays(project)

    jobs, prev_img, prev_cam, n = [], None, None, 0
    for g, mode in zip(groups, modes):
        head = g[0]
        img = _scene_image(project, head, [s["text"] for s in g], work, (w, h))
        total = sum(frames_of[s["id"]] for s in g)
        start = 0
        for k, shot in enumerate(g):
            ov = _overlay_for(shot, auto)
            img_ov = apply_overlay(img, ov, lang, primary, work / f"{shot['id']}_ov.png")
            anim = sorted(project.shots_dir.glob(f"{head['id']}_a[0-9][0-9].png")) if k == 0 else []
            if ov and anim:
                anim = [apply_overlay(a, ov, lang, primary, work / f"{a.stem}_ov.png") for a in anim]
            jobs.append(dict(img=img_ov, out=work / f"{n:04d}.mp4", frames=frames_of[shot["id"]],
                             cam=(mode, zoom, start, total), anim=anim,
                             prev=prev_img if k == 0 else None, prev_cam=prev_cam if k == 0 else None))
            n += 1
            start += frames_of[shot["id"]]
            prev_img, prev_cam = img_ov, (mode, zoom, total - 1, total)

    last_scene = project.shots_dir / f"{groups[-1][0]['id']}.png" if groups else None
    outro = outro_image(project, cfg, lang, last_scene, (w, h))
    outro_frames = int(float(cfg.get_path("channel.outro.seconds", 18) or 18) * fps) if outro else 0
    if outro:
        jobs.append(dict(img=outro, out=work / f"{n:04d}.mp4", frames=outro_frames,
                         cam=("in", zoom / 2, 0, outro_frames), anim=[], prev=prev_img, prev_cam=prev_cam))

    print(f"  [{lang}] {len(groups)} sahne, {len(jobs)} klip hazırlanıyor...")
    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        for _ in ex.map(lambda j: _clip(j["img"], j["out"], j["frames"], fps, j["cam"], w, h, crf,
                                        j["prev"], j["prev_cam"], j["anim"], xfade), jobs):
            done += 1
            if done % 25 == 0 or done == len(jobs):
                print(f"  klip {done}/{len(jobs)}")
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{j['out'].name}'\n" for j in jobs), encoding="utf-8")
    silent = work / "video_silent.mp4"
    _run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)])
    total = sum(_frames(timing, fps)) / fps + outro_frames / fps
    sfx = None
    if cfg.get_path("audio.sfx", True):
        sfx = build_sfx_track(sfx_events(groups, timing), total, ASSETS, work / "sfx.wav")
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
    Pictures are framed for 9:16 (blurred backdrop, charts re-cut as vectors) with burned-in captions."""
    from .fx import caption_frame, focus_x
    from .images import engine_name, scene_map
    from .project import shot_text
    lang = lang or project.primary_lang()
    cuts = project.meta.get("shorts") or []
    if not cuts:
        raise SystemExit("project.yaml → shorts listesi boş. Örnek: shorts: [{title: 'Hook', from: s001, to: s018}]")
    timing = project.read_json(project.timing_path(lang))
    ids = [t["id"] for t in timing]
    all_shots = project.load_storyboard()["shots"]
    shots = {s["id"]: s for s in all_shots}
    heads = scene_map(all_shots)
    fps = int(cfg.get_path("video.fps", 30))
    zoom = float(cfg.get_path("video.zoom", 0.08))
    out_dir = project.lang_dir(lang) / "shorts"
    out_dir.mkdir(exist_ok=True)
    vdir = project.build / "shots_9x16"
    vdir.mkdir(exist_ok=True)
    made = []

    def vertical(head: dict, work: Path) -> Path:
        vert = vdir / f"{head['id']}.png"
        src = project.shots_dir / f"{head['id']}.png"
        if vert.exists() and src.exists() and vert.stat().st_mtime >= src.stat().st_mtime:
            return vert
        v = head.get("visual")
        if isinstance(v, dict) and engine_name(head, cfg) == "svg":
            from .images.svg_engine import SvgEngine
            from .svgkit import crop_vertical, render_svg
            from .svgkit.style import use_palette
            with SvgEngine(cfg) as eng, use_palette(cfg.get_path("channel.style.palette") or {}):
                eng.svg_to_png(crop_vertical(render_svg({k: x for k, x in v.items() if k != "frame"}), focus_x(v)),
                               vert, size=(1080, 1920))
            return vert
        if not src.exists():
            src = work / f"{head['id']}_ph.png"
            placeholder(_wrap_text(head["text"], 24), src)
        _short_frame_fallback(src, vert)
        return vert

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
        frames = _frames(rel, fps)
        scene_len: dict[str, int] = {}
        for t, f in zip(rel, frames):
            scene_len[heads[t["id"]]] = scene_len.get(heads[t["id"]], 0) + f
        clips, pos = [], {}
        for i, (t, f) in enumerate(zip(rel, frames)):
            shot, hid = shots[t["id"]], heads[t["id"]]
            vert = vertical(shots[hid], work)
            title = cut.get("hook") if (cut.get("hook") and t["start"] < 2.5) else cut.get("title", "")
            frame = work / f"{t['id']}.png"
            caption_frame(Image.open(vert), title, shot_text(shot, lang, project.primary_lang())).save(frame)
            clip = work / f"{i:04d}.mp4"
            _clip(frame, clip, f, fps, ("in", zoom, pos.get(hid, 0), scene_len[hid]), 1080, 1920, 21)
            pos[hid] = pos.get(hid, 0) + f
            clips.append(clip)
        (work / "list.txt").write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
        silent = work / "silent.mp4"
        _run(["-f", "concat", "-safe", "0", "-i", str(work / "list.txt"), "-c", "copy", str(silent)])
        out = out_dir / f"short{n:02d}.mp4"
        _mix_and_mux(silent, project.audio_dir(lang) / "narration.wav", out, cfg, work, start=base, duration=total)
        made.append(out)
        print(f"  short hazır: {out.name} ({total:.0f} sn, dikey + altyazı)")
    return made


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


def contact_sheet(project: Project, cols: int = 4, limit: int = 400) -> Path:
    """One tile per scene (picture + the words it covers), for reviewing the whole video at a glance."""
    from .images import scenes
    groups = scenes(project.load_storyboard()["shots"])[:limit]
    tw, th, lh = 480, 270, 64
    rows = max(1, (len(groups) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + lh)), "white")
    d = ImageDraw.Draw(sheet)
    font = _font(15)
    for i, g in enumerate(groups):
        x, y = (i % cols) * tw, (i // cols) * (th + lh)
        p = project.shots_dir / f"{g[0]['id']}.png"
        if p.exists():
            sheet.paste(Image.open(p).convert("RGB").resize((tw, th)), (x, y))
        else:
            d.rectangle([x, y, x + tw - 1, y + th - 1], fill="#eee")
        words = " ".join(s["text"] for s in g)
        label = f"{g[0]['id']}–{g[-1]['id'][1:]}  {words}" if len(g) > 1 else f"{g[0]['id']}  {words}"
        d.multiline_text((x + 6, y + th + 4), _wrap_text(label, 56)[:180], fill="black", font=font, spacing=2)
    out = project.build / "contact_sheet.png"
    sheet.save(out)
    return out
