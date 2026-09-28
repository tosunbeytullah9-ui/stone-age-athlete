"""Finishing layer: on-screen text per language, chart animation, sound effects, outro, vertical framing.

Images stay text-free (shared by every language). Text is drawn at render time, per language:

  shot.overlay:
    kind: stat | label | cite      stat = big number/phrase, label = caption band, cite = small source line
    text: "11–16%"                 primary language (numbers usually need no translation)
    i18n: {tr: "%11–16"}           optional per-language text
    pos: top | bottom | center      optional (defaults: stat top, label bottom, cite bottom-left)

Claims with `on_screen: true` get an automatic `cite` line on their first shot.
"""
from __future__ import annotations

import copy
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ANIM_FRAMES = 8
CHART_PROPS = {"bar_chart": ("values",), "line_chart": ("values", "values2"), "meter": ("value",),
               "gauge": ("value",), "battery": ("value",), "pie": ("value",)}


# ------------------------------------------------------------------ overlays
def _font(size: int):
    from .thumbnails import _font as f
    return f(size)


def _regular(size: int):
    from .render import _font as f
    return f(size)


def overlay_text(ov: dict, lang: str, primary: str) -> str:
    if lang != primary and (ov.get("i18n") or {}).get(lang):
        return str(ov["i18n"][lang])
    return str(ov.get("text") or "")


