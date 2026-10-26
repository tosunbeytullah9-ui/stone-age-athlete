"""Thumbnail kinds (docs/THUMBNAILS.md). A channel picks its own set of three (`channel.yaml → thumbnails.kinds`), so
two channels of the same owner never share one thumbnail grammar.

Myth channels (default set: You're Wrong!, Homo Athleticus):
  correction  the belief in big letters, struck through by hand in the accent colour, a short handwritten note under it
  stamp       one picture, one rubber stamp ("WRONG", "MYTH", ...) on its empty side, no other words
  scene       a moment from the video with at most three handwritten words
Object channels (Ordinary Genius): the object is the hero, the hidden part is the question
  loupe       the object drawn huge; a magnifying lens blows up the one small part that does the trick
  xray        the object split by a glowing scan line: outside on one side, its mechanism on the other
  tag         the object drawn huge; one thick arrow and a part tag point at the part the video explains

The look comes from the channel (`channel.yaml → thumbnails`): ink and accent colour, the three fonts, whether the
picture is a paper page (warm it, darken its edges, thicken thin lines) or a painting (words sit on a paper slip),
and the series tab colour. Every size below is written for a 1280×720 canvas and scaled to the output size.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .config import ASSETS

FONTS = ASSETS / "fonts"
KINDS = ("correction", "stamp", "scene", "loupe", "xray", "tag")
DEFAULT_KINDS = ["correction", "stamp", "scene"]
KIND_INFO = {   # Turkish name (panel, preview) and how the packaging prompt explains the kind
    "correction": ("Düzeltme", "`myth`: the belief the video overturns, at most 3 short words or one number, printed big "
                   "and struck through by hand. `note`: at most 3 handwritten words under it that open a curiosity gap "
                   "without giving the answer away. Picture: the object of the belief, large."),
    "stamp": ("Damga", "One iconic object of the belief drawn large; a rubber stamp (\"{stamp}\") goes on the empty "
              "side. `stamp` only if another word fits much better. No other words."),
    "scene": ("Sahne", "A funny or tense moment that really happens in the video; `text`: at most 3 words."),
    "loupe": ("Büyüteç", "The everyday object drawn huge and exact, filling about half of the frame. `focus: {x, y, r}` "
              "marks the one small part that does the trick (design canvas 1920×1080) and `lens: {x, y, r}` where a "
              "magnifying lens shows it enlarged (lens.r ≈ 2–3 × focus.r, on the empty side). `text`: at most 3 words "
              "that ask, never answer."),
    "xray": ("Röntgen", "The same object twice on the same canvas: `visual` = the outside as everyone knows it, "
             "`inside` = the same drawing cut open, its mechanism glowing yellow (same position and size). The factory "
             "splits them with a glowing scan line (`split: {x, angle}`; the inside shows on the `side`, default right). "
             "`text`: at most 3 words."),
    "tag": ("Etiket", "The object drawn huge; `point: {x, y}` is the small part the video explains. The factory draws "
            "rings around it and one thick arrow from a yellow part tag. `text` on the tag: at most 3 words, a "
            "question or a number that is a claim (\"WHY TEETH?\", \"5 LAYERS\")."),
}
KIND_EXAMPLE = {
    "correction": '{{kind: correction, visual: {{prompt: "...", characters: []}}, myth: {{en: "..."}}, note: {{en: "..."}}, pos: top-left, claim: c01}}',
    "stamp": '{{kind: stamp, visual: {{prompt: "...", characters: []}}, pos: top-left}}',
    "scene": '{{kind: scene, visual: {{prompt: "...", characters: []}}, text: {{en: "..."}}, pos: top}}',
    "loupe": '{{kind: loupe, visual: {{comp: mech, items: [...]}}, focus: {{x: 1300, y: 620, r: 90}}, lens: {{x: 560, y: 600, r: 260}}, text: {{en: "..."}}, pos: top-left}}',
    "xray": '{{kind: xray, visual: {{comp: mech, items: [...]}}, inside: {{comp: mech, items: [...]}}, split: {{x: 1150, angle: 10}}, text: {{en: "..."}}, pos: top-left}}',
    "tag": '{{kind: tag, visual: {{comp: mech, items: [...]}}, point: {{x: 1290, y: 760}}, text: {{en: "..."}}, pos: top-left, claim: c05}}',
}
DEFAULT_THEME = {
    "ink": "#181614",
    "accent": "#b23026",
    "stamp": "WRONG",
    "fonts": {"title": "Anton-Regular.ttf", "hand": "PermanentMarker-Regular.ttf", "stamp": "AlfaSlabOne-Regular.ttf"},
    "paper": False,          # true: the picture is a paper page (ledger, notebook): warm it and darken the edges
    "ink_boost": 0,          # 1-2: thicken thin drawn lines so they survive at 168 px
    "slip": True,            # words on a paper slip; turned off automatically when paper: true
    "slip_color": "#f3ead8",
    "series_tab": True,
    "size": [1920, 1080],
    "kinds": None,           # the channel's three kinds (default: correction, stamp, scene)
    "outline": None,         # vivid channels (pop look): words in `text_fill` with a thick outline in this colour,
    "text_fill": None,       # no paper slip (e.g. outline "#0d1030", text_fill "#ffffff")
}
POSITIONS = ("top-left", "top", "top-right", "left", "right", "bottom-left", "bottom")


def theme_of(channel_data: dict) -> dict:
    t = {**DEFAULT_THEME, **((channel_data or {}).get("thumbnails") or {})}
    t["fonts"] = {**DEFAULT_THEME["fonts"], **(t.get("fonts") or {})}
    if "slip" not in ((channel_data or {}).get("thumbnails") or {}):
        t["slip"] = not t["paper"] and not t.get("outline")
    return t


def kinds_of(channel_data: dict) -> list[str]:
    """The three thumbnail kinds this channel tests (channel.yaml → thumbnails.kinds)."""
    ks = [k for k in (((channel_data or {}).get("thumbnails") or {}).get("kinds") or []) if k in KINDS]
    return ks or list(DEFAULT_KINDS)


def _txt(d: ImageDraw.ImageDraw, xy, text: str, f, fill, theme: dict, size: float) -> None:
    """Text, with the channel's thick outline when it has one (pop look) — readable on any colour at 168 px."""
    if theme.get("outline"):
        d.text(xy, text, font=f, fill=rgb(theme.get("text_fill") or "#ffffff") + (255,),
               stroke_width=max(3, int(size * 0.09)), stroke_fill=rgb(theme["outline"]) + (255,))
    else:
        d.text(xy, text, font=f, fill=fill)


