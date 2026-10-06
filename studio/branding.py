"""Channel artwork for YouTube Studio → Customisation → Branding, drawn with the same kit as the videos.

  python -m studio branding [--channel C]   →  channels/<C>/build/branding/
    profile.png       800×800   profile picture (shown as a circle: the mascot's face sits in the middle)
    banner.png        2560×1440 banner; name + tagline inside the 1546×423 area every device shows
    banner_guides.png the banner with TV / desktop / phone crop lines, for checking before upload
    watermark.png     150×150   video watermark (transparent round badge)

Optional channel.yaml → branding (all keys optional):
  branding:
    profile_bg: plain_warm        # any background from docs/STORYBOARD.md
    banner_bg: split              # "then vs now": fits a channel about the body through history
    banner_props: [{type: spear, x: 300}]
  mascot_pose: wave               # pose for the artwork (default wave; the video mascot pose points)
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
SVG_W, SVG_H = 1920, 1080


def _view(svg: str, x0: float, y0: float, vw: float, vh: float, out_w: int, out_h: int) -> str:
    head = f'width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}"'
    return svg.replace(head, f'width="{out_w}" height="{out_h}" viewBox="{x0:.1f} {y0:.1f} {vw:.1f} {vh:.1f}"', 1)


def _mascot(cfg: Config, **extra) -> dict:
    m = dict(cfg.get_path("channel.mascot") or {})
    m.update({"pose": "wave", "hold": "none"})      # friendly and compact: no pointer crossing the name
    m.update({k: v for k, v in extra.items() if v is not None})
    return m


def _head_box(mascot: dict, ground: float) -> tuple[float, float]:
    """Centre of the mascot's head+shoulders in drawing coordinates (figure ~450 px tall at scale 1)."""
    s = float(mascot.get("scale", 1))
    return float(mascot.get("x", 960)), ground - 355 * s


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


def render_branding(channel: str, cfg: Config) -> list[Path]:
    from .images.svg_engine import SvgEngine
    from .svgkit import backgrounds, render_svg
    from .svgkit.style import use_palette
    ch = Channel(channel)
    data = ch.data
    b = data.get("branding") or {}
    out = ch.dir / "build" / "branding"
    out.mkdir(parents=True, exist_ok=True)
    palette = cfg.get_path("channel.style.palette") or {}
    made: list[Path] = []

    with SvgEngine(cfg) as eng, use_palette(palette):
        # profile picture: head and shoulders, centred for YouTube's circle crop
        pbg = b.get("profile_bg", "plain_warm")
        ground = backgrounds.get(pbg)[2]
        m = _mascot(cfg, x=960, scale=1.6, pose=b.get("mascot_pose"))
        cx, cy = _head_box(m, ground)
        side = 540
        svg = _view(render_svg({"bg": pbg, "figures": [m]}), cx - side / 2, cy - side / 2, side, side,
                    PROFILE, PROFILE)
        raw = out / "profile.png"
        eng.svg_to_png(svg, raw, size=(PROFILE, PROFILE))
        made.append(raw)

        # watermark: same drawing, round and transparent outside the circle
        wm = Image.open(raw).convert("RGBA").crop((170, 150, 630, 610)).resize((WATERMARK, WATERMARK), Image.LANCZOS)
        mask = Image.new("L", (WATERMARK, WATERMARK), 0)
        ImageDraw.Draw(mask).ellipse([2, 2, WATERMARK - 3, WATERMARK - 3], fill=255)
        wm.putalpha(mask)
        ImageDraw.Draw(wm).ellipse([2, 2, WATERMARK - 3, WATERMARK - 3], outline="#ffffff", width=5)
        wpath = out / "watermark.png"
        wm.save(wpath)
        made.append(wpath)

        # banner: scene across the full width, mascot at the left edge of the safe area, text beside him
        bbg = b.get("banner_bg", "split")
        ground = backgrounds.get(bbg)[2]
        sx = BANNER[0] / SVG_W                       # 2560 / 1920
        x0, y0, x1, y1 = safe_box()
        mascot_x = (x0 + 190) / sx
        # stand him so head+torso fill the safe area's height
        scale = 0.95
        m = _mascot(cfg, x=mascot_x, scale=scale, ground=(y1 / sx) + 150 * scale, pose=b.get("mascot_pose"))
        svg = render_svg({"bg": bbg, "figures": [m], "props": b.get("banner_props") or []})
        svg = _view(svg, 0, 0, SVG_W, SVG_H, *BANNER)
        bpath = out / "banner.png"
        eng.svg_to_png(svg, bpath, size=BANNER)
    img = Image.open(bpath).convert("RGB")
    band = Image.new("RGBA", BANNER, (0, 0, 0, 0))
    ImageDraw.Draw(band).rounded_rectangle([x0 + 360, y0 + 20, x1, y1 - 20], radius=28, fill=(15, 15, 15, 150))
    img = Image.alpha_composite(img.convert("RGBA"), band).convert("RGB")
    _banner_text(img, data.get("name") or channel, data.get("tagline") or "", x0 + 400,
                 b.get("name_color", "#ffffff"), b.get("accent", "#ffd84d"))
    img.save(bpath, optimize=True)
    made.append(bpath)
    made.append(guides(bpath, out / "banner_guides.png"))
    for p in made:
        print(f"  {p.name}: {out / p.name}")
    return made