def draw_overlay(img: Image.Image, ov: dict, text: str) -> Image.Image:
    if not text:
        return img
    img = img.convert("RGB").copy()
    W, H = img.size
    d = ImageDraw.Draw(img, "RGBA")
    kind = ov.get("kind", "label")
    pos = ov.get("pos") or {"stat": "top", "label": "bottom", "cite": "bottom"}.get(kind, "bottom")
    if kind == "cite":
        f = _regular(max(22, H // 40))
        tw = d.textlength(text, font=f)
        pad, y = 14, H - H // 11
        d.rounded_rectangle([40, y - pad, 40 + tw + 2 * pad, y + f.size + pad], 10, fill=(20, 20, 20, 170))
        d.text((40 + pad, y), text, font=f, fill="#f4efe2")
        return img
    size = H // 7 if kind == "stat" else H // 16
    f = _font(size)
    while d.textlength(text, font=f) > W * 0.86 and size > 20:
        size -= 4
        f = _font(size)
    y = {"top": H // 9, "center": H // 2, "bottom": H - H // 6}.get(pos, H - H // 6)
    stroke = max(4, size // 10)
    if kind == "label":
        tw = d.textlength(text, font=f)
        d.rounded_rectangle([W / 2 - tw / 2 - 28, y - size * 0.75, W / 2 + tw / 2 + 28, y + size * 0.75], 18,
                            fill=(255, 250, 238, 225), outline=(27, 27, 27, 255), width=5)
        d.text((W / 2, y), text, font=f, fill="#1b1b1b", anchor="mm")
    else:
        d.text((W / 2 + 5, y + 7), text, font=f, fill="#000000", anchor="mm", stroke_width=stroke, stroke_fill="#000000")
        d.text((W / 2, y), text, font=f, fill=ov.get("color", "#ffd84d"), anchor="mm", stroke_width=stroke,
               stroke_fill="#111111")
    return img


def short_cite(src: dict) -> str:
    who = str(src.get("authors") or src.get("title") or src.get("id", ""))
    first = re.split(r"[ ,]", who.strip())[0] if who else ""
    etal = " et al." if ("," in who or "et al" in who) else ""
    parts = [f"{first}{etal}".strip(), str(src.get("year") or ""), str(src.get("venue") or "")]
    return " · ".join(p for p in parts if p)


def auto_overlays(project) -> dict[str, dict]:
    """{shot id: overlay} from claims marked on_screen (first listed shot of each claim)."""
    from .claims import library_index, load_claims
    lib = library_index()
    out: dict[str, dict] = {}
    for c in load_claims(project)["claims"]:
        if c.get("on_screen") and c.get("shots") and c.get("source") in lib:
            out.setdefault(c["shots"][0], {"kind": "cite", "text": short_cite(lib[c["source"]])})
    return out


def apply_overlay(src: Path, overlay: dict | None, lang: str, primary: str, out: Path) -> Path:
    if not overlay:
        return src
    text = overlay_text(overlay, lang, primary)
    if not text:
        return src
    draw_overlay(Image.open(src), overlay, text).save(out)
    return out


# ------------------------------------------------------------------ chart animation
def _ease(t: float) -> float:
    return 1 - (1 - t) ** 3


def animated_visuals(visual) -> list[dict]:
    """Intermediate recipes where chart values grow from 0 (empty list when nothing to animate)."""
    if not isinstance(visual, dict) or visual.get("animate") is False:
        return []
    props = visual.get("props") or []
    if not any(isinstance(p, dict) and p.get("type") in CHART_PROPS for p in props):
        return []
    out = []
    for k in range(1, ANIM_FRAMES + 1):
        e = _ease(k / (ANIM_FRAMES + 1))
        v = copy.deepcopy(visual)
        for p in v["props"]:
            keys = CHART_PROPS.get(p.get("type"), ())
            for key in keys:
                if key in p and isinstance(p[key], (list, tuple)):
                    p[key] = [float(x) * e for x in p[key]]
                elif key in p or key == "value":
                    p[key] = float(p.get(key, 0.5)) * e
        out.append(v)
    return out


# ------------------------------------------------------------------ sound effects
SR = 48000


def _whoosh(dur=0.45, seed=1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * dur)
    noise = rng.standard_normal(n)
    t = np.linspace(0, 1, n)
    out = np.zeros(n)
    acc = 0.0
    for i in range(n):                      # one-pole low-pass whose cutoff sweeps up then down
        a = 0.02 + 0.25 * math.sin(math.pi * t[i])
        acc += a * (noise[i] - acc)
        out[i] = acc
    env = np.sin(np.pi * t) ** 2
    out = out * env
    return (out / (np.abs(out).max() + 1e-9) * 0.6).astype("float32")


def _pop(dur=0.09) -> np.ndarray:
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    f = 880 - 380 * t / dur
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45)
    return (x * 0.55).astype("float32")


def _load_sfx(name: str, assets: Path) -> np.ndarray:
    """assets/sfx/<name>.wav overrides the built-in synthesized sound."""
    f = assets / "sfx" / f"{name}.wav"
    if f.exists():
        import soundfile as sf
        x, sr = sf.read(f, dtype="float32")
        if x.ndim > 1:
            x = x.mean(axis=1)
        if sr != SR:
            idx = np.linspace(0, len(x) - 1, int(len(x) * SR / sr))
            x = np.interp(idx, np.arange(len(x)), x).astype("float32")
        return x
    return _whoosh() if name == "whoosh" else _pop()


def _bg(shot: dict):
    v = shot.get("visual")
    return v.get("bg") if isinstance(v, dict) else None


def sfx_events(shots_in_order: list[dict], timing: list[dict]) -> list[tuple[float, str]]:
    """whoosh on a change of scene, pop when a new object appears in the same scene."""
    events = []
    for i in range(1, len(timing)):
        a, b = shots_in_order[i - 1], shots_in_order[i]
        if _bg(a) and _bg(b) and _bg(a) != _bg(b):
            events.append((max(0.0, timing[i]["start"] - 0.18), "whoosh"))
        elif _bg(b) and isinstance(b.get("visual"), dict) and isinstance(a.get("visual"), dict):
            na, nb = len(a["visual"].get("props") or []), len(b["visual"].get("props") or [])
            if nb > na:
                events.append((timing[i]["start"] + 0.04, "pop"))
    return events


def build_sfx_track(events: list[tuple[float, str]], total: float, assets: Path, out: Path) -> Path | None:
    if not events:
        return None
    import soundfile as sf
    track = np.zeros(int((total + 1) * SR), dtype="float32")
    cache: dict[str, np.ndarray] = {}
    for t, name in events:
        s = cache.setdefault(name, _load_sfx(name, assets))
        a = int(t * SR)
        b = min(len(track), a + len(s))
        if a < len(track):
            track[a:b] += s[: b - a]
    sf.write(out, np.clip(track, -1, 1), SR, subtype="PCM_16")
    return out


# ------------------------------------------------------------------ outro
def outro_visual(mascot: dict) -> dict:
    m = dict(mascot or {"pose": "point"})
    m.update({"x": 520, "flip": False})
    return {"bg": "plain_warm", "figures": [m]}


def draw_outro(base: Image.Image, text: str, sub: str) -> Image.Image:
    """End-screen layout: two video slots and a subscribe circle where YouTube's end-screen elements go."""
    img = base.convert("RGB").copy()
    W, H = img.size
    d = ImageDraw.Draw(img, "RGBA")
    for (x0, y0) in ((1010, 150), (1010, 560)):
        d.rounded_rectangle([x0, y0, x0 + 780, y0 + 380], 24, fill=(255, 255, 255, 120), outline="#1b1b1b", width=6)
    d.ellipse([760, 780, 940, 960], fill=(255, 255, 255, 120), outline="#1b1b1b", width=6)
    f = _font(76)
    d.text((80, 90), text.upper(), font=f, fill="#ffd84d", stroke_width=8, stroke_fill="#111111")
    if sub:
        d.text((84, 190), sub, font=_regular(40), fill="#1b1b1b")
    return img


# ------------------------------------------------------------------ vertical (Shorts)
def focus_x(visual) -> float:
    if not isinstance(visual, dict):
        return 960.0
    fr = visual.get("frame")
    if isinstance(fr, dict) and "x" in fr:
        return float(fr["x"])
    xs = [float(f.get("x", 960)) for f in visual.get("figures") or [] if isinstance(f, dict)]
    return sum(xs) / len(xs) if xs else 960.0


def caption_frame(img: Image.Image, title: str, caption: str) -> Image.Image:
    """Shorts frame: title band at the top, spoken words in the middle-lower third (clear of the Shorts UI)."""
    from .thumbnails import _wrap
    img = img.convert("RGB").copy()
    W, H = img.size
    d = ImageDraw.Draw(img, "RGBA")
    if title:
        f = _font(62)
        lines = _wrap(d, title.upper(), f, W - 120)[:3]
        top = 150
        d.rectangle([0, top - 30, W, top + len(lines) * 74 + 20], fill=(17, 17, 17, 200))
        for i, ln in enumerate(lines):
            d.text((W // 2, top + i * 74), ln, font=f, fill="#ffd84d", anchor="ma")
    if caption:
        f = _font(72)
        lines = _wrap(d, caption, f, W - 140)[:3]
        y = int(H * 0.62)
        for ln in lines:
            d.text((W // 2, y), ln, font=f, fill="#ffffff", anchor="ma", stroke_width=9, stroke_fill="#000000")
            y += 88
    return img