def rgb(c) -> tuple[int, int, int]:
    if isinstance(c, (list, tuple)):
        return tuple(int(v) for v in c[:3])
    c = str(c).lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for cand in (FONTS / name, Path(name)):
        try:
            return ImageFont.truetype(str(cand), max(8, int(size)))
        except OSError:
            continue
    for fallback in ("Anton-Regular.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(str(FONTS / fallback) if (FONTS / fallback).exists() else fallback, max(8, int(size)))
        except OSError:
            continue
    return ImageFont.load_default()


def word_count(text: str) -> int:
    return len([w for w in str(text or "").replace("…", " ").split() if w.strip(".,!?…-")])


# ---- picture preparation -------------------------------------------------------------------------------------------

def prepare(img: Image.Image, theme: dict, size: tuple[int, int]) -> Image.Image:
    """Resize to the canvas; for paper pages: thicker ink, a warmer, slightly darker page and darker edges so the page
    does not melt into YouTube's white (light mode) feed."""
    W, H = size
    img = img.convert("RGB").resize((W, H), Image.LANCZOS)
    boost = int(theme.get("ink_boost") or 0)
    if boost:
        k = 2 * round(boost * W / 1280) + 1
        img = ImageChops.darker(img, img.filter(ImageFilter.MinFilter(k)))
    if theme.get("paper"):
        img = ImageEnhance.Contrast(img).enhance(1.12)
        a = np.asarray(img).astype("float32") / 255
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        v = 1 - 0.22 * np.clip(d - 0.55, 0, 1) ** 1.4 / 0.8
        a = a * v[..., None] * np.array([0.97, 0.93, 0.85], "float32")
        img = Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))
    else:
        img = ImageEnhance.Contrast(img).enhance(1.06)
    return img


# ---- ink helpers ---------------------------------------------------------------------------------------------------

def _layer(size) -> Image.Image:
    return Image.new("RGBA", size, (0, 0, 0, 0))


