"""Final assembly with FFmpeg: one gently moving clip per shot → concat → narration + music → loudness normalised."""
from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import ASSETS, Config
from .project import Project


def _run(args: list[str]) -> None:
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])


def _measure_lufs(path: Path) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    vals = [ln for ln in r.stderr.splitlines() if ln.strip().startswith("I:")]
    return float(vals[-1].split()[1]) if vals else -23.0


def placeholder(text: str, out: Path, size=(1920, 1080)) -> None:
    """A plain card showing the narration text, used when a shot has no image yet."""
    img = Image.new("RGB", size, "#efe6d2")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 64)
    except OSError:
        font = ImageFont.load_default()
    d.multiline_text((size[0] // 2, size[1] // 2), text, fill="#555", font=font, anchor="mm", align="center")
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


def render_video(project: Project, cfg: Config) -> Path:
    shots = {s["id"]: s for s in project.load_storyboard()["shots"]}
    timing = project.read_json(project.timing_path)
    fps = int(cfg.get_path("video.fps", 30))
    w, h = int(cfg.get_path("video.width", 1920)), int(cfg.get_path("video.height", 1080))
    zoom = float(cfg.get_path("video.zoom", 0.06))
    crf = int(cfg.get_path("video.crf", 20))
    clips_dir = project.build / "clips"
    clips_dir.mkdir(exist_ok=True)

    jobs = []
    for i, t in enumerate(timing):
        f0, f1 = round(t["start"] * fps), round(t["end"] * fps)
        frames = max(1, f1 - f0)
        img = project.shots_dir / f"{t['id']}.png"
        if not img.exists():
            img = clips_dir / f"{t['id']}_placeholder.png"
            placeholder(shots[t["id"]]["text"], img, (w, h))
        jobs.append((img, clips_dir / f"{i:04d}.mp4", frames, _camera(shots[t["id"]], i)))

    print(f"  {len(jobs)} klip hazırlanıyor...")
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda j: _clip(j[0], j[1], j[2], fps, zoom, j[3], w, h, crf), jobs))

    lst = clips_dir / "list.txt"
    lst.write_text("".join(f"file '{j[1].name}'\n" for j in jobs))
    silent = project.build / "video_silent.mp4"
    _run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)])

    narration = project.audio_dir / "narration.wav"
    out = project.build / "video.mp4"
    mixed = project.build / "mix.wav"
    lufs = float(cfg.get_path("audio.target_lufs", -14))
    music_name = cfg.get_path("audio.music", "") or ""
    music = ASSETS / "music" / music_name if music_name else None
    if music and music.exists():
        vol = cfg.get_path("audio.music_volume", 0.07)
        _run(["-i", str(narration), "-stream_loop", "-1", "-i", str(music), "-filter_complex",
              f"[0:a]acompressor=threshold=-20dB:ratio=3:attack=5:release=120[v];"
              f"[1:a]volume={vol}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]",
              "-map", "[a]", "-ar", "48000", str(mixed)])
    else:
        _run(["-i", str(narration), "-af", "acompressor=threshold=-20dB:ratio=3:attack=5:release=120",
              "-ar", "48000", str(mixed)])
    gain = lufs - _measure_lufs(mixed)  # two-pass: measure, then apply exact gain + peak limiter
    _run(["-i", str(silent), "-i", str(mixed), "-filter_complex",
          f"[1:a]volume={gain:.2f}dB,alimiter=limit=0.87:level=false[a]",
          "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])
    print(f"  video hazır: {out}")
    return out


def contact_sheet(project: Project, cols: int = 6, limit: int = 48) -> Path:
    """Grid of shot thumbnails with their ids, for a quick visual review."""
    shots = project.load_storyboard()["shots"][:limit]
    tw, th = 320, 180
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 30)), "white")
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
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
