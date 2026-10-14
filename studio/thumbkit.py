"""Thumbnail kinds shared by every channel (docs/THUMBNAILS.md).

  correction  the belief in big letters, struck through by hand in the accent colour, a short handwritten note under it
  stamp       one picture, one rubber stamp ("WRONG", "MYTH", ...) on its empty side, no other words
  scene       a moment from the video with at most three handwritten words

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
KINDS = ("correction", "stamp", "scene")
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
}
POSITIONS = ("top-left", "top", "top-right", "left", "right", "bottom-left", "bottom")


def theme_of(channel_data: dict) -> dict:
    t = {**DEFAULT_THEME, **((channel_data or {}).get("thumbnails") or {})}
    t["fonts"] = {**DEFAULT_THEME["fonts"], **(t.get("fonts") or {})}
    if "slip" not in ((channel_data or {}).get("thumbnails") or {}):
        t["slip"] = not t["paper"]
    return t


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
    d.text((x - mb[0], y - mb[1]), myth.upper(), font=fm, fill=ink + (255,))
    mid = y + (mb[3] - mb[1]) * 0.52
    _rough_line(d, (x - 16 * s, mid + 10 * s), (x + mb[2] - mb[0] + 20 * s, mid - 14 * s), max(10 * s, sm / 9),
                acc + (240,), seed=3)
    out = _ink(base, lay, theme)
    if note:
        nl = _layer(base.size)
        ny = y + (mb[3] - mb[1]) + gap
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
        d.text((x - b[0], y + i * 1.15 * lh - b[1]), ln, font=f, fill=rgb(theme["ink"]) + (250,))
    return _ink(base, lay.rotate(1.5, resample=Image.BICUBIC, center=(x, y)), theme)


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


def compose_kind(base: Image.Image, v: dict, texts: dict, theme: dict, series_color=None) -> Image.Image:
    """v: one project.yaml thumbnail entry (kind + positions); texts: {myth, note, stamp, text} in the output language."""
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
    elif kind == "scene" and word_count(texts.get("text")) > 3:
        warn.append("sahne yazısı en fazla 3 kelime olmalı")
    if any(ch.isdigit() for t in texts.values() for ch in str(t or "")) and not v.get("claim"):
        warn.append("yazıda sayı var ama `claim:` (iddia numarası) yok")
    if v.get("pos") == "bottom-right":
        warn.append("sağ alt köşeye süre etiketi gelir; başka konum seç")
    return warn
