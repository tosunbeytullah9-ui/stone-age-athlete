"""Environment pieces and marks. Floor objects: (x, y) = bottom centre; floating marks: centre."""
from __future__ import annotations

import math
import random

from .props import prop
from .style import INK, RED, band, c, circle, dot, ellipse, line, path, poly, polar, rect


# ---------------- floating marks ----------------
@prop("wave", floating=True)
def wave(x, y, s=1.0, **_):
    """Curling sea wave (rough sea, surf)."""
    return (path(f"M{x - 200 * s},{y + 70 * s} Q{x - 120 * s},{y - 20 * s} {x - 20 * s},{y - 80 * s} "
                 f"Q{x + 90 * s},{y - 130 * s} {x + 150 * s},{y - 40 * s} Q{x + 90 * s},{y - 80 * s} {x + 50 * s},{y - 20 * s} "
                 f"Q{x + 110 * s},{y + 20 * s} {x + 200 * s},{y + 70 * s} Z", fill="sea", w=7 * s)
            + path(f"M{x - 20 * s},{y - 80 * s} Q{x + 90 * s},{y - 130 * s} {x + 150 * s},{y - 40 * s}", w=14 * s,
                   stroke=c("foam")))


@prop("bubbles", floating=True)
def bubbles(x, y, s=1.0, n=6, **_):
    """Rising air bubbles (column about 260 px tall at scale 1)."""
    rnd = random.Random(int(n) * 7 + 1)
    out = []
    for i in range(max(1, int(n))):
        t = i / max(1, int(n) - 1)
        bx = x + rnd.uniform(-35, 35) * s
        by = y + 130 * s - t * 260 * s
        r = (8 + 14 * t + rnd.uniform(-2, 4)) * s
        out.append(circle(bx, by, r, fill="#e6f4fa", w=4 * s))
        out.append(dot(bx - r * 0.35, by - r * 0.35, r * 0.22, color="#fff"))
    return "".join(out)


@prop("snowflake", floating=True)
def snowflake(x, y, s=1.0, **_):
    out = []
    for a in range(0, 360, 60):
        out.append(line([(x, y), polar(x, y, 70 * s, a)], 7 * s, color=c("vein")))
        b = polar(x, y, 42 * s, a)
        out.append(line([polar(b[0], b[1], 20 * s, a - 50), b, polar(b[0], b[1], 20 * s, a + 50)], 6 * s, color=c("vein")))
    return "".join(out)


@prop("mountain_icon", floating=True)
def mountain_icon(x, y, s=1.0, flag=False, **_):
    out = [poly([(x - 150 * s, y + 90 * s), (x - 10 * s, y - 110 * s), (x + 150 * s, y + 90 * s)], fill="rock_cool", w=7 * s),
           poly([(x - 10 * s, y - 110 * s), (x - 52 * s, y - 50 * s), (x - 25 * s, y - 60 * s), (x - 5 * s, y - 40 * s),
                 (x + 20 * s, y - 62 * s), (x + 36 * s, y - 45 * s)], fill="snow", w=5 * s)]
    if flag:
        out.append(line([(x - 10 * s, y - 110 * s), (x - 10 * s, y - 190 * s)], 6 * s))
        out.append(poly([(x - 8 * s, y - 190 * s), (x + 60 * s, y - 172 * s), (x - 8 * s, y - 152 * s)], fill=RED, w=5 * s))
    return "".join(out)


@prop("sunbeam", floating=True)
def sunbeam(x, y, s=1.0, **_):
    """Hot sun with rays (heat, midday)."""
    out = [line([polar(x, y, 105 * s, a), polar(x, y, 160 * s, a)], 10 * s, color=c("ochre")) for a in range(0, 360, 30)]
    out.append(circle(x, y, 85 * s, fill="ochre", w=7 * s))
    return "".join(out)


@prop("cloud", floating=True)
def cloud(x, y, s=1.0, dark=False, **_):
    col = "#aab4bb" if dark else "#fbfbf7"
    return path(f"M{x - 180 * s},{y + 50 * s} q{-60 * s},{-80 * s} {40 * s},{-100 * s} q{40 * s},{-80 * s} {130 * s},{-30 * s} "
                f"q{90 * s},{-40 * s} {120 * s},{50 * s} q{70 * s},{20 * s} {30 * s},{80 * s} Z", fill=col, w=7 * s)


