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


def _camera(shot: dict, index: int) -> str:
    cam = (shot.get("camera") or {}).get("zoom") if isinstance(shot.get("camera"), dict) else shot.get("camera")
    if cam in ("in", "out", "none"):
        return cam
    return "in" if index % 3 != 2 else "out"  # mostly push-in, every third pulls out


def _clip(img: Path, out: Path, frames: int, fps: int, zoom: float, mode: str, w: int, h: int, crf: int) -> None:
    if mode == "none" or zoom <= 0:
        vf = f"scale={w}:{h},format=yuv420p"
    else:
        z = f"1+{zoom}*on/{max(frames - 1, 1)}" if mode == "in" else f"1+{zoom}-{zoom}*on/{max(frames - 1, 1)}"
        vf = (f"scale={w * 2}:{h * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={w}x{h}:fps={fps},format=yuv420p")
    _run(["-loop", "1", "-i", str(img), "-vf", vf, "-frames:v", str(frames), "-r", str(fps),
          "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), str(out)])


def _mix_and_mux(silent: Path, narration: Path, out: Path, cfg: Config, work: Path, start: float = 0.0,
                 duration: float | None = None) -> None:
    """Narration (+ optional music) → compressor → exact loudness gain → limiter → mux with video."""
    mixed = work / "mix.wav"
    lufs = float(cfg.get_path("audio.target_lufs", -14))
    music_name = cfg.get_path("audio.music", "") or ""
    music = ASSETS / "music" / music_name if music_name else None
    trim = ["-ss", f"{start:.3f}"] + (["-t", f"{duration:.3f}"] if duration else [])
    comp = "acompressor=threshold=-20dB:ratio=3:attack=5:release=120"
    if music and music.exists():
        vol = cfg.get_path("audio.music_volume", 0.07)
        _run([*trim, "-i", str(narration), "-stream_loop", "-1", "-i", str(music), "-filter_complex",
              f"[0:a]{comp}[v];[1:a]volume={vol}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]",
              "-map", "[a]", "-ar", "48000", str(mixed)])
    else:
        _run([*trim, "-i", str(narration), "-af", comp, "-ar", "48000", str(mixed)])
    gain = lufs - _measure_lufs(mixed)
    _run(["-i", str(silent), "-i", str(mixed), "-filter_complex",
          f"[1:a]volume={gain:.2f}dB,alimiter=limit=0.87:level=false[a]",
          "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])


def _frames(timing: list[dict], fps: int) -> list[int]:
    return [max(1, round(t["end"] * fps) - round(t["start"] * fps)) for t in timing]


def render_video(project: Project, cfg: Config, lang: str | None = None) -> Path:
    lang = lang or project.primary_lang()
    shots = {s["id"]: s for s in project.load_storyboard()["shots"]}
    tpath = project.timing_path(lang)
    if not tpath.exists():
        raise SystemExit(f"[{lang}] zamanlama yok. Önce 'voice' ve 'align' adımlarını çalıştır.")
    timing = project.read_json(tpath)
    fps = int(cfg.get_path("video.fps", 30))
    w, h = int(cfg.get_path("video.width", 1920)), int(cfg.get_path("video.height", 1080))
    zoom = float(cfg.get_path("video.zoom", 0.06))
    crf = int(cfg.get_path("video.crf", 20))
    work = project.lang_dir(lang) / "clips"
    work.mkdir(exist_ok=True)

    jobs = []
    for i, (t, frames) in enumerate(zip(timing, _frames(timing, fps))):
        img = project.shots_dir / f"{t['id']}.png"
        if not img.exists():
            img = work / f"{t['id']}_placeholder.png"
            placeholder(shots[t["id"]]["text"], img, (w, h))
        jobs.append((img, work / f"{i:04d}.mp4", frames, _camera(shots[t["id"]], i)))

    print(f"  [{lang}] {len(jobs)} klip hazırlanıyor...")
    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        for _ in ex.map(lambda j: _clip(j[0], j[1], j[2], fps, zoom, j[3], w, h, crf), jobs):
            done += 1
            if done % 25 == 0 or done == len(jobs):
                print(f"  klip {done}/{len(jobs)}")
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{j[1].name}'\n" for j in jobs))
    silent = work / "video_silent.mp4"
    _run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)])
    out = project.video_path(lang)
    _mix_and_mux(silent, project.audio_dir(lang) / "narration.wav", out, cfg, work)
    describe(project, cfg, lang)
    print(f"  video hazır: {out}")
    return out


# ---------------------------------------------------------------- shorts
def _cover(img: Image.Image, W: int, H: int) -> Image.Image:
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)))
    l, t = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((l, t, l + W, t + H))


def _short_frame(img_path: Path, title: str, out: Path, size=(1080, 1920)) -> None:
    W, H = size
    src = Image.open(img_path).convert("RGB")
    canvas = _cover(src, W, H).filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * 0.72))
    cw = min(src.width, round(src.height * 4 / 3))          # centre 4:3 crop → bigger figures
    left = (src.width - cw) // 2
    fg = src.crop((left, 0, left + cw, src.height)).resize((W, round(src.height * W / cw)))
    top = (H - fg.height) // 2 + 80
    canvas.paste(fg, (0, top))
    d = ImageDraw.Draw(canvas)
    font = _font(68)
    lines, line = [], ""
    for wd in title.split():
        test = f"{line} {wd}".strip()
        if d.textlength(test, font=font) > W - 120 and line:
            lines.append(line)
            line = wd
        else:
            line = test
    if line:
        lines.append(line)
    y = top - 70 - (len(lines) - 1) * 84
    for ln in lines:
        d.text((W // 2, y), ln, font=font, fill="white", anchor="mm", stroke_width=6, stroke_fill="black")
        y += 84
    canvas.save(out)


def render_shorts(project: Project, cfg: Config, lang: str | None = None) -> list[Path]:
    """Cuts listed in project.yaml → shorts: [{title: "...", from: s012, to: s030}]."""
    lang = lang or project.primary_lang()
    cuts = project.meta.get("shorts") or []
    if not cuts:
        raise SystemExit("project.yaml → shorts listesi boş. Örnek: shorts: [{title: 'Hook', from: s001, to: s018}]")
    timing = project.read_json(project.timing_path(lang))
    ids = [t["id"] for t in timing]
    fps = int(cfg.get_path("video.fps", 30))
    out_dir = project.lang_dir(lang) / "shorts"
    out_dir.mkdir(exist_ok=True)
    made = []
    for n, cut in enumerate(cuts, 1):
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
            frame = work / f"{t['id']}.png"
            src = project.shots_dir / f"{t['id']}.png"
            if not src.exists():
                placeholder(t["id"], src)
            _short_frame(src, cut.get("title", ""), frame)
            clip = work / f"{i:04d}.mp4"
            _clip(frame, clip, frames, fps, float(cfg.get_path("video.zoom", 0.06)), "in", 1080, 1920, 21)
            clips.append(clip)
        (work / "list.txt").write_text("".join(f"file '{c.name}'\n" for c in clips))
        silent = work / "silent.mp4"
        _run(["-f", "concat", "-safe", "0", "-i", str(work / "list.txt"), "-c", "copy", str(silent)])
        out = out_dir / f"short{n:02d}.mp4"
        _mix_and_mux(silent, project.audio_dir(lang) / "narration.wav", out, cfg, work, start=base, duration=total)
        made.append(out)
        print(f"  short hazır: {out.name} ({total:.0f} sn)")
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