def _ink(base: Image.Image, layer: Image.Image, theme: dict) -> Image.Image:
    """Paper pages: the ink is multiplied into the page (keeps the grain). Paintings: normal alpha paste."""
    base = base.convert("RGB")
    if theme.get("paper"):
        white = Image.new("RGB", base.size, (255, 255, 255))
        white.paste(layer.convert("RGB"), mask=layer.split()[3])
        return ImageChops.multiply(base, white)
    out = base.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def _rough_line(d: ImageDraw.ImageDraw, p0, p1, width: float, color, seed: int = 1) -> None:
    """A brush stroke: slightly wavy, three overlapping passes, round ends."""
    rnd = random.Random(seed)
    n = 24
    pts = []
    for i in range(n + 1):
        t = i / n
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t + math.sin(t * 5.5 + seed) * width * 0.25 + rnd.uniform(-1, 1) * width * 0.12
        pts.append((x, y))
    for k in range(3):
        off = (k - 1) * width * 0.12
        d.line([(x, y + off) for x, y in pts], fill=color, width=max(1, int(width * (1 - k * 0.22))), joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill=color)


def _fit(text: str, fname: str, start: int, max_w: float, min_size: int) -> tuple[ImageFont.FreeTypeFont, int]:
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    size = start
    while size > min_size:
        f = font(fname, size)
        if probe.textlength(text, font=f) <= max_w:
            return f, size
        size -= max(2, size // 25)
    return font(fname, min_size), min_size


def _anchor(pos: str, W: int, H: int, bw: float, bh: float, m: float) -> tuple[float, float]:
    """Top-left corner of a block of bw×bh at a named position. The bottom-right corner is never used (duration)."""
    pos = pos if pos in POSITIONS else "top-left"
    if pos in ("top-left", "bottom-left", "left"):
        x = m
    elif pos in ("top-right", "right"):
        x = W - m - bw
    else:
        x = (W - bw) / 2
    y =m if pos.startswith("top") else (H - m - bh if pos.startswith("bottom") else (H - bh) / 2)
    return x, y


def _slip(base: Image.Image, box, theme: dict, s: float, seed: int = 3) -> Image.Image:
    """A torn paper slip with a soft shadow behind words on a painting."""
    if not theme.get("slip"):
        return base
    x0, y0, x1, y1 = box
    pad = 22 * s
    lay = _layer(base.size)
    d = ImageDraw.Draw(lay)
    rnd = random.Random(seed)
    pts = []
    for i in range(13):
        pts.append((x0 - pad + (x1 - x0 + 2 * pad) * i / 12, y0 - pad + rnd.uniform(-4, 4) * s))
    for i in range(13):
        pts.append((x1 + pad - (x1 - x0 + 2 * pad) * i / 12, y1 + pad + rnd.uniform(-4, 4) * s))
    shadow = _layer(base.size)
    ImageDraw.Draw(shadow).polygon([(x + 8 * s, y + 10 * s) for x, y in pts], fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10 * s))
    d.polygon(pts, fill=rgb(theme.get("slip_color", "#f3ead8")) + (246,))
    out = base.convert("RGBA")
    out.alpha_composite(shadow)
    out.alpha_composite(lay.rotate(-1.2, resample=Image.BICUBIC, center=((x0 + x1) / 2, (y0 + y1) / 2)))
    return out.convert("RGB")


# ---- the three kinds -----------------------------------------------------------------------------------------------

def correction(base: Image.Image, myth: str, note: str, theme: dict, pos: str = "top-left") -> Image.Image:
    W, H = base.size
    s = W / 1280
    m = 52 * s
    ink, acc = rgb(theme["ink"]), rgb(theme["accent"])
    max_w = (W - 2 * m) * (0.62 if pos in ("left", "right") else 0.9)
    fm, sm = _fit(myth.upper(), theme["fonts"]["title"], int(190 * s), max_w, int(90 * s))
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    mb = probe.textbbox((0, 0), myth.upper(), font=fm)
    fn, sn = (_fit(note, theme["fonts"]["hand"], int(sm * 0.58), max_w, int(60 * s)) if note else (None, 0))
    nb = probe.textbbox((0, 0), note, font=fn) if note else (0, 0, 0, 0)
    gap = 24 * s
    bw = max(mb[2] - mb[0], nb[2] - nb[0] + 30 * s)
    bh = (mb[3] - mb[1]) + (gap + nb[3] - nb[1] if note else 0)
    x, y = _anchor(pos, W, H, bw, bh, m)
    base = _slip(base, (x, y, x + bw, y + bh), theme, s)
    lay = _layer(base.size)
    d = ImageDraw.Draw(lay)
    _txt(d, (x - mb[0], y - mb[1]), myth.upper(), fm, ink + (255,), theme, sm)
    mid = y + (mb[3] - mb[1]) * 0.52
    _rough_line(d, (x - 16 * s, mid + 10 * s), (x + mb[2] - mb[0] + 20 * s, mid - 14 * s), max(10 * s, sm / 9),
                acc + (240,), seed=3)
    out = _ink(base, lay, theme)
    if note:
        nl = _layer(base.size)
        ny = y + (mb[3] - mb[1]) + gap
        if theme.get("outline"):
            ImageDraw.Draw(nl).text((x + 10 * s - nb[0], ny - nb[1]), note, font=fn, fill=acc + (255,),
                                    stroke_width=max(3, int(sn * 0.09)), stroke_fill=rgb(theme["outline"]) + (255,))
        else:
            ImageDraw.Draw(nl).text((x + 10 * s - nb[0], ny - nb[1]), note, font=fn, fill=acc + (248,))
        out = _ink(out, nl.rotate(3, resample=Image.BICUBIC, center=(x, ny)), theme)
    return out