@prop("heat", floating=True)
def heat(x, y, s=1.0, **_):
    """Rising heat shimmer."""
    return "".join(path(f"M{x + d * s},{y + 90 * s} q{-25 * s},{-30 * s} 0,{-60 * s} q{25 * s},{-30 * s} 0,{-60 * s} "
                        f"q{-25 * s},{-30 * s} 0,{-60 * s}", w=7 * s, stroke=c("fire")) for d in (-60, 0, 60))


@prop("wind", floating=True)
def wind(x, y, s=1.0, **_):
    out = []
    for dx, dy, L in ((-40, -60, 260), (20, 0, 300), (-80, 60, 200)):
        x0, x1 = x + (dx - L / 2) * s, x + (dx + L / 2) * s
        out.append(path(f"M{x0},{y + dy * s} L{x1},{y + dy * s} q{40 * s},0 {40 * s},{-28 * s} "
                        f"q0,{-24 * s} {-24 * s},{-24 * s} q{-20 * s},0 {-20 * s},{18 * s}", w=7 * s, stroke=c("#8e979c")))
    return "".join(out)


@prop("splash", floating=True)
def splash(x, y, s=1.0, **_):
    """Water splash; (x, y) = point on the water line."""
    out = [ellipse(x, y, 110 * s, 22 * s, fill="foam", w=6 * s)]
    for a in (-160, -130, -100, -80, -50, -20):
        p = polar(x, y - 10 * s, 110 * s, a)
        out.append(path(f"M{x + (p[0] - x) * 0.35},{y - 12 * s} Q{(x + p[0]) / 2},{p[1] - 20 * s} {p[0]},{p[1]}", w=7 * s,
                        stroke=c("sea")))
        out.append(circle(p[0], p[1] - 14 * s, 9 * s, fill="foam", w=4 * s))
    return "".join(out)


@prop("pulse", floating=True)
def pulse(x, y, s=1.0, rate=1.0, **_):
    """Heartbeat (ECG) line, 400 px wide. rate: 0.5 (slow, fit heart) .. 2 (fast)."""
    n = max(1, round(2 * float(rate)))
    step = 400 * s / n
    pts = [(x - 200 * s, y)]
    for i in range(n):
        x0 = x - 200 * s + i * step
        pts += [(x0 + step * 0.35, y), (x0 + step * 0.45, y - 90 * s), (x0 + step * 0.55, y + 50 * s),
                (x0 + step * 0.63, y), (x0 + step, y)]
    return line(pts, 8 * s, color=RED)


# ---------------- floor: plants, shelters ----------------
@prop("palm")
def palm(x, y, s=1.0, **_):
    out = [path(f"M{x - 18 * s},{y} Q{x - 10 * s},{y - 250 * s} {x + 40 * s},{y - 420 * s} L{x + 66 * s},{y - 415 * s} "
                f"Q{x + 18 * s},{y - 250 * s} {x + 18 * s},{y} Z", fill="bark", w=7 * s)]
    tx, ty = x + 52 * s, y - 425 * s
    for a, L in ((-165, 200), (-120, 150), (-65, 150), (-15, 200), (160, 170), (25, 170)):
        e = polar(tx, ty, L * s, a)
        e = (e[0], e[1] + 55 * s)                       # fronds droop at the tip
        m = polar(tx, ty, L * 0.55 * s, a)
        px, py = -math.sin(math.radians(a)), math.cos(math.radians(a))
        up = (m[0] - px * 34 * s, m[1] - py * 34 * s - 20 * s)
        dn = (m[0] + px * 10 * s, m[1] + py * 10 * s + 20 * s)
        out.append(path(f"M{tx},{ty} Q{up[0]},{up[1]} {e[0]},{e[1]} Q{dn[0]},{dn[1]} {tx},{ty} Z", fill="leaf", w=6 * s))
    out.append(circle(tx - 12 * s, ty + 20 * s, 16 * s, fill="bark", w=4 * s))
    out.append(circle(tx + 14 * s, ty + 24 * s, 16 * s, fill="bark", w=4 * s))
    return "".join(out)


