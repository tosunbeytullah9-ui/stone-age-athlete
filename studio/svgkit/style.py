"""Shared drawing style: ink, palette, hand-drawn wobble and paper texture."""
from __future__ import annotations

import math

W, H = 1920, 1080
INK = "#1b1b1b"
RED = "#d8342c"

PALETTE = {
    # ancient / warm
    "sky_warm": "#f0dfb8", "sand": "#d8b684", "olive": "#a9a56f", "ochre": "#e3a447",
    "clay": "#b98b52", "stone": "#8c8377", "stone_dark": "#6c645a", "grain": "#e7c45f",
    "bark": "#7a5a3a", "leaf": "#7f8f4e", "hide": "#a0764a", "cave": "#5b4636", "fire": "#f08a2c",
    # modern / cool
    "wall_cool": "#cbd5dc", "floor_cool": "#9aabb6", "furniture": "#6b7e8b", "metal": "#37474f",
    "night": "#34466b", "screen": "#bfe8ff",
    # neutral
    "paper": "#f6eedc", "bone": "#fbf3df", "white": "#ffffff", "water": "#8fb3c9", "sweat": "#9ec9e2",
    "good": "#6f9a52", "bad": RED,
    # added for the extended kit (water, snow, anatomy, metals)
    "sea": "#6f9fc0", "deep": "#3f6f94", "foam": "#e6f2f7", "snow": "#f4f6f4", "ice": "#cfe4ee",
    "rock_cool": "#8e979c", "grass": "#93a95c", "track": "#c4613f",
    "flesh": "#e0685c", "organ": "#c9423b", "vein": "#4f7fb3", "pink": "#f0a7a8", "fat": "#f2d27a",
    "bronze": "#c9a24a", "steel": "#aeb6bb", "cloth": "#e8dcc0", "fur": "#6b4a2e",
}


_BASE = dict(PALETTE)


class use_palette:
    """Temporarily apply a channel's palette overrides: with use_palette({"sky_warm": "#..."}): ..."""

    def __init__(self, overrides: dict | None):
        self.overrides = overrides or {}

    def __enter__(self):
        PALETTE.clear()
        PALETTE.update(_BASE)
        PALETTE.update(self.overrides)
        return self

    def __exit__(self, *exc):
        PALETTE.clear()
        PALETTE.update(_BASE)


def c(name_or_hex: str) -> str:
    return PALETTE.get(name_or_hex, name_or_hex)


def line(pts, w=8, color=INK, dash=None) -> str:
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{w:.1f}" '
            f'stroke-linecap="round" stroke-linejoin="round"{d}/>')


def circle(cx, cy, r, fill="#fff", w=7, stroke=INK) -> str:
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{c(fill)}" stroke="{stroke}" stroke-width="{w:.1f}"/>'


def rect(x, y, w_, h_, fill, rx=0, w=7) -> str:
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w_:.1f}" height="{h_:.1f}" rx="{rx}" '
            f'fill="{c(fill)}" stroke="{INK}" stroke-width="{w:.1f}"/>')


def path(d, fill="none", w=7, stroke=INK, extra="") -> str:
    return f'<path d="{d}" fill="{c(fill)}" stroke="{stroke}" stroke-width="{w:.1f}" stroke-linejoin="round" stroke-linecap="round"{extra}/>'


def polar(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def document(body: str, bg: str = "#f0dfb8", seed: int = 7, wobble: float = 5.0) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <filter id="rough" x="-5%" y="-5%" width="110%" height="110%">
    <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="{seed}" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="{wobble}" xChannelSelector="R" yChannelSelector="G"/>
  </filter>
  <filter id="paper" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="2"/>
    <feColorMatrix type="saturate" values="0"/>
  </filter>
</defs>
<rect width="{W}" height="{H}" fill="{c(bg)}"/>
<g filter="url(#rough)">{body}</g>
<rect width="{W}" height="{H}" filter="url(#paper)" opacity="0.07" style="mix-blend-mode:multiply"/>
</svg>'''


def ellipse(cx, cy, rx, ry, fill="#fff", w=7, rot=0, stroke=INK, extra="") -> str:
    t = f' transform="rotate({rot:.1f} {cx:.1f} {cy:.1f})"' if rot else ""
    return (f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{c(fill)}" '
            f'stroke="{stroke}" stroke-width="{w:.1f}"{t}{extra}/>')


def band(pts, width, fill, outline=5.0) -> str:
    """Thick stroke with an ink outline (animal legs, tubes, sleeves)."""
    return line(pts, width + 2 * outline, color=INK) + line(pts, width, color=c(fill))


def poly(pts, fill="none", w=7) -> str:
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
    return path(d, fill=fill, w=w)


def dot(x, y, r, color=INK) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{c(color)}"/>'
