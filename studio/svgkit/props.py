"""Objects placed in a scene. Every prop: {type, x, y, scale?, ...options}.
For objects that stand on the floor, (x, y) is the bottom-centre; for floating things
(clock, sun, icons, marks) it is the centre.
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


# ---------------- modern ----------------
@prop("clock")
def clock(x, y, s=1.0, time="7:00", **_):
    """Wall clock. time: "H:MM"."""
    r = 90 * s
    h, m = (int(v) for v in str(time).split(":"))
    out = [circle(x, y, r, fill="#fbfbf7", w=7 * s)]
    for a in range(0, 360, 30):
        out.append(line([polar(x, y, r - 14 * s, a), polar(x, y, r - 4 * s, a)], 4 * s))
    out.append(line([(x, y), polar(x, y, r * 0.5, (h % 12 + m / 60) * 30 - 90)], 8 * s))
    out.append(line([(x, y), polar(x, y, r * 0.78, m * 6 - 90)], 5 * s))
    return "".join(out)


@prop("sofa")
def sofa(x, y, s=1.0, color="furniture", **_):
    w = 820 * s
    x0 = x - w / 2
    return "".join([
        rect(x0, y - 390 * s, w, 200 * s, color, rx=30 * s, w=8 * s),
        rect(x0 - 20 * s, y - 220 * s, w + 40 * s, 170 * s, color, rx=24 * s, w=8 * s),
        rect(x0 - 60 * s, y - 300 * s, 110 * s, 250 * s, color, rx=30 * s, w=8 * s),
        rect(x0 + w - 50 * s, y - 300 * s, 110 * s, 250 * s, color, rx=30 * s, w=8 * s),
        line([(x0, y - 50 * s), (x0 - 10 * s, y)], 10 * s), line([(x0 + w, y - 50 * s), (x0 + w + 10 * s, y)], 10 * s),
    ])


@prop("chair")
def chair(x, y, s=1.0, **_):
    return "".join([
        rect(x - 80 * s, y - 200 * s, 160 * s, 26 * s, "furniture", rx=8 * s, w=7 * s),
        line([(x - 70 * s, y - 175 * s), (x - 70 * s, y)], 8 * s), line([(x + 70 * s, y - 175 * s), (x + 70 * s, y)], 8 * s),
        line([(x - 75 * s, y - 200 * s), (x - 90 * s, y - 420 * s)], 9 * s),
    ])


@prop("desk")
def desk(x, y, s=1.0, laptop=True, **_):
    out = [rect(x - 260 * s, y - 330 * s, 520 * s, 30 * s, "clay", rx=6 * s, w=7 * s),
           line([(x - 230 * s, y - 300 * s), (x - 230 * s, y)], 9 * s), line([(x + 230 * s, y - 300 * s), (x + 230 * s, y)], 9 * s)]
    if laptop:
        out.append(path(f"M{x - 60 * s},{y - 330 * s} L{x - 90 * s},{y - 460 * s} L{x + 60 * s},{y - 460 * s} "
                        f"L{x + 90 * s},{y - 330 * s} Z", fill="metal", w=6 * s))
        out.append(path(f"M{x - 70 * s},{y - 345 * s} L{x - 80 * s},{y - 445 * s} L{x + 55 * s},{y - 445 * s} "
                        f"L{x + 75 * s},{y - 345 * s} Z", fill="screen", w=0))
    return "".join(out)


@prop("window")
def window(x, y, s=1.0, night=False, **_):
    w, h = 330 * s, 300 * s
    x0, y0 = x - w / 2, y - h / 2
    sky = "night" if night else "#bfe0f2"
    out = [rect(x0, y0, w, h, sky, w=8 * s), line([(x, y0), (x, y0 + h)], 6 * s), line([(x0, y), (x0 + w, y)], 6 * s)]
    if night:
        out.append(circle(x + 85 * s, y0 + 65 * s, 34 * s, fill="#f3ecc8", w=5 * s))
        out.append(f'<circle cx="{x + 101 * s:.1f}" cy="{y0 + 56 * s:.1f}" r="{30 * s:.1f}" fill="{c("night")}"/>')
    else:
        out.append(circle(x - 80 * s, y0 + 70 * s, 30 * s, fill="ochre", w=5 * s))
    return "".join(out)


@prop("tv")
def tv(x, y, s=1.0, **_):
    return "".join([rect(x - 190 * s, y - 380 * s, 380 * s, 230 * s, "metal", rx=10 * s, w=8 * s),
                    rect(x - 170 * s, y - 362 * s, 340 * s, 194 * s, "screen", rx=4 * s, w=0),
                    rect(x - 150 * s, y - 150 * s, 300 * s, 150 * s, "furniture", rx=8 * s, w=7 * s)])


@prop("dumbbell_rack")
def dumbbell_rack(x, y, s=1.0, **_):
    out = [rect(x - 200 * s, y - 160 * s, 400 * s, 24 * s, "metal", rx=6 * s, w=6 * s),
           line([(x - 180 * s, y - 136 * s), (x - 180 * s, y)], 9 * s), line([(x + 180 * s, y - 136 * s), (x + 180 * s, y)], 9 * s)]
    for i in range(4):
        cx = x - 140 * s + i * 93 * s
        out.append(line([(cx - 25 * s, y - 180 * s), (cx + 25 * s, y - 180 * s)], 8 * s))
        out.append(rect(cx - 36 * s, y - 202 * s, 18 * s, 44 * s, "metal", rx=5 * s, w=5 * s))
        out.append(rect(cx + 18 * s, y - 202 * s, 18 * s, 44 * s, "metal", rx=5 * s, w=5 * s))
    return "".join(out)


@prop("mat")
def mat(x, y, s=1.0, **_):
    return rect(x - 400 * s, y - 12 * s, 800 * s, 24 * s, "#5f7280", rx=8 * s, w=5 * s)


@prop("treadmill")
def treadmill(x, y, s=1.0, **_):
    return "".join([path(f"M{x - 260 * s},{y - 20 * s} L{x + 200 * s},{y - 60 * s} L{x + 210 * s},{y - 20 * s} "
                         f"L{x - 250 * s},{y + 10 * s} Z", fill="metal", w=7 * s),
                    line([(x + 190 * s, y - 50 * s), (x + 230 * s, y - 330 * s)], 10 * s),
                    rect(x + 190 * s, y - 360 * s, 110 * s, 50 * s, "furniture", rx=8 * s, w=6 * s)])


# ---------------- ancient ----------------
@prop("hut")
def hut(x, y, s=1.0, **_):
    out = [path(f"M{x - 180 * s},{y} L{x},{y - 300 * s} L{x + 180 * s},{y} Z", fill="clay", w=8 * s)]
    for i in range(6):
        out.append(line([(x - 120 * s + i * 50 * s, y), (x, y - 300 * s)], 3 * s))
    out.append(path(f"M{x - 40 * s},{y} L{x - 40 * s},{y - 90 * s} Q{x},{y - 130 * s} {x + 40 * s},{y - 90 * s} "
                    f"L{x + 40 * s},{y} Z", fill="#4a3a2a", w=6 * s))
    return "".join(out)


@prop("quern")
def quern(x, y, s=1.0, **_):
    """Saddle quern (grinding stone). (x,y) = bottom centre."""
    return "".join([
        path(f"M{x - 125 * s},{y + 10 * s} Q{x - 115 * s},{y - 50 * s} {x - 5 * s},{y - 45 * s} "
             f"Q{x + 105 * s},{y - 42 * s} {x + 125 * s},{y + 10 * s} Q{x + 5 * s},{y + 40 * s} {x - 125 * s},{y + 10 * s} Z",
             fill="stone", w=7 * s),
        rect(x - 50 * s, y - 78 * s, 95 * s, 42 * s, "stone_dark", rx=20 * s, w=7 * s),
    ])


@prop("grain")
def grain(x, y, s=1.0, **_):
    out = [f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{95 * s:.1f}" ry="{32 * s:.1f}" fill="{c("grain")}" '
           f'stroke="{INK}" stroke-width="{6 * s:.1f}"/>']
    for dx, dy in ((-40, -10), (-10, -19), (25, -7), (45, -15), (-20, 5), (15, 7)):
        out.append(f'<ellipse cx="{x + dx * s:.1f}" cy="{y + dy * s:.1f}" rx="{6 * s:.1f}" ry="{3.5 * s:.1f}" fill="#b8922e"/>')
    return "".join(out)


@prop("campfire")
def campfire(x, y, s=1.0, **_):
    return "".join([
        line([(x - 70 * s, y), (x + 60 * s, y - 25 * s)], 16 * s, color=c("bark")),
        line([(x + 70 * s, y), (x - 60 * s, y - 25 * s)], 16 * s, color=c("bark")),
        path(f"M{x},{y - 170 * s} q{70 * s},{80 * s} {40 * s},{150 * s} q{-40 * s},{20 * s} {-80 * s},0 "
             f"q{-30 * s},{-70 * s} {40 * s},{-150 * s}z", fill="fire", w=6 * s),
        path(f"M{x},{y - 100 * s} q{30 * s},{40 * s} {15 * s},{80 * s} q{-15 * s},{8 * s} {-30 * s},0 "
             f"q{-10 * s},{-40 * s} {15 * s},{-80 * s}z", fill="#f7d35a", w=4 * s),
    ])


@prop("tree")
def tree(x, y, s=1.0, **_):
    return "".join([rect(x - 22 * s, y - 260 * s, 44 * s, 260 * s, "bark", rx=10 * s, w=7 * s),
                    circle(x, y - 330 * s, 130 * s, fill="leaf", w=7 * s),
                    circle(x - 100 * s, y - 270 * s, 80 * s, fill="leaf", w=7 * s),
                    circle(x + 100 * s, y - 280 * s, 85 * s, fill="leaf", w=7 * s)])


@prop("acacia")
def acacia(x, y, s=1.0, **_):
    return "".join([line([(x, y), (x - 10 * s, y - 180 * s), (x - 90 * s, y - 280 * s)], 16 * s, color=c("bark")),
                    line([(x - 10 * s, y - 180 * s), (x + 80 * s, y - 290 * s)], 14 * s, color=c("bark")),
                    path(f"M{x - 230 * s},{y - 280 * s} Q{x},{y - 400 * s} {x + 230 * s},{y - 285 * s} "
                         f"Q{x},{y - 250 * s} {x - 230 * s},{y - 280 * s} Z", fill="leaf", w=7 * s)])


@prop("rock")
def rock(x, y, s=1.0, **_):
    return path(f"M{x - 150 * s},{y} Q{x - 150 * s},{y - 120 * s} {x - 20 * s},{y - 130 * s} "
                f"Q{x + 140 * s},{y - 120 * s} {x + 150 * s},{y} Z", fill="stone", w=7 * s)


@prop("bush")
def bush(x, y, s=1.0, **_):
    return "".join(circle(x + dx * s, y - dy * s, r * s, fill="leaf", w=6 * s)
                   for dx, dy, r in ((-60, 45, 55), (0, 70, 70), (60, 45, 55)))


@prop("deer")
def deer(x, y, s=1.0, flip=False, **_):
    f = -1 if flip else 1
    X = lambda dx: x + f * dx * s  # noqa: E731
    return "".join([
        f'<ellipse cx="{x:.1f}" cy="{y - 190 * s:.1f}" rx="{120 * s:.1f}" ry="{52 * s:.1f}" fill="{c("hide")}" stroke="{INK}" stroke-width="{7 * s:.1f}"/>',
        line([(X(-80), y - 160 * s), (X(-90), y)], 8 * s), line([(X(-50), y - 160 * s), (X(-40), y)], 8 * s),
        line([(X(60), y - 160 * s), (X(55), y)], 8 * s), line([(X(90), y - 160 * s), (X(100), y)], 8 * s),
        line([(X(100), y - 215 * s), (X(150), y - 300 * s)], 16 * s, color=c("hide")),
        f'<ellipse cx="{X(170):.1f}" cy="{y - 310 * s:.1f}" rx="{40 * s:.1f}" ry="{24 * s:.1f}" fill="{c("hide")}" stroke="{INK}" stroke-width="{6 * s:.1f}"/>',
        line([(X(160), y - 330 * s), (X(140), y - 390 * s), (X(115), y - 405 * s)], 5 * s),
        line([(X(140), y - 390 * s), (X(165), y - 415 * s)], 5 * s),
        f'<circle cx="{X(185):.1f}" cy="{y - 314 * s:.1f}" r="{4 * s:.1f}" fill="{INK}"/>',
    ])


@prop("mammoth")
def mammoth(x, y, s=1.0, flip=False, **_):
    f = -1 if flip else 1
    X = lambda dx: x + f * dx * s  # noqa: E731
    return "".join([
        path(f"M{X(-230)},{y - 150 * s} Q{X(-240)},{y - 420 * s} {X(0)},{y - 430 * s} Q{X(200)},{y - 440 * s} "
             f"{X(230)},{y - 260 * s} L{X(230)},{y - 150 * s} Z", fill="#7a5a3a", w=8 * s),
        rect(min(X(-200), X(-140)), y - 170 * s, 60 * s, 170 * s, "#7a5a3a", rx=12 * s, w=7 * s),
        rect(min(X(-100), X(-40)), y - 170 * s, 60 * s, 170 * s, "#7a5a3a", rx=12 * s, w=7 * s),
        rect(min(X(90), X(150)), y - 170 * s, 60 * s, 170 * s, "#7a5a3a", rx=12 * s, w=7 * s),
        rect(min(X(170), X(230)), y - 170 * s, 60 * s, 170 * s, "#7a5a3a", rx=12 * s, w=7 * s),
        path(f"M{X(230)},{y - 280 * s} Q{X(300)},{y - 200 * s} {X(270)},{y - 60 * s}", w=34 * s, stroke=c("#7a5a3a")),
        path(f"M{X(230)},{y - 280 * s} Q{X(300)},{y - 200 * s} {X(270)},{y - 60 * s}", w=4 * s),
        path(f"M{X(215)},{y - 230 * s} Q{X(330)},{y - 150 * s} {X(360)},{y - 260 * s}", w=14 * s, stroke=c("bone")),
        f'<circle cx="{X(180):.1f}" cy="{y - 330 * s:.1f}" r="{6 * s:.1f}" fill="{INK}"/>',
    ])


@prop("footprints")
def footprints(x, y, s=1.0, n=5, **_):
    return "".join(f'<ellipse cx="{x + i * 90 * s:.1f}" cy="{y + (i % 2) * 22 * s:.1f}" rx="{22 * s:.1f}" '
                   f'ry="{11 * s:.1f}" fill="#b8956a" stroke="{INK}" stroke-width="{3 * s:.1f}"/>' for i in range(n))


@prop("spear_ground")
def spear_ground(x, y, s=1.0, **_):
    return "".join([line([(x, y), (x + 20 * s, y - 330 * s)], 7 * s, color=c("bark")),
                    path(f"M{x + 6 * s},{y - 330 * s} L{x + 24 * s},{y - 385 * s} L{x + 36 * s},{y - 328 * s} Z",
                         fill="stone", w=5 * s)])


# ---------------- explainer / comparison ----------------
@prop("board")
def board(x, y, s=1.0, w=960, h=690, divider=True, **_):
    x0, y0 = x - w * s / 2, y - h * s / 2
    out = [rect(x0, y0, w * s, h * s, "paper", rx=14 * s, w=9 * s)]
    if divider:
        out.append(line([(x, y0 + 50 * s), (x, y0 + h * s - 40 * s)], 4 * s))
    return "".join(out)


@prop("bone")
def bone(x, y, s=1.0, thick=1.0, length=350, **_):
    """Upper-arm bone standing upright; (x,y) = centre. thick: 0.6 (thin) .. 1.4 (thick)."""
    shaft, knob = 64 * thick * s, 46 * thick * s
    top, bottom = y - length * s / 2, y + length * s / 2
    f = c("bone")
    return "".join([
        f'<rect x="{x - shaft / 2:.1f}" y="{top:.1f}" width="{shaft:.1f}" height="{bottom - top:.1f}" fill="{f}" stroke="{INK}" stroke-width="{7 * s:.1f}"/>',
        circle(x - knob * .55, top, knob, fill=f, w=7 * s), circle(x + knob * .55, top + 6 * s, knob * .85, fill=f, w=7 * s),
        f'<rect x="{x - shaft / 2 + 3.5 * s:.1f}" y="{top:.1f}" width="{shaft - 7 * s:.1f}" height="{40 * s:.1f}" fill="{f}"/>',
        circle(x - knob * .5, bottom, knob * .8, fill=f, w=7 * s), circle(x + knob * .5, bottom, knob * .8, fill=f, w=7 * s),
        f'<rect x="{x - shaft / 2 + 3.5 * s:.1f}" y="{bottom - 40 * s:.1f}" width="{shaft - 7 * s:.1f}" height="{40 * s:.1f}" fill="{f}"/>',
    ])


@prop("bone_section")
def bone_section(x, y, s=1.0, density=0.5, **_):
    """Cross-section of spongy bone; density 0..1 = how filled the mesh is."""
    import random
    rnd = random.Random(int(density * 1000))
    R = 150 * s
    out = [circle(x, y, R, fill="bone", w=9 * s)]
    n = int(20 + 140 * density)
    for _ in range(n):
        a, rr = rnd.uniform(0, 2 * math.pi), R * math.sqrt(rnd.uniform(0, 0.8))
        px, py = x + rr * math.cos(a), y + rr * math.sin(a)
        out.append(line([(px, py), polar(px, py, 18 * s, rnd.uniform(0, 360))], 5 * s, color="#b9a98a"))
    return "".join(out)


@prop("icon_quern")
def icon_quern(x, y, s=1.0, **_):
    return quern(x, y + 20 * s, 0.5 * s)


@prop("icon_oar")
def icon_oar(x, y, s=1.0, **_):
    return "".join([line([(x - 60 * s, y - 45 * s), (x + 60 * s, y + 45 * s)], 8 * s),
                    f'<ellipse cx="{x + 75 * s:.1f}" cy="{y + 57 * s:.1f}" rx="{36 * s:.1f}" ry="{16 * s:.1f}" '
                    f'transform="rotate(37 {x + 75 * s:.1f} {y + 57 * s:.1f})" fill="{c("water")}" stroke="{INK}" stroke-width="{5 * s:.1f}"/>'])


@prop("bar_chart")
def bar_chart(x, y, s=1.0, values=(1.0, 0.6), colors=("ochre", "water"), w=420, h=360, **_):
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


@prop("question")
def question(x, y, s=1.0, **_):
    return (path(f"M{x - 35 * s},{y - 40 * s} q0,{-45 * s} {35 * s},{-45 * s} q{38 * s},0 {38 * s},{35 * s} "
                 f"q0,{25 * s} {-38 * s},{40 * s} l0,{25 * s}", w=12 * s)
            + circle(x, y + 55 * s, 8 * s, fill=INK, w=2))


@prop("heart")
def heart(x, y, s=1.0, **_):
    return path(f"M{x},{y + 50 * s} C{x - 110 * s},{y - 20 * s} {x - 50 * s},{y - 95 * s} {x},{y - 40 * s} "
                f"C{x + 50 * s},{y - 95 * s} {x + 110 * s},{y - 20 * s} {x},{y + 50 * s} Z", fill=RED, w=7 * s)


@prop("calendar")
def calendar(x, y, s=1.0, **_):
    out = [rect(x - 110 * s, y - 100 * s, 220 * s, 200 * s, "#fbfbf7", rx=10 * s, w=7 * s),
           rect(x - 110 * s, y - 100 * s, 220 * s, 50 * s, RED, rx=10 * s, w=7 * s)]
    for r_ in range(3):
        for c_ in range(4):
            out.append(rect(x - 90 * s + c_ * 48 * s, y - 35 * s + r_ * 42 * s, 30 * s, 26 * s, "paper", rx=3, w=3 * s))
    return "".join(out)


@prop("zzz")
def zzz(x, y, s=1.0, **_):
    out = []
    for i, k in enumerate((1.0, 0.75, 0.55)):
        zx, zy, z = x + i * 45 * s, y - i * 50 * s, 30 * k * s
        out.append(line([(zx - z, zy - z), (zx + z, zy - z), (zx - z, zy + z), (zx + z, zy + z)], 6 * k * s))
    return "".join(out)


@prop("sweat")
def sweat(x, y, s=1.0, **_):
    return path(f"M{x},{y} q{-9 * s},{16 * s} 0,{24 * s} q{9 * s},{-8 * s} 0,{-24 * s}z", fill="sweat", w=3 * s)


@prop("motion")
def motion(x, y, s=1.0, direction="both", **_):
    """Back-and-forth or directional motion marks."""
    out = []
    if direction in ("both", "right"):
        out.append(line([(x + 20 * s, y), (x + 70 * s, y)], 5 * s) + line([(x + 58 * s, y - 10 * s), (x + 70 * s, y), (x + 58 * s, y + 10 * s)], 5 * s))
    if direction in ("both", "left"):
        out.append(line([(x - 20 * s, y), (x - 70 * s, y)], 5 * s) + line([(x - 58 * s, y - 10 * s), (x - 70 * s, y), (x - 58 * s, y + 10 * s)], 5 * s))
    if direction == "speed":
        for i in range(3):
            out.append(line([(x - 60 * s, y + i * 30 * s), (x - 160 * s, y + i * 30 * s)], 5 * s))
    return "".join(out)


@prop("effort")
def effort(x, y, s=1.0, **_):
    return "".join(line([polar(x, y, 60 * s, a), polar(x, y, 95 * s, a)], 5 * s) for a in (-150, -120, -60, -30))


@prop("rain")
def rain(x, y, s=1.0, **_):
    """Rain cloud centred at (x, y) with falling drops."""
    out = [path(f"M{x - 250 * s},{y} q{-40 * s},{-110 * s} {90 * s},{-120 * s} q{60 * s},{-90 * s} {170 * s},{-20 * s} "
                f"q{120 * s},{-50 * s} {150 * s},{70 * s} q{70 * s},{30 * s} {20 * s},{80 * s} Z", fill="#aab4bb", w=7 * s)]
    for i in range(18):
        rx_ = x - 230 * s + (i % 9) * 55 * s
        ry_ = y + 40 * s + (i // 9) * 100 * s
        out.append(line([(rx_, ry_), (rx_ - 12 * s, ry_ + 45 * s)], 4 * s, color=c("water")))
    return "".join(out)


@prop("sun")
def sun(x, y, s=1.0, **_):
    return circle(x, y, 85 * s, fill="ochre", w=7 * s)


@prop("moon")
def moon(x, y, s=1.0, **_):
    return circle(x, y, 60 * s, fill="#f3ecc8", w=6 * s)


@prop("stars")
def stars(x, y, s=1.0, n=14, **_):
    import random
    rnd = random.Random(3)
    return "".join(circle(rnd.uniform(40, 1880), rnd.uniform(40, 420), rnd.uniform(3, 6), fill="#f3ecc8", w=0)
                   for _ in range(n))


FLOATING.update({"clock", "sun", "moon", "icon_quern", "icon_oar", "check", "cross", "question", "heart", "calendar",
                 "zzz", "sweat", "motion", "effort", "bone", "bone_section", "window", "board", "stars", "arrow",
                 "rain"})

# extended kit (each module registers more props with @prop)
from . import props_animals, props_body, props_gear, props_nature, props_charts  # noqa: E402,F401