@prop("pine")
def pine(x, y, s=1.0, snow=False, **_):
    out = [rect(x - 18 * s, y - 90 * s, 36 * s, 90 * s, "bark", w=6 * s)]
    for i, (w_, top) in enumerate(((150, 250), (120, 350), (85, 440))):
        base = y - 70 * s - i * 95 * s
        out.append(poly([(x - w_ * s, base), (x, y - top * s - 40 * s), (x + w_ * s, base)], fill="#5f7a45", w=7 * s))
        if snow:
            out.append(path(f"M{x - w_ * 0.45 * s},{base - (top - 70 - i * 95) * 0.45 * s} L{x},{y - top * s - 40 * s} "
                            f"L{x + w_ * 0.45 * s},{base - (top - 70 - i * 95) * 0.45 * s} Q{x},{base - (top - 70 - i * 95) * 0.3 * s} "
                            f"{x - w_ * 0.45 * s},{base - (top - 70 - i * 95) * 0.45 * s} Z", fill="snow", w=4 * s))
    return "".join(out)


@prop("reeds")
def reeds(x, y, s=1.0, **_):
    out = []
    for i, (dx, h, lean) in enumerate(((-60, 230, -20), (-30, 290, -8), (0, 260, 6), (30, 310, 14), (60, 220, 24))):
        top = (x + (dx + lean) * s, y - h * s)
        out.append(path(f"M{x + dx * s},{y} Q{x + dx * s},{y - h * 0.5 * s} {top[0]},{top[1]}", w=7 * s, stroke=c("#6f7f3e")))
        if i % 2 == 1:
            out.append(ellipse(top[0], top[1] + 30 * s, 11 * s, 30 * s, fill="bark", w=4 * s, rot=lean * 0.8))
    return "".join(out)


@prop("seaweed")
def seaweed(x, y, s=1.0, **_):
    return "".join(path(f"M{x + dx * s},{y} q{-35 * s},{-h * 0.25 * s} 0,{-h * 0.5 * s} q{35 * s},{-h * 0.25 * s} 0,{-h * 0.5 * s}",
                        w=14 * s, stroke=c("#4f7a4a")) for dx, h in ((-30, 220), (10, 300), (45, 180)))


@prop("coral")
def coral(x, y, s=1.0, color="#e98a7e", **_):
    col = c(color)
    out = [band([(x, y), (x, y - 110 * s)], 22 * s, col, 5 * s),
           band([(x, y - 60 * s), (x - 60 * s, y - 120 * s), (x - 70 * s, y - 170 * s)], 18 * s, col, 5 * s),
           band([(x, y - 80 * s), (x + 55 * s, y - 130 * s), (x + 60 * s, y - 190 * s)], 18 * s, col, 5 * s),
           band([(x, y - 110 * s), (x + 5 * s, y - 180 * s)], 16 * s, col, 5 * s)]
    return "".join(out)


@prop("igloo")
def igloo(x, y, s=1.0, **_):
    out = [path(f"M{x - 220 * s},{y} A{220 * s},{200 * s} 0 0 1 {x + 220 * s},{y} Z", fill="snow", w=8 * s)]
    for i, yy in enumerate((60, 120, 170)):
        half = 220 * math.sqrt(max(0, 1 - (yy / 200) ** 2))
        out.append(line([(x - half * s, y - yy * s), (x + half * s, y - yy * s)], 3.5 * s, color="#9fb3c0"))
        for j in range(-3, 4):
            bx = x + (j * 60 + (30 if i % 2 else 0)) * s
            if abs(bx - x) < half * s - 10 * s:
                out.append(line([(bx, y - yy * s), (bx, y - (yy - 55 if i else 0) * s)], 3.5 * s, color="#9fb3c0"))
    out.append(path(f"M{x + 60 * s},{y} L{x + 60 * s},{y - 80 * s} A{60 * s},{60 * s} 0 0 1 {x + 180 * s},{y - 80 * s} "
                    f"L{x + 180 * s},{y} Z", fill="snow", w=7 * s))
    out.append(path(f"M{x + 90 * s},{y} L{x + 90 * s},{y - 60 * s} A{30 * s},{30 * s} 0 0 1 {x + 150 * s},{y - 60 * s} "
                    f"L{x + 150 * s},{y} Z", fill="#3e4b57", w=5 * s))
    return "".join(out)


