"""Channel artwork for YouTube Studio → Customisation → Branding, painted in the channel's style.

  python -m studio branding [--channel C] [--force]   →  channels/<C>/build/branding/
    profile.png       800×800   profile picture: the coach's portrait (shown as a circle)
    banner.png        2560×1440 banner; name + tagline inside the 1546×423 area every device shows
    banner_guides.png the banner with TV / desktop / phone crop lines, for checking before upload
    watermark.png     150×150   video watermark (transparent round badge)

The two paintings (raw/profile_art.png, raw/banner_art.png) are made once with Gemini and reused; --force repaints.
Optional channel.yaml → branding:
  branding:
    profile_prompt: "..."         # replaces the default portrait description
    banner_prompt: "..."          # replaces the default banner scene
    name_color: "#ffffff"
    accent: "#e3a447"             # tagline colour
Text is allowed here (not in shots): it is channel artwork, not a video frame.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .channel import Channel
from .config import Config

PROFILE = 800
BANNER = (2560, 1440)
SAFE = (1546, 423)            # always visible (phone); desktop shows 2560×423, TV the whole banner
DESKTOP_H = 423
WATERMARK = 150

PROFILE_SCENE = ("Head-and-shoulders portrait of the coach, centred, looking at the viewer with a confident warm "
                 "smile, plain soft warm background, the face filling the middle third of the square.")
BANNER_SCENE = ("Wide panoramic scene: on the left, the coach stands confidently; behind and across the frame a "
                "painted journey of human movement from an ancient savanna with early humans running and throwing "
                "on the far left to a modern training ground on the right. The middle band of the picture is calm "
                "and uncluttered so a title can sit on it.")


def safe_box() -> tuple[int, int, int, int]:
    x0, y0 = (BANNER[0] - SAFE[0]) // 2, (BANNER[1] - SAFE[1]) // 2
    return x0, y0, x0 + SAFE[0], y0 + SAFE[1]


def _banner_text(img: Image.Image, name: str, tagline: str, left: int, name_color: str, accent: str) -> None:
    from .thumbnails import _font, _wrap
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = safe_box()
    box_w = x1 - 40 - left
    size = 150
    while size > 50:
        f = _font(size)
        if d.textlength(name.upper(), font=f) <= box_w:
            break
        size -= 6
    tf_size = max(34, size // 3)
    tf = _font(tf_size)
    tag_lines = _wrap(d, tagline, tf, box_w)[:2] if tagline else []
    block = size + (len(tag_lines) * int(tf_size * 1.25) + 18 if tag_lines else 0)
    y = y0 + (SAFE[1] - block) // 2
    stroke = max(6, size // 12)
    d.text((left + 6, y + 8), name.upper(), font=f, fill="#000000", stroke_width=stroke, stroke_fill="#000000")
    d.text((left, y), name.upper(), font=f, fill=name_color, stroke_width=stroke, stroke_fill="#111111")
    y += size + 18
    for ln in tag_lines:
        d.text((left, y), ln, font=tf, fill=accent, stroke_width=max(3, tf_size // 12), stroke_fill="#111111")
        y += int(tf_size * 1.25)


def guides(banner: Path, out: Path) -> Path:
    img = Image.open(banner).convert("RGB")
    d = ImageDraw.Draw(img)
    W, H = BANNER
    dy = (H - DESKTOP_H) // 2
    d.rectangle([0, dy, W - 1, dy + DESKTOP_H], outline="#2f80ff", width=8)          # desktop
    d.rectangle(safe_box(), outline="#ff3b30", width=8)                              # every device
    from .render import _font as small_font
    f = small_font(34)
    d.text((24, dy - 48), "masaüstü (2560×423)", fill="#2f80ff", font=f)
    d.text((safe_box()[0], safe_box()[3] + 12), "her cihaz / telefon (1546×423)", fill="#ff3b30", font=f)
    d.text((24, 20), "TV: tamamı", fill="#ffffff", font=f)
    img.save(out)
    return out


def _paint(eng, prompt: str, out: Path, aspect: str, size: tuple[int, int], refs: list[Path], force: bool) -> Path:
    if force or not out.exists():
        eng.generate(prompt, out, refs, aspect=aspect, size=size)
    return out


def render_branding(channel: str, cfg: Config, force: bool = False) -> list[Path]:
    from .images.gemini_engine import GeminiEngine
    from .images.style_prompt import build_prompt
    ch = Channel(channel)
    data = ch.data
    b = data.get("branding") or {}
    out = ch.dir / "build" / "branding"
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    eng = GeminiEngine(cfg)
    chars = cfg.get_path("channel.characters") or {}
    who = [n for n in ("coach",) if n in chars] or list(chars)[:1]
    refs = eng.char_refs(who)
    made: list[Path] = []

    def prompt(scene: str) -> str:
        return build_prompt({"prompt": scene, "characters": who}, eng.style, chars)

    art = _paint(eng, prompt(b.get("profile_prompt") or PROFILE_SCENE), raw_dir / "profile_art.png", "1:1",
                 (PROFILE, PROFILE), refs, force)
    raw = out / "profile.png"
    Image.open(art).convert("RGB").resize((PROFILE, PROFILE), Image.LANCZOS).save(raw)
    made.append(raw)

    # watermark: the same portrait, round and transparent outside the circle
    wm = Image.open(raw).convert("RGBA").crop((120, 80, 680, 640)).resize((WATERMARK, WATERMARK), Image.LANCZOS)
    mask = Image.new("L", (WATERMARK, WATERMARK), 0)
    ImageDraw.Draw(mask).ellipse([2, 2, WATERMARK - 3, WATERMARK - 3], fill=255)
    wm.putalpha(mask)
    ImageDraw.Draw(wm).ellipse([2, 2, WATERMARK - 3, WATERMARK - 3], outline="#ffffff", width=5)
    wpath = out / "watermark.png"
    wm.save(wpath)
    made.append(wpath)

    # banner: painting across the full width, name + tagline on a soft band inside the safe area
    bart = _paint(eng, prompt(b.get("banner_prompt") or BANNER_SCENE), raw_dir / "banner_art.png", "16:9",
                  BANNER, refs, force)
    x0, y0, x1, y1 = safe_box()
    img = Image.open(bart).convert("RGBA").resize(BANNER, Image.LANCZOS)
    band = Image.new("RGBA", BANNER, (0, 0, 0, 0))
    ImageDraw.Draw(band).rounded_rectangle([x0 + 360, y0 + 20, x1, y1 - 20], radius=28, fill=(15, 15, 15, 150))
    img = Image.alpha_composite(img, band).convert("RGB")
    _banner_text(img, data.get("name") or channel, data.get("tagline") or "", x0 + 400,
                 b.get("name_color", "#ffffff"), b.get("accent", "#ffd84d"))
    bpath = out / "banner.png"
    img.save(bpath, optimize=True)
    made.append(bpath)
    made.append(guides(bpath, out / "banner_guides.png"))
    for p in made:
        print(f"  {p.name}: {out / p.name}")
    return made