def stamp(base: Image.Image, word: str, theme: dict, pos: str = "top-left", angle: float | None = None,
          seed: int = 7) -> Image.Image:
    """A rubber stamp: double frame, slab letters, uneven ink (multiplied on paper, opaque-ish on paintings)."""
    W, H = base.size
    s = W / 1280
    word = (word or theme.get("stamp") or "WRONG").upper()
    f, size = _fit(word, theme["fonts"]["stamp"], int(118 * s), W * 0.42, int(60 * s))
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    tb = probe.textbbox((0, 0), word, font=f)
    pad = int(size * 0.32)
    w, h = tb[2] - tb[0] + 2 * pad, tb[3] - tb[1] + 2 * pad
    m = Image.new("L", (w + 40, h + 40), 0)
    d = ImageDraw.Draw(m)
    b = max(3, int(size * 0.075))
    d.rounded_rectangle([20, 20, 20 + w, 20 + h], radius=int(size * 0.12), outline=255, width=b)
    d.rounded_rectangle([20 + 2.2 * b, 20 + 2.2 * b, 20 + w - 2.2 * b, 20 + h - 2.2 * b], radius=int(size * 0.06),
                        outline=255, width=max(2, b // 2))
    d.text((20 + pad - tb[0], 20 + pad - tb[1]), word, font=f, fill=255)
    rng = np.random.default_rng(seed)
    noise = Image.fromarray((rng.random((m.size[1] // 4 + 1, m.size[0] // 4 + 1)) * 255).astype("uint8"))
    noise = np.asarray(noise.resize(m.size, Image.BILINEAR)).astype("float32") / 255
    speck = (rng.random((m.size[1], m.size[0])) > 0.06).astype("float32")
    grain = 0.38 if theme.get("paper") else 0.2       # on a painting the stamp needs more solid ink to read
    ink = np.asarray(m).astype("float32") / 255 * (1 - grain + grain * noise) * speck
    if angle is None:
        angle = -11 if "left" in pos else (11 if "right" in pos else -6)
    mask = Image.fromarray((np.clip(ink, 0, 1) * 235).astype("uint8")).rotate(angle, resample=Image.BICUBIC, expand=True)
    x, y = _anchor(pos, W, H, mask.size[0], mask.size[1], 30 * s)
    lay = _layer(base.size)
    col = Image.new("RGBA", mask.size, rgb(theme["accent"]) + (255,))
    col.putalpha(mask)
    lay.alpha_composite(col, (int(x), int(y)))
    if not theme.get("paper"):                     # on a painting the stamp needs a faint light ground to read
        glow = lay.split()[3].filter(ImageFilter.MaxFilter(int(9 * s) | 1)).filter(ImageFilter.GaussianBlur(6 * s))
        halo = Image.new("RGBA", base.size, (255, 255, 255, 0))
        halo.putalpha(glow.point(lambda v: int(v * 0.6)))
        out = base.convert("RGBA")
        out.alpha_composite(halo)
        base = out.convert("RGB")
    return _ink(base, lay, theme)


def scene(base: Image.Image, text: str, theme: dict, pos: str = "top") -> Image.Image:
    if not text:
        return base
    W, H = base.size
    s = W / 1280
    m = 44 * s
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    max_w = (W - 2 * m) * (0.55 if pos in ("left", "right") else 0.92)
    f, size = _fit(text, theme["fonts"]["hand"], int(150 * s), max_w, int(96 * s))
    lines = [text]
    if probe.textlength(text, font=f) > max_w and " " in text:   # two lines rather than tiny letters
        words = text.split()
        half = (len(words) + 1) // 2
        lines = [" ".join(words[:half]), " ".join(words[half:])]
        f, size = _fit(max(lines, key=len), theme["fonts"]["hand"], int(150 * s), max_w, int(80 * s))
    boxes = [probe.textbbox((0, 0), ln, font=f) for ln in lines]
    lh = max(b[3] - b[1] for b in boxes)
    bw = max(b[2] - b[0] for b in boxes)
    bh = lh * len(lines) + (len(lines) - 1) * 0.15 * lh
    x, y = _anchor(pos, W, H, bw, bh, m)
    base = _slip(base, (x, y, x + bw, y + bh), theme, s)
    lay = _layer(base.size)
    d = ImageDraw.Draw(lay)
    for i, (ln, b) in enumerate(zip(lines, boxes)):
        _txt(d, (x - b[0], y + i * 1.15 * lh - b[1]), ln, f, rgb(theme["ink"]) + (250,), theme, size)
    return _ink(base, lay.rotate(1.5, resample=Image.BICUBIC, center=(x, y)), theme)


# ---- object kinds (Ordinary Genius): the object is the hero, the hidden part is the question ------------------------

def _headline(base: Image.Image, text: str, theme: dict, pos: str, avoid=None) -> Image.Image:
    """Big bold words (title font; the channel's outline look when it has one), one or two lines."""
    if not text:
        return base
    W, H = base.size
    s = W / 1280
    m = 46 * s
    text = text.upper()
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    max_w = (W - 2 * m) * (0.5 if pos in ("left", "right") else 0.6)
    fname = theme["fonts"]["title"]
    f, size = _fit(text, fname, int(170 * s), max_w, int(104 * s))
    lines = [text]
    if probe.textlength(text, font=f) > max_w and " " in text:
        words = text.split()
        half = (len(words) + 1) // 2
        lines = [" ".join(words[:half]), " ".join(words[half:])]
        f, size = _fit(max(lines, key=lambda ln: probe.textlength(ln, font=f)), fname, int(170 * s), max_w, int(90 * s))
    boxes = [probe.textbbox((0, 0), ln, font=f) for ln in lines]
    lh = max(b[3] - b[1] for b in boxes)
    bw = max(b[2] - b[0] for b in boxes)
    bh = lh * len(lines) + (len(lines) - 1) * 0.16 * lh
    x, y = _anchor(pos, W, H, bw, bh, m)
    lay = _layer(base.size)
    d = ImageDraw.Draw(lay)
    for i, (ln, b) in enumerate(zip(lines, boxes)):
        lx = x + (bw - (b[2] - b[0])) * (0 if "left" in pos or pos == "left" else (1 if "right" in pos else 0.5))
        _txt(d, (lx - b[0], y + i * 1.16 * lh - b[1]), ln, f, rgb(theme["ink"]) + (255,), theme, size)
    if theme.get("outline"):                       # a hard drop shadow: reads on any colour at 168 px
        sh = lay.split()[3].point(lambda v: int(v * 0.55))
        shadow = Image.new("RGBA", base.size, rgb(theme["outline"]) + (0,))
        shadow.putalpha(sh)
        out = base.convert("RGBA")
        out.alpha_composite(shadow, (int(7 * s), int(9 * s)))
        out.alpha_composite(lay)
        return out.convert("RGB")
    return _ink(base, lay, theme)


def _pt(v: dict | None, key: str, default: float, sx: float) -> float:
    return float((v or {}).get(key, default)) * sx


def _ring(d: ImageDraw.ImageDraw, cx, cy, r, width, color, outline, ow) -> None:
    d.ellipse([cx - r - ow, cy - r - ow, cx + r + ow, cy + r + ow], outline=outline, width=int(width + 2 * ow))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=int(width))


def loupe(base: Image.Image, v: dict, text: str, theme: dict) -> Image.Image:
    """A magnifying lens: the small part at `focus` shown enlarged in a big round lens at `lens`, joined by a light cone."""
    W, H = base.size
    sx = W / 1920
    fx, fy, fr = _pt(v.get("focus"), "x", 1300, sx), _pt(v.get("focus"), "y", 620, sx), _pt(v.get("focus"), "r", 90, sx)
    lx, ly, lr = _pt(v.get("lens"), "x", 560, sx), _pt(v.get("lens"), "y", 600, sx), _pt(v.get("lens"), "r", 260, sx)
    acc, line = rgb(theme["accent"]), rgb(theme.get("outline") or theme["ink"])
    src = base.copy()
    # the light cone from the focus ring to the lens (tangent lines of the two circles)
    ang = math.atan2(ly - fy, lx - fx)
    dist = max(1.0, math.hypot(lx - fx, ly - fy))
    off = math.asin(max(-1.0, min(1.0, (lr - fr) / dist)))
    pts = []
    for sgn in (1, -1):
        a = ang + sgn * (math.pi / 2 + off)
        pts.append(((fx + fr * math.cos(a), fy + fr * math.sin(a)), (lx + lr * math.cos(a), ly + lr * math.sin(a))))
    cone = _layer(base.size)
    cd = ImageDraw.Draw(cone)
    cd.polygon([pts[0][0], pts[0][1], pts[1][1], pts[1][0]], fill=acc + (60,))
    for p0, p1 in pts:
        cd.line([p0, p1], fill=line + (255,), width=int(13 * sx))
        cd.line([p0, p1], fill=acc + (255,), width=int(6 * sx))
    out = base.convert("RGBA")
    out.alpha_composite(cone)
    # the lens: shadow, magnified picture, glass highlight, thick rim
    shadow = _layer(base.size)
    ImageDraw.Draw(shadow).ellipse([lx - lr + 14 * sx, ly - lr + 20 * sx, lx + lr + 14 * sx, ly + lr + 20 * sx],
                                   fill=line + (170,))
    out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(16 * sx)))
    box = (round(fx - fr), round(fy - fr), round(fx + fr), round(fy + fr))
    mag = src.crop(box).resize((round(2 * lr), round(2 * lr)), Image.LANCZOS)
    mag = ImageEnhance.Contrast(mag).enhance(1.08)
    mask = Image.new("L", mag.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, mag.size[0] - 1, mag.size[1] - 1], fill=255)
    glass = mag.convert("RGBA")
    hl = _layer(mag.size)
    hd = ImageDraw.Draw(hl)
    hd.arc([lr * 0.18, lr * 0.18, lr * 1.82, lr * 1.82], 200, 250, fill=(255, 255, 255, 150), width=int(lr * 0.07))
    glass.alpha_composite(hl)
    out.paste(glass, (round(lx - lr), round(ly - lr)), mask)
    rim = _layer(base.size)
    rd = ImageDraw.Draw(rim)
    hang = math.radians(float(v.get("handle", 135 if lx > W / 2 else 45)))
    if v.get("handle", True) is not False:     # a stubby handle: reads as "magnifying glass" at 168 px
        hx0, hy0 = lx + (lr + 10 * sx) * math.cos(hang), ly + (lr + 10 * sx) * math.sin(hang)
        hx1, hy1 = lx + (lr * 1.75) * math.cos(hang), ly + (lr * 1.75) * math.sin(hang)
        rd.line([(hx0, hy0), (hx1, hy1)], fill=line + (255,), width=int(lr * 0.30))
        rd.line([(hx0, hy0), (hx1, hy1)], fill=rgb(theme.get("handle_color") or "#ff6b5b") + (255,), width=int(lr * 0.2))
    _ring(rd, lx, ly, lr, max(10, lr * 0.09), acc + (255,), line + (255,), 7 * sx)
    _ring(rd, fx, fy, fr, max(6, 9 * sx), acc + (255,), line + (255,), 5 * sx)
    out.alpha_composite(rim)
    return _headline(out.convert("RGB"), text, theme, v.get("pos", "top-left"))


def xray(base: Image.Image, inside: Image.Image | None, v: dict, text: str, theme: dict) -> Image.Image:
    """Outside on one side of a glowing scan line, the same object's mechanism on the other."""
    W, H = base.size
    sx = W / 1920
    out = base.convert("RGBA")
    if inside is not None:
        ins = inside.convert("RGB").resize((W, H), Image.LANCZOS)
        if v.get("tint"):                          # an AI picture of the inside: turn it into a blueprint
            g = ImageEnhance.Contrast(ins.convert("L")).enhance(1.3)
            ins = Image.merge("RGB", [g.point(lambda p: int(p * 0.35)), g.point(lambda p: int(40 + p * 0.65)),
                                      g.point(lambda p: int(90 + p * 0.65))])
        sp = v.get("split") or {}
        x0 = float(sp.get("x", 1100)) * sx
        a = math.radians(float(sp.get("angle", 10)))
        top, bot = x0 + math.tan(a) * H / 2, x0 - math.tan(a) * H / 2
        right = (v.get("side") or "right") != "left"
        poly = [(top, 0), (W + 5, 0), (W + 5, H), (bot, H)] if right else [(-5, 0), (top, 0), (bot, H), (-5, H)]
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).polygon(poly, fill=255)
        out.paste(ins.convert("RGBA"), (0, 0), mask)
        acc = rgb(theme["accent"])
        glow = _layer(base.size)
        gd = ImageDraw.Draw(glow)
        gd.line([(top, 0), (bot, H)], fill=acc + (200,), width=int(46 * sx))
        out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(22 * sx)))
        ln = _layer(base.size)
        ld = ImageDraw.Draw(ln)
        ld.line([(top, 0), (bot, H)], fill=(255, 255, 255, 255), width=int(10 * sx))
        for k in range(1, 12):                     # scanner ticks along the line
            t = k / 12
            px, py = top + (bot - top) * t, H * t
            ld.line([(px - 18 * sx, py), (px + 18 * sx, py)], fill=acc + (255,), width=int(5 * sx))
        out.alpha_composite(ln)
    return _headline(out.convert("RGB"), text, theme, v.get("pos", "top-left"))


