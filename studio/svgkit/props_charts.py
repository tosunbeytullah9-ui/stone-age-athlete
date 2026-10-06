"""Charts and meters. Values are relative (0..1) — pictures of numbers, never digits.
line_chart / timeline: y = baseline (like bar_chart). pie, gauge, meter, battery, people: centre.
balance stands on the floor."""
from __future__ import annotations

import math

from .props import prop
from .style import INK, RED, c, circle, dot, line, path, polar, rect


def _clamp(v):
    return max(0.0, min(1.0, float(v)))


@prop("line_chart")
def line_chart(x, y, s=1.0, values=(0.2, 0.4, 0.35, 0.7, 0.9), values2=None, color=RED, color2="water",
               w=760, h=480, **_):
    """Axes + line through `values` (0..1, left→right). Optional second line `values2`. y = baseline."""
    x0, x1 = x - w * s / 2, x + w * s / 2
    out = [line([(x0, y - h * s - 20 * s), (x0, y), (x1 + 20 * s, y)], 7 * s)]
    for vals, col in ((values2, color2), (values, color)):
        if not vals:
            continue
        n = len(vals)
        pts = [(x0 + 30 * s + i * (w - 60) * s / max(1, n - 1), y - _clamp(v) * h * s) for i, v in enumerate(vals)]
        out.append(line(pts, 9 * s, color=c(col)))
        out += [circle(px, py, 11 * s, fill=col, w=5 * s) for px, py in pts]
    return "".join(out)


@prop("pie", floating=True)
def pie(x, y, s=1.0, value=0.25, colors=("ochre", "#fbfbf7"), **_):
    """Pie with one highlighted wedge = value (0..1)."""
    r = 130 * s
    v = _clamp(value)
    out = [circle(x, y, r, fill=colors[1] if len(colors) > 1 else "#fbfbf7", w=8 * s)]
    if v >= 0.999:
        out.append(circle(x, y, r, fill=colors[0], w=8 * s))
    elif v > 0:
        ex, ey = polar(x, y, r, -90 + 360 * v)
        big = 1 if v > 0.5 else 0
        out.append(path(f"M{x},{y} L{x},{y - r} A{r},{r} 0 {big} 1 {ex},{ey} Z", fill=colors[0], w=7 * s))
    return "".join(out)


@prop("gauge", floating=True)
def gauge(x, y, s=1.0, value=0.5, **_):
    """Half-dial from green (low) to red (high); needle at value 0..1. (x, y) = pivot."""
    r = 150 * s
    zones = (("good", 180, 240), ("ochre", 240, 300), (RED, 300, 360))
    out = []
    for col, a0, a1 in zones:
        p0, p1 = polar(x, y, r, a0), polar(x, y, r, a1)
        q0, q1 = polar(x, y, r * 0.62, a1), polar(x, y, r * 0.62, a0)
        out.append(path(f"M{p0[0]},{p0[1]} A{r},{r} 0 0 1 {p1[0]},{p1[1]} L{q0[0]},{q0[1]} "
                        f"A{r * 0.62},{r * 0.62} 0 0 0 {q1[0]},{q1[1]} Z", fill=col, w=6 * s))
    out.append(line([(x, y), polar(x, y, r * 0.9, 180 + 180 * _clamp(value))], 10 * s))
    out.append(circle(x, y, 16 * s, fill=INK, w=2))
    return "".join(out)


@prop("meter", floating=True)
def meter(x, y, s=1.0, value=0.5, color="good", w=420, **_):
    """Horizontal progress bar filled to value (0..1)."""
    W = w * s
    out = [rect(x - W / 2, y - 30 * s, W, 60 * s, "#fbfbf7", rx=30 * s, w=7 * s)]
    v = _clamp(value)
    if v > 0:
        out.append(rect(x - W / 2 + 8 * s, y - 22 * s, max(44 * s, (W - 16 * s) * v), 44 * s, color, rx=22 * s, w=0))
    out.append(rect(x - W / 2, y - 30 * s, W, 60 * s, "none", rx=30 * s, w=7 * s))
    return "".join(out)