@prop("yurt")
def yurt(x, y, s=1.0, **_):
    """Mongolian ger."""
    return "".join([rect(x - 230 * s, y - 170 * s, 460 * s, 170 * s, "#f3ead8", w=8 * s),
                    poly([(x - 250 * s, y - 165 * s), (x - 60 * s, y - 300 * s), (x + 60 * s, y - 300 * s),
                          (x + 250 * s, y - 165 * s)], fill="#e8dcc0", w=8 * s),
                    line([(x - 230 * s, y - 120 * s), (x + 230 * s, y - 120 * s)], 6 * s, color=RED),
                    line([(x - 240 * s, y - 175 * s), (x + 240 * s, y - 175 * s)], 6 * s, color=RED),
                    rect(x - 45 * s, y - 120 * s, 90 * s, 120 * s, "#d8342c", rx=4 * s, w=6 * s),
                    rect(x - 40 * s, y - 318 * s, 80 * s, 22 * s, "bark", rx=4 * s, w=5 * s)])


@prop("stilt_house")
def stilt_house(x, y, s=1.0, **_):
    """Wooden house on stilts (sea nomads). y = water/ground line; the deck is 220·scale above it,
    so a figure on the deck uses ground = y − 220·scale."""
    deck = y - 220 * s
    out = [line([(x + dx * s, y + 30 * s), (x + dx * s, deck)], 12 * s, color=c("bark")) for dx in (-200, -90, 40, 170)]
    out += [rect(x - 250 * s, deck - 20 * s, 500 * s, 24 * s, "clay", w=6 * s),
            rect(x - 200 * s, deck - 210 * s, 340 * s, 190 * s, "#c7a36f", w=7 * s),
            poly([(x - 240 * s, deck - 200 * s), (x - 30 * s, deck - 330 * s), (x + 180 * s, deck - 200 * s)], fill="#b8924a", w=7 * s),
            rect(x - 150 * s, deck - 150 * s, 70 * s, 130 * s, "#5b4636", w=5 * s)]
    for i in range(5):
        out.append(line([(x - 190 * s, deck - 190 * s + i * 38 * s), (x + 130 * s, deck - 190 * s + i * 38 * s)], 3 * s,
                        color="#9c7f4c"))
    return "".join(out)


@prop("tent")
def tent(x, y, s=1.0, **_):
    """Modern expedition tent (base camp)."""
    return "".join([poly([(x - 200 * s, y), (x, y - 220 * s), (x + 200 * s, y)], fill="#e8793a", w=8 * s),
                    poly([(x - 50 * s, y), (x, y - 130 * s), (x + 50 * s, y)], fill="#5a3a2a", w=6 * s),
                    line([(x, y - 220 * s), (x + 60 * s, y - 250 * s)], 5 * s)])


@prop("ice_hole")
def ice_hole(x, y, s=1.0, **_):
    """Hole in the ice (Inuit fishing / seal hunting); lies flat on the floor."""
    return ellipse(x, y + 20 * s, 110 * s, 30 * s, fill="#3f6f94", w=7 * s) + \
        path(f"M{x - 110 * s},{y + 20 * s} Q{x},{y - 5 * s} {x + 110 * s},{y + 20 * s}", w=4 * s, stroke=c("ice"))


@prop("water_surface")
def water_surface(x, y, s=1.0, w=1920, **_):
    """See-through water from the line y down to the bottom of the frame, `w` px wide centred on x.
    Draw it OVER figures (order: figures_first) to show someone chest-deep or swimming at the surface."""
    W_ = w * s
    x0 = x - W_ / 2
    n = max(1, int(W_ // 120))
    d = f"M{x0},{y} " + " ".join(f"q30,{-12 if i % 2 == 0 else 12} 60,0" for i in range(n * 2))
    return (f'<path d="{d} L{x0 + n * 120},1100 L{x0},1100 Z" fill="{c("sea")}" fill-opacity="0.55"/>'
            + path(d, w=6, stroke=c("foam")))