def tag(base: Image.Image, v: dict, text: str, theme: dict) -> Image.Image:
    """Rings around one small part and a thick arrow from a yellow part tag carrying ≤ 3 words."""
    W, H = base.size
    s, sx = W / 1280, W / 1920
    px, py = _pt(v.get("point"), "x", 1300, sx), _pt(v.get("point"), "y", 640, sx)
    pr = _pt(v.get("point"), "r", 70, sx)
    acc, line = rgb(theme["accent"]), rgb(theme.get("outline") or theme["ink"])
    pos = v.get("pos", "top-left")
    words = (text or "?").upper()
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    f, size = _fit(words, theme["fonts"]["title"], int(150 * s), W * 0.5, int(92 * s))
    tb = probe.textbbox((0, 0), words, font=f)
    pad = 0.3 * size
    bw, bh = tb[2] - tb[0] + 2 * pad, tb[3] - tb[1] + 1.4 * pad
    x, y = _anchor(pos, W, H, bw, bh, 50 * s)
    lay = _layer(base.size)
    d = ImageDraw.Draw(lay)
    # arrow from the tag edge to just outside the rings, a gentle curve
    sx0, sy0 = x + bw / 2, y + bh / 2
    ang = math.atan2(py - sy0, px - sx0)
    ex, ey = px - (pr * 1.55) * math.cos(ang), py - (pr * 1.55) * math.sin(ang)
    hx = max(abs(bw / 2 / max(1e-6, math.cos(ang))) if abs(math.cos(ang)) > 1e-6 else 1e9, 0)
    hy = abs(bh / 2 / math.sin(ang)) if abs(math.sin(ang)) > 1e-6 else 1e9
    r0 = min(hx, hy) + 18 * s
    bx0, by0 = sx0 + r0 * math.cos(ang), sy0 + r0 * math.sin(ang)
    mx, my = (bx0 + ex) / 2, (by0 + ey) / 2
    nx, ny = -math.sin(ang), math.cos(ang)
    bend = float(v.get("bend", 0.18)) * math.hypot(ex - bx0, ey - by0)
    cx, cy = mx + nx * bend, my + ny * bend
    curve = [((1 - t) ** 2 * bx0 + 2 * (1 - t) * t * cx + t * t * ex, (1 - t) ** 2 * by0 + 2 * (1 - t) * t * cy + t * t * ey)
             for t in [i / 40 for i in range(41)]]
    head_a = math.atan2(ey - curve[-4][1], ex - curve[-4][0])
    hl, hw = 70 * s, 46 * s
    tip = (ex + 14 * s * math.cos(head_a), ey + 14 * s * math.sin(head_a))
    back = (tip[0] - hl * math.cos(head_a), tip[1] - hl * math.sin(head_a))
    head = [tip, (back[0] + hw * math.sin(head_a), back[1] - hw * math.cos(head_a)),
            (back[0] - hw * math.sin(head_a), back[1] + hw * math.cos(head_a))]
    body = curve[:-5]
    d.line(body, fill=line + (255,), width=int(34 * s), joint="curve")
    d.polygon(head, fill=line + (255,), outline=line + (255,), width=int(10 * s))
    d.line(body, fill=acc + (255,), width=int(20 * s), joint="curve")
    d.polygon(head, fill=acc + (255,))
    for rr, w in ((pr, 11 * s), (pr * 1.32, 7 * s)):
        _ring(d, px, py, rr, w, acc + (255,), line + (255,), 4 * s)
    # the tag: a yellow pill with a navy outline and navy letters, a little tilted
    tagl = _layer(base.size)
    td = ImageDraw.Draw(tagl)
    td.rounded_rectangle([x + 8 * s, y + 10 * s, x + bw + 8 * s, y + bh + 10 * s], radius=int(bh * 0.28), fill=line + (255,))
    td.rounded_rectangle([x, y, x + bw, y + bh], radius=int(bh * 0.28), fill=acc + (255,), outline=line + (255,),
                         width=int(7 * s))
    td.text((x + pad - tb[0], y + 0.7 * pad - tb[1]), words, font=f, fill=line + (255,))
    tagl = tagl.rotate(float(v.get("angle", -3)), resample=Image.BICUBIC, center=(x + bw / 2, y + bh / 2))
    out = base.convert("RGBA")
    out.alpha_composite(lay)
    out.alpha_composite(tagl)
    return out.convert("RGB")