@prop("battery", floating=True)
def battery(x, y, s=1.0, value=0.8, **_):
    """Energy battery; value 0..1 (red when low)."""
    v = _clamp(value)
    col = "good" if v > 0.5 else ("ochre" if v > 0.2 else RED)
    out = [rect(x - 130 * s, y - 65 * s, 260 * s, 130 * s, "#fbfbf7", rx=18 * s, w=8 * s),
           rect(x + 130 * s, y - 28 * s, 26 * s, 56 * s, INK, rx=6 * s, w=4 * s)]
    if v > 0:
        out.append(rect(x - 115 * s, y - 50 * s, 230 * s * v, 100 * s, col, rx=10 * s, w=0))
    return "".join(out)


@prop("timeline")
def timeline(x, y, s=1.0, n=5, highlight=-1, w=1000, **_):
    """Horizontal time arrow with n ticks; highlight = index of the tick marked in red (-1: none).
    y = the line. Put icons above the ticks: tick i is at x − w/2 + (i + 0.5)·w/n."""
    W = w * s
    n = max(1, int(n))
    out = [line([(x - W / 2, y), (x + W / 2, y)], 8 * s),
           line([(x + W / 2 - 30 * s, y - 20 * s), (x + W / 2, y), (x + W / 2 - 30 * s, y + 20 * s)], 8 * s)]
    for i in range(n):
        tx = x - W / 2 + (i + 0.5) * W / n
        if i == int(highlight):
            out.append(circle(tx, y, 22 * s, fill=RED, w=6 * s))
        else:
            out.append(line([(tx, y - 22 * s), (tx, y + 22 * s)], 7 * s))
    return "".join(out)


@prop("people", floating=True)
def people(x, y, s=1.0, n=10, k=3, color=RED, cols=5, **_):
    """Pictogram of n little people, the first k highlighted ("3 in 10")."""
    n, cols = max(1, int(n)), max(1, int(cols))
    rows = math.ceil(n / cols)
    dx, dy = 70 * s, 120 * s
    out = []
    for i in range(n):
        r_, c_ = divmod(i, cols)
        px = x - (cols - 1) * dx / 2 + c_ * dx
        py = y - (rows - 1) * dy / 2 + r_ * dy
        col = color if i < int(k) else "#c9c2b3"
        out.append(circle(px, py - 30 * s, 15 * s, fill=col, w=4 * s))
        out.append(path(f"M{px - 24 * s},{py + 45 * s} L{px - 24 * s},{py} Q{px},{py - 18 * s} {px + 24 * s},{py} "
                        f"L{px + 24 * s},{py + 45 * s} Z", fill=col, w=4 * s))
    return "".join(out)


@prop("balance")
def balance(x, y, s=1.0, tilt=0.0, **_):
    """Scale with two pans. tilt: -1 (left pan down) .. 1 (right pan down). Put icons on the pans:
    left pan rim ≈ (x − 220·s, y − (330 + 90·tilt)·s), right ≈ (x + 220·s, y − (330 − 90·tilt)·s)."""
    t = max(-1.0, min(1.0, float(tilt)))
    top = y - 470 * s
    dy = 90 * t * s
    lx, ly = x - 220 * s, top - dy
    rx_, ry = x + 220 * s, top + dy
    out = [path(f"M{x - 100 * s},{y} L{x + 100 * s},{y} L{x + 40 * s},{y - 40 * s} L{x - 40 * s},{y - 40 * s} Z",
                fill="bronze", w=6 * s),
           line([(x, y - 40 * s), (x, top)], 12 * s),
           line([(lx, ly), (rx_, ry)], 10 * s)]
    for px, py in ((lx, ly), (rx_, ry)):
        out.append(line([(px, py), (px - 70 * s, py + 140 * s)], 3 * s))
        out.append(line([(px, py), (px + 70 * s, py + 140 * s)], 3 * s))
        out.append(path(f"M{px - 90 * s},{py + 140 * s} Q{px},{py + 190 * s} {px + 90 * s},{py + 140 * s} Z", fill="bronze", w=6 * s))
    out.append(dot(x, top, 14 * s))
    return "".join(out)
