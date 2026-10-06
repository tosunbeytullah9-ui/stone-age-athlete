"""Chart elements. Every prop: {type, x, y, scale?, ...options}.
For things that stand on the baseline, (x, y) is the bottom-centre; for floating ones (marks, dials) the centre.
"""
from __future__ import annotations

import math

from .style import INK, RED, c, circle, line, path, polar, rect

PROPS = {}
FLOATING: set[str] = set()   # props whose (x, y) is the centre (everything else stands on y)


def prop(name, floating=False):
    def deco(fn):
        PROPS[name] = fn
        if floating:
            FLOATING.add(name)
        return fn
    return deco


@prop("bar_chart")
def bar_chart(x, y, s=1.0, values=(1.0, 0.6), colors=("ochre", "water"), w=680, h=540, **_):
    """Bars growing from baseline y. values relative (max 1.0)."""
    n = len(values)
    bw = w * s / (n * 1.6)
    out = [line([(x - w * s / 2, y), (x + w * s / 2, y)], 7 * s)]
    for i, v in enumerate(values):
        bx = x - w * s / 2 + bw * 0.3 + i * bw * 1.6
        bh = h * s * float(v)
        col = colors[i % len(colors)] if colors else "ochre"
        out.append(rect(bx, y - bh, bw, bh, col, rx=6 * s, w=6 * s))
    return "".join(out)


@prop("arrow")
def arrow(x, y, s=1.0, to=(0, 0), color=INK, **_):
    x2, y2 = to
    a = math.atan2(y2 - y, x2 - x)
    L = 28 * s
    p1 = (x2 - L * math.cos(a - 0.5), y2 - L * math.sin(a - 0.5))
    p2 = (x2 - L * math.cos(a + 0.5), y2 - L * math.sin(a + 0.5))
    return line([(x, y), (x2, y2)], 7 * s, color=c(color)) + line([p1, (x2, y2), p2], 7 * s, color=c(color))


@prop("check")
def check(x, y, s=1.0, **_):
    return line([(x - 40 * s, y), (x - 10 * s, y + 35 * s), (x + 50 * s, y - 40 * s)], 14 * s, color=c("good"))


@prop("cross")
def cross(x, y, s=1.0, **_):
    return (line([(x - 40 * s, y - 40 * s), (x + 40 * s, y + 40 * s)], 14 * s, color=RED)
            + line([(x + 40 * s, y - 40 * s), (x - 40 * s, y + 40 * s)], 14 * s, color=RED))

FLOATING.update({"check", "cross", "arrow"})

from . import props_charts  # noqa: E402,F401  (registers line_chart, pie, gauge, meter, battery, timeline, people, balance)