def series_tab(base: Image.Image, color, theme: dict) -> Image.Image:
    """A coloured index tab on the top edge: the series at a glance, no words."""
    if not color or not theme.get("series_tab", True):
        return base
    W = base.size[0]
    s = W / 1280
    lay = _layer(base.size)
    ImageDraw.Draw(lay).rounded_rectangle([W - 210 * s, -30 * s, W - 70 * s, 46 * s], radius=int(14 * s),
                                          fill=rgb(color) + (235,))
    return _ink(base, lay, theme)


def compose_kind(base: Image.Image, v: dict, texts: dict, theme: dict, series_color=None,
                 inside: Image.Image | None = None) -> Image.Image:
    """v: one project.yaml thumbnail entry (kind + positions); texts: {myth, note, stamp, text} in the output language;
    inside: the second picture of an `xray` thumbnail."""
    size = tuple(theme.get("size") or (1920, 1080))
    img = prepare(base, theme, size)
    kind = v.get("kind")
    if kind == "correction":
        img = correction(img, texts.get("myth") or texts.get("text") or "", texts.get("note") or "", theme,
                         v.get("pos", "top-left"))
    elif kind == "stamp":
        img = stamp(img, texts.get("stamp") or "", theme, v.get("pos", "top-left"), v.get("angle"))
    elif kind == "scene":
        img = scene(img, texts.get("text") or "", theme, v.get("pos", "top"))
    elif kind == "loupe":
        img = loupe(img, v, texts.get("text") or "", theme)
    elif kind == "xray":
        img = xray(img, prepare(inside, theme, size) if inside is not None else None, v, texts.get("text") or "", theme)
    elif kind == "tag":
        img = tag(img, v, texts.get("text") or "", theme)
    return series_tab(img, series_color, theme)


