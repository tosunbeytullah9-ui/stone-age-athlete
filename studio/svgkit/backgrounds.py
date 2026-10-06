"""Plain backgrounds for charts. Each returns (fill colour, svg body, baseline_y)."""
from __future__ import annotations

from .style import INK, W, c, circle, line, path, rect

BACKGROUNDS = {}


def bg(name):
    def deco(fn):
        BACKGROUNDS[name] = fn
        return fn
    return deco


def _floor(y, color):
    return rect(-10, y, W + 20, 1100 - y, color, w=0) + line([(0, y), (W, y)], 6)


@bg("plain_warm")
def plain_warm(**_):
    return "sky_warm", "", 900


@bg("plain_cool")
def plain_cool(**_):
    return "wall_cool", "", 900


def get(name: str, **opts):
    fn = BACKGROUNDS.get(name)
    if fn is None:
        raise ValueError(f"unknown background: {name} (options: {', '.join(BACKGROUNDS)})")
    return fn(**opts)
