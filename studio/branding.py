"""Channel artwork for YouTube Studio → Customisation → Branding, painted in the channel's style.

  python -m studio branding [--channel C] [--force]   →  channels/<C>/build/branding/
    profile.png       800×800   profile picture: the coach's portrait (shown as a circle)
    banner.png        2560×1440 banner: a panorama without people in focus, and inside the 1546×423 area every
                                device shows, the coach's portrait in a round frame + name + tagline
    banner_guides.png the banner with TV / desktop / phone crop lines, for checking before upload
    watermark.png     150×150   video watermark (transparent round badge)

The two paintings (raw/profile_art.png, raw/banner_art.png) are made once with Gemini and reused; --force repaints.
Optional channel.yaml → branding:
  branding:
    profile_prompt: "..."         # replaces the default portrait description
    profile_crop: [0.15, 0, 0.85, 0.7]   # part of the portrait painting used (fractions x0 y0 x1 y1), default all
    banner_prompt: "..."          # replaces the default banner scene (keep it free of the coach: she is framed)
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

PROFILE_SCENE = ("Close-up head-and-shoulders portrait of the coach, centred, looking at the viewer with a confident "
                 "warm smile, plain soft warm background. Her face fills the middle of the square, cropped just "
                 "below the shoulders; no hands, no body below the chest.")
BANNER_SCENE = ("One continuous wide panoramic landscape painting, a single scene with one horizon line at the "
                "vertical middle of the picture, no panels, no borders, no split. From left to right it slowly "
                "changes from an ancient golden savanna with small early humans running and throwing spears, to a "
                "Greek stadium track, to a modern athletics track. All people are small, seen from a distance, and "
                "stand along the horizon in the middle band; sky above and ground below are calm and empty.")
MEDALLION = 360               # the coach's round portrait on the banner (inside the safe area)


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


def _crop(img: Image.Image, frac) -> Image.Image:
    """Square crop by fractions [x0, y0, x1, y1] of the image (None = whole image)."""
    if not frac:
        return img
    W, H = img.size
    x0, y0, x1, y1 = (round(f * d) for f, d in zip(frac, (W, H, W, H)))
    side = min(x1 - x0, y1 - y0)
    return img.crop((x0, y0, x0 + side, y0 + side))


def _medallion(img: Image.Image, portrait: Image.Image, centre: tuple[int, int], size: int) -> None:
    """Paste the portrait as a circle with a light ring and a soft shadow, centred on `centre`."""
    from PIL import ImageFilter
    face = portrait.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    x, y = centre[0] - size // 2, centre[1] - size // 2
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([x + 6, y + 14, x + size + 6, y + size + 14], fill=(0, 0, 0, 140))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
    img.paste(face, (x, y), mask)
    ImageDraw.Draw(img).ellipse([x, y, x + size - 1, y + size - 1], outline="#f4ead7", width=10)


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
    portrait = _crop(Image.open(art).convert("RGB"), b.get("profile_crop")).resize((PROFILE, PROFILE), Image.LANCZOS)
    raw = out / "profile.png"
    portrait.save(raw)
    made.append(raw)

    # watermark: the same portrait, round and transparent outside the circle
    wm = portrait.convert("RGBA").crop((80, 40, 720, 680)).resize((WATERMARK, WATERMARK), Image.LANCZOS)
    mask = Image.new("L", (WATERMARK, WATERMARK), 0)
    ImageDraw.Draw(mask).ellipse([2, 2, WATERMARK - 3, WATERMARK - 3], fill=255)
    wm.putalpha(mask)
    ImageDraw.Draw(wm).ellipse([2, 2, WATERMARK - 3, WATERMARK - 3], outline="#ffffff", width=5)
    wpath = out / "watermark.png"
    wm.save(wpath)
    made.append(wpath)

    # banner: a panorama across the full width; the coach's portrait in a round frame and the name + tagline sit
    # inside the safe area, so a phone shows her face and the name, a TV the whole painting
    bart = _paint(eng, build_prompt({"prompt": b.get("banner_prompt") or BANNER_SCENE}, eng.style, chars),
                  raw_dir / "banner_art.png", "16:9", BANNER, [], force)
    x0, y0, x1, y1 = safe_box()
    img = Image.open(bart).convert("RGBA").resize(BANNER, Image.LANCZOS)
    cx, cy = x0 + 30 + MEDALLION // 2, (y0 + y1) // 2
    band = Image.new("RGBA", BANNER, (0, 0, 0, 0))
    ImageDraw.Draw(band).rounded_rectangle([cx, y0 + 50, x1 - 10, y1 - 50], radius=36, fill=(20, 16, 12, 165))
    img = Image.alpha_composite(img, band)
    _medallion(img, portrait, (cx, cy), MEDALLION)
    img = img.convert("RGB")
    _banner_text(img, data.get("name") or channel, data.get("tagline") or "", cx + MEDALLION // 2 + 40,
                 b.get("name_color", "#ffffff"), b.get("accent", "#ffd84d"))
    bpath = out / "banner.png"
    img.save(bpath, optimize=True)
    made.append(bpath)
    made.append(guides(bpath, out / "banner_guides.png"))
    for p in made:
        print(f"  {p.name}: {out / p.name}")
    return made