def lint(v: dict, texts: dict) -> list[str]:
    """Rules from docs/THUMBNAILS.md that a renderer can check."""
    warn = []
    kind = v.get("kind")
    if kind == "correction":
        if word_count(texts.get("myth")) > 3:
            warn.append("inanış en fazla 3 kelime olmalı")
        if word_count(texts.get("note")) > 3:
            warn.append("not en fazla 3 kelime olmalı")
    elif kind in ("scene", "loupe", "xray", "tag") and word_count(texts.get("text")) > 3:
        warn.append("yazı en fazla 3 kelime olmalı")
    if kind == "loupe" and not (v.get("focus") and v.get("lens")):
        warn.append("büyüteç için `focus: {x, y, r}` ve `lens: {x, y, r}` gerekli")
    if kind == "xray" and not v.get("inside"):
        warn.append("röntgen için `inside:` (nesnenin içi, aynı yerde ve boyutta) gerekli")
    if kind == "tag" and not v.get("point"):
        warn.append("etiket için `point: {x, y}` (okun gösterdiği parça) gerekli")
    if any(ch.isdigit() for t in texts.values() for ch in str(t or "")) and not v.get("claim"):
        warn.append("yazıda sayı var ama `claim:` (iddia numarası) yok")
    if v.get("pos") == "bottom-right":
        warn.append("sağ alt köşeye süre etiketi gelir; başka konum seç")
    return warn
