"""Body / anatomy icons. All floating: (x, y) = centre; about 250-300 px tall at scale 1.
Relative options (size, fill, density...) are 0..1 or multipliers — never text."""
from __future__ import annotations

import math
import random

from .props import prop
from .style import INK, RED, band, c, circle, dot, ellipse, line, path, poly, polar


@prop("heart_organ", floating=True)
def heart_organ(x, y, s=1.0, size=1.0, beat=False, **_):
    """Anatomical heart. size: 0.7 (small) .. 1.4 (athlete's heart). beat: pulse marks."""
    k = s * float(size)
    X = lambda d: x + d * k  # noqa: E731
    Y = lambda d: y + d * k  # noqa: E731
    out = [band([(X(-10), Y(-60)), (X(-12), Y(-120)), (X(40), Y(-150)), (X(80), Y(-110)), (X(82), Y(-70))],
                30 * k, "organ", 6 * k),                                                    # aortic arch
           band([(X(-55), Y(-50)), (X(-60), Y(-125))], 26 * k, "vein", 6 * k),              # vena cava
           band([(X(30), Y(-60)), (X(18), Y(-118))], 22 * k, "vein", 6 * k),                # pulmonary trunk
           path(f"M{X(-70)},{Y(-40)} C{X(-120)},{Y(20)} {X(-60)},{Y(110)} {X(20)},{Y(130)} "
                f"C{X(70)},{Y(95)} {X(120)},{Y(10)} {X(85)},{Y(-45)} C{X(55)},{Y(-80)} {X(-40)},{Y(-85)} {X(-70)},{Y(-40)} Z",
                fill="organ", w=7 * k),
           path(f"M{X(-5)},{Y(-60)} C{X(-15)},{Y(0)} {X(10)},{Y(60)} {X(40)},{Y(95)}", w=5 * k, stroke=c("#8e2a24")),
           ellipse(X(-35), Y(-15), 18 * k, 10 * k, fill="#f08a80", w=0, rot=-30)]
    if beat:
        for a in (-160, -135, -45, -20):
            out.append(line([polar(x, y, 150 * k, a), polar(x, y, 185 * k, a)], 6 * k))
    return "".join(out)


@prop("lungs", floating=True)
def lungs(x, y, s=1.0, fill=1.0, **_):
    """Pair of lungs with windpipe. fill: 0 (empty, narrow) .. 1 (full breath)."""
    k = s
    wv = 0.72 + 0.28 * max(0.0, min(1.0, float(fill)))
    out = [band([(x, y - 150 * k), (x, y - 40 * k)], 20 * k, "#f4e4dc", 5 * k)]
    for i in range(4):
        out.append(line([(x - 12 * k, y - (140 - i * 25) * k), (x + 12 * k, y - (140 - i * 25) * k)], 3 * k))
    for sx in (-1, 1):
        cx = x + sx * 78 * k
        out.append(path(f"M{x + sx * 22 * k},{y - 70 * k} C{x + sx * 60 * k},{y - 140 * k} {cx + sx * 85 * k * wv},{y - 60 * k} "
                        f"{cx + sx * 80 * k * wv},{y + 60 * k} C{cx + sx * 70 * k * wv},{y + 130 * k} {x + sx * 30 * k},{y + 120 * k} "
                        f"{x + sx * 22 * k},{y + 70 * k} Z", fill="pink", w=7 * k))
        out.append(line([(x, y - 40 * k), (x + sx * 40 * k, y - 10 * k), (x + sx * 70 * k, y + 40 * k)], 6 * k,
                        color=c("#c2615f")))
        out.append(line([(x + sx * 40 * k, y - 10 * k), (x + sx * 85 * k, y - 5 * k)], 5 * k, color=c("#c2615f")))
    return "".join(out)


@prop("spleen", floating=True)
def spleen(x, y, s=1.0, size=1.0, **_):
    """Spleen (bean shape). size multiplier: 1.0 normal, ~1.5 for Bajau divers."""
    k = s * float(size)
    return (path(f"M{x - 90 * k},{y + 10 * k} C{x - 110 * k},{y - 70 * k} {x - 10 * k},{y - 95 * k} {x + 60 * k},{y - 70 * k} "
                 f"C{x + 115 * k},{y - 45 * k} {x + 110 * k},{y + 40 * k} {x + 60 * k},{y + 60 * k} "
                 f"C{x + 20 * k},{y + 75 * k} {x + 15 * k},{y + 25 * k} {x - 20 * k},{y + 40 * k} "
                 f"C{x - 55 * k},{y + 60 * k} {x - 80 * k},{y + 50 * k} {x - 90 * k},{y + 10 * k} Z", fill="#9c3b52", w=7 * k)
            + ellipse(x + 20 * k, y - 40 * k, 30 * k, 12 * k, fill="#c26a80", w=0, rot=-15))


@prop("brain", floating=True)
def brain(x, y, s=1.0, **_):
    k = s
    out = [path(f"M{x - 140 * k},{y + 20 * k} C{x - 160 * k},{y - 70 * k} {x - 80 * k},{y - 130 * k} {x},{y - 118 * k} "
                f"C{x + 90 * k},{y - 130 * k} {x + 165 * k},{y - 60 * k} {x + 140 * k},{y + 25 * k} "
                f"C{x + 130 * k},{y + 70 * k} {x + 70 * k},{y + 80 * k} {x + 30 * k},{y + 60 * k} "
                f"C{x - 30 * k},{y + 90 * k} {x - 120 * k},{y + 80 * k} {x - 140 * k},{y + 20 * k} Z", fill="pink", w=7 * k),
           path(f"M{x + 20 * k},{y + 60 * k} Q{x + 40 * k},{y + 110 * k} {x + 20 * k},{y + 140 * k}", w=22 * k,
                stroke=c("#e58c90")),
           ellipse(x + 85 * k, y + 55 * k, 45 * k, 28 * k, fill="#e58c90", w=6 * k)]
    for d in (f"M{x - 110 * k},{y - 20 * k} q{30 * k},{-40 * k} {60 * k},{-10 * k} q{25 * k},{-45 * k} {60 * k},{-20 * k}",
              f"M{x - 90 * k},{y + 35 * k} q{35 * k},{-35 * k} {70 * k},0 q{30 * k},{-40 * k} {70 * k},{-10 * k}",
              f"M{x + 20 * k},{y - 90 * k} q{20 * k},{40 * k} {60 * k},{20 * k} q{35 * k},{-10 * k} {50 * k},{30 * k}",
              f"M{x + 40 * k},{y + 5 * k} q{30 * k},{-25 * k} {70 * k},0",
              f"M{x - 50 * k},{y - 95 * k} q{10 * k},{35 * k} {-40 * k},{50 * k}"):
        out.append(path(d, w=5 * k, stroke=c("#b8676b")))
    return "".join(out)


@prop("muscle", floating=True)
def muscle(x, y, s=1.0, size=1.0, vertical=False, **_):
    """Muscle belly with tendons at both ends. size: 0.5 (thin) .. 1.5 (big)."""
    k, b = s, 55 * float(size)
    L = 150
    rot = 90 if vertical else 0
    fib = "".join(path(f"M{x - 115 * k},{y} Q{x},{y + t * b * 1.6 * k} {x + 115 * k},{y}", w=3.5 * k, stroke=c("#9e3a33"))
                  for t in (-0.55, -0.2, 0.2, 0.55))
    body = (band([(x - (L + 45) * k, y), (x - L * 0.6 * k, y)], 18 * k, "cloth", 5 * k)
            + band([(x + L * 0.6 * k, y), (x + (L + 45) * k, y)], 18 * k, "cloth", 5 * k)
            + path(f"M{x - L * k},{y} C{x - 70 * k},{y - b * 1.25 * k} {x + 70 * k},{y - b * 1.25 * k} {x + L * k},{y} "
                   f"C{x + 70 * k},{y + b * 1.25 * k} {x - 70 * k},{y + b * 1.25 * k} {x - L * k},{y} Z", fill="flesh", w=7 * k)
            + fib)
    return f'<g transform="rotate({rot} {x:.1f} {y:.1f})">{body}</g>' if rot else body


@prop("muscle_fiber", floating=True)
def muscle_fiber(x, y, s=1.0, fast=0.5, **_):
    """Cross-section of a muscle: dark red = slow-twitch, pale = fast-twitch. fast: share 0..1."""
    R = 130 * s
    rnd = random.Random(11)
    out = [circle(x, y, R, fill="#f3d6cf", w=8 * s)]
    cells = []
    for ring, n in ((0, 1), (1, 6), (2, 12), (3, 18)):
        for i in range(n):
            a = 2 * math.pi * i / n + ring * 0.3
            cells.append((x + ring * 32 * s * math.cos(a), y + ring * 32 * s * math.sin(a)))
    order = list(range(len(cells)))
    rnd.shuffle(order)
    nf = round(float(fast) * len(cells))
    fast_set = set(order[:nf])
    for i, (cx, cy) in enumerate(cells):
        out.append(circle(cx, cy, 14.5 * s, fill="#fbe9e4" if i in fast_set else "#a8322c", w=3.5 * s))
    return "".join(out)


@prop("tendon", floating=True)
def tendon(x, y, s=1.0, thick=1.0, **_):
    """Lower leg from the side (toes right): calf muscle → Achilles tendon (white band) → heel.
    thick: 0.5 .. 1.5 (tendon width)."""
    k = s
    tw = 22 * float(thick) * k
    X = lambda d: x + d * k  # noqa: E731
    Y = lambda d: y + d * k  # noqa: E731
    leg = (f"M{X(-40)},{Y(-160)} L{X(40)},{Y(-160)} L{X(35)},{Y(70)} Q{X(45)},{Y(100)} {X(80)},{Y(108)} "
           f"L{X(150)},{Y(118)} Q{X(172)},{Y(135)} {X(150)},{Y(152)} L{X(-60)},{Y(152)} Q{X(-85)},{Y(140)} {X(-72)},{Y(100)} "
           f"L{X(-62)},{Y(40)} Q{X(-100)},{Y(-60)} {X(-70)},{Y(-160)} Z")
    return "".join([path(leg, fill="#f6e3cf", w=7 * k),
                    path(f"M{X(-68)},{Y(-150)} Q{X(-108)},{Y(-60)} {X(-58)},{Y(10)} Q{X(-20)},{Y(-60)} {X(-30)},{Y(-150)} Z",
                         fill="flesh", w=6 * k),
                    band([(X(-56), Y(0)), (X(-60), Y(112))], tw, "#fbf6ea", 4 * k),
                    ellipse(X(-50), Y(125), 30 * k, 24 * k, fill="bone", w=5 * k)])


@prop("foot_arch", floating=True)
def foot_arch(x, y, s=1.0, arch=0.6, **_):
    """Foot from the inside with its arch. arch: 0 (flat) .. 1 (high)."""
    k, a = s, max(0.0, min(1.0, float(arch)))
    h = (4 + 46 * a) * k
    sole = y + 70 * k
    d = (f"M{x - 150 * k},{sole} Q{x - 165 * k},{sole - 40 * k} {x - 140 * k},{sole - 70 * k} "
         f"L{x - 110 * k},{y - 110 * k} L{x - 50 * k},{y - 110 * k} Q{x - 40 * k},{y - 40 * k} {x + 40 * k},{y - 5 * k} "
         f"L{x + 140 * k},{sole - 40 * k} Q{x + 175 * k},{sole - 30 * k} {x + 165 * k},{sole} "
         f"L{x + 95 * k},{sole} Q{x - 20 * k},{sole - h * 2} {x - 115 * k},{sole} Z")
    out = [path(d, fill="#f6e3cf", w=7 * k),
           line([(x - 190 * k, sole + 6 * k), (x + 200 * k, sole + 6 * k)], 5 * k, color=c("stone_dark")),
           path(f"M{x - 115 * k},{sole - 8 * k} Q{x - 20 * k},{sole - h * 2 - 14 * k} {x + 95 * k},{sole - 8 * k}",
                w=6 * k, stroke=RED)]
    return "".join(out)


@prop("knee_joint", floating=True)
def knee_joint(x, y, s=1.0, cartilage=1.0, **_):
    """Knee from the front: femur, tibia, kneecap. cartilage: 0 (worn) .. 1 (healthy, thick blue layer)."""
    k = s
    t = (4 + 18 * max(0.0, min(1.0, float(cartilage)))) * k
    out = [path(f"M{x - 40 * k},{y - 170 * k} L{x - 40 * k},{y - 60 * k} Q{x - 95 * k},{y - 50 * k} {x - 90 * k},{y - 12 * k} "
                f"Q{x - 45 * k},{y - 2 * k} {x},{y - 20 * k} Q{x + 45 * k},{y - 2 * k} {x + 90 * k},{y - 12 * k} "
                f"Q{x + 95 * k},{y - 50 * k} {x + 40 * k},{y - 60 * k} L{x + 40 * k},{y - 170 * k} Z", fill="bone", w=7 * k),
           path(f"M{x - 85 * k},{y + 8 * k + t} L{x + 85 * k},{y + 8 * k + t} L{x + 50 * k},{y + 60 * k} "
                f"L{x + 38 * k},{y + 170 * k} L{x - 38 * k},{y + 170 * k} L{x - 50 * k},{y + 60 * k} Z", fill="bone", w=7 * k)]
    out.append(f'<rect x="{x - 88 * k:.1f}" y="{y - 6 * k:.1f}" width="{176 * k:.1f}" height="{t + 12 * k:.1f}" '
               f'rx="{8 * k:.1f}" fill="{c("#8cc3e0")}" stroke="{INK}" stroke-width="{4 * k:.1f}"/>')
    out.append(ellipse(x, y - 70 * k, 30 * k, 36 * k, fill="#f2e6c9", w=6 * k))
    return "".join(out)


@prop("skull", floating=True)
def skull(x, y, s=1.0, chin=True, brow=False, flip=False, **_):
    """Skull from the side (faces right). chin: modern chin; brow: heavy brow ridge (Neanderthal/erectus)."""
    f = -1 if flip else 1
    k = s
    X = lambda d: x + f * d * k  # noqa: E731
    Y = lambda d: y + d * k  # noqa: E731
    jaw_end = (X(90), Y(115)) if chin else (X(70), Y(110))
    d = (f"M{X(-120)},{Y(10)} C{X(-140)},{Y(-110)} {X(-20)},{Y(-150)} {X(60)},{Y(-110)} "
         f"C{X(95)},{Y(-90)} {X(110)},{Y(-60)} {X(105)},{Y(-40)} "
         + (f"L{X(125)},{Y(-40)} L{X(118)},{Y(-18)} " if brow else "")
         + f"L{X(110)},{Y(10)} L{X(125)},{Y(45)} L{X(108)},{Y(55)} L{X(110)},{Y(70)} "
         f"L{jaw_end[0]},{jaw_end[1]} "
         + (f"Q{X(100)},{Y(130)} {X(70)},{Y(130)} " if chin else f"Q{X(60)},{Y(125)} {X(40)},{Y(128)} ")
         + f"L{X(-10)},{Y(120)} L{X(-20)},{Y(60)} L{X(-80)},{Y(55)} Q{X(-115)},{Y(45)} {X(-120)},{Y(10)} Z")
    out = [path(d, fill="bone", w=7 * k),
           circle(X(58), Y(-15), 22 * k, fill="#5b4636", w=5 * k),
           poly([(X(100), Y(20)), (X(112), Y(40)), (X(96), Y(40))], fill="#5b4636", w=3 * k),
           line([(X(40), Y(78)), (X(104), Y(78))], 4 * k)]
    for i in range(4):
        out.append(line([(X(55 + i * 14), Y(70)), (X(55 + i * 14), Y(86))], 3 * k))
    return "".join(out)


@prop("tooth", floating=True)
def tooth(x, y, s=1.0, decay=False, **_):
    k = s
    out = [path(f"M{x - 70 * k},{y - 40 * k} Q{x - 75 * k},{y - 105 * k} {x - 35 * k},{y - 100 * k} Q{x},{y - 85 * k} "
                f"{x + 35 * k},{y - 100 * k} Q{x + 75 * k},{y - 105 * k} {x + 70 * k},{y - 40 * k} "
                f"Q{x + 60 * k},{y + 20 * k} {x + 45 * k},{y + 100 * k} Q{x + 30 * k},{y + 110 * k} {x + 20 * k},{y + 60 * k} "
                f"Q{x},{y + 20 * k} {x - 20 * k},{y + 60 * k} Q{x - 30 * k},{y + 110 * k} {x - 45 * k},{y + 100 * k} "
                f"Q{x - 60 * k},{y + 20 * k} {x - 70 * k},{y - 40 * k} Z", fill="bone", w=7 * k)]
    if decay:
        out.append(ellipse(x + 20 * k, y - 60 * k, 20 * k, 14 * k, fill="#5b4636", w=4 * k))
    return "".join(out)


@prop("dna", floating=True)
def dna(x, y, s=1.0, n=7, **_):
    """Vertical double helix, n = number of rungs."""
    n = max(3, int(n))
    h = 300 * s
    top = y - h / 2
    a_pts, b_pts, rungs = [], [], []
    for i in range(61):
        t = i / 60
        yy = top + t * h
        ph = t * 2 * math.pi * 1.5
        a_pts.append((x + 60 * s * math.sin(ph), yy))
        b_pts.append((x - 60 * s * math.sin(ph), yy))
    cols = ("ochre", "good", "water", RED)
    for j in range(n):
        t = (j + 0.5) / n
        yy = top + t * h
        ph = t * 2 * math.pi * 1.5
        xa, xb = x + 60 * s * math.sin(ph), x - 60 * s * math.sin(ph)
        rungs.append(line([(xa, yy), ((xa + xb) / 2, yy)], 7 * s, color=c(cols[j % 4])))
        rungs.append(line([((xa + xb) / 2, yy), (xb, yy)], 7 * s, color=c(cols[(j + 1) % 4])))
    return "".join(rungs) + line(a_pts, 9 * s) + line(b_pts, 9 * s, color=c("vein"))


@prop("blood_cells", floating=True)
def blood_cells(x, y, s=1.0, n=5, **_):
    """Cluster of n red blood cells (more cells = more oxygen carriers)."""
    rnd = random.Random(5)
    out = []
    n = max(1, int(n))
    for i in range(n):
        a = i * 2.4
        r = 0 if i == 0 else 55 * s * math.sqrt(i)
        cx, cy = x + r * math.cos(a), y + r * math.sin(a) * 0.8
        rot = rnd.uniform(-30, 30)
        out.append(ellipse(cx, cy, 44 * s, 36 * s, fill="#d24b3f", w=6 * s, rot=rot))
        out.append(ellipse(cx, cy, 20 * s, 14 * s, fill="#a8322c", w=0, rot=rot))
    return "".join(out)


@prop("mitochondria", floating=True)
def mitochondria(x, y, s=1.0, **_):
    k = s
    out = [ellipse(x, y, 150 * k, 72 * k, fill="#f0a24a", w=7 * k),
           ellipse(x, y, 128 * k, 52 * k, fill="#f7c47c", w=4 * k)]
    d = f"M{x - 110 * k},{y}"
    for i in range(8):
        xx = x - 110 * k + (i + 0.5) * 27.5 * k
        d += f" L{xx},{y + (-38 if i % 2 == 0 else 38) * k}"
    d += f" L{x + 110 * k},{y}"
    out.append(path(d, w=5 * k, stroke=c("#c46a1e")))
    return "".join(out)


@prop("eye", floating=True)
def eye(x, y, s=1.0, pupil=0.5, **_):
    """Eye from the front. pupil: 0 (pinpoint, bright light / Moken underwater) .. 1 (wide open)."""
    k = s
    pr = (8 + 30 * max(0.0, min(1.0, float(pupil)))) * k
    return "".join([path(f"M{x - 150 * k},{y} Q{x},{y - 120 * k} {x + 150 * k},{y} Q{x},{y + 120 * k} {x - 150 * k},{y} Z",
                         fill="#fff", w=7 * k),
                    circle(x, y, 55 * k, fill="#6f9a52", w=6 * k),
                    dot(x, y, pr),
                    dot(x + 18 * k, y - 20 * k, 9 * k, color="#fff")])


@prop("spine", floating=True)
def spine(x, y, s=1.0, pain=False, **_):
    """Spine from the side (S-curve of vertebrae). pain: red glow on the lower back."""
    k = s
    out = []
    n = 12
    if pain:
        out.append(circle(x - 8 * k, y + 105 * k, 70 * k, fill="#f3b2a8", w=0))
    for i in range(n):
        t = i / (n - 1)
        cy = y - 170 * k + t * 330 * k
        cx = x + 22 * k * math.sin(t * 2 * math.pi) - 10 * k
        w_ = (22 + 14 * t) * k
        out.append(f'<rect x="{cx - w_:.1f}" y="{cy - 11 * k:.1f}" width="{2 * w_:.1f}" height="{22 * k:.1f}" '
                   f'rx="{7 * k:.1f}" fill="{c("bone")}" stroke="{INK}" stroke-width="{5 * k:.1f}"/>')
        out.append(line([(cx - w_ - 4 * k, cy), (cx - w_ - 22 * k, cy + 6 * k)], 7 * k))
    out.append(path(f"M{x - 40 * k},{y + 170 * k} L{x + 30 * k},{y + 170 * k} L{x - 5 * k},{y + 230 * k} Z",
                    fill="bone", w=6 * k))
    return "".join(out)


@prop("sweat_gland", floating=True)
def sweat_gland(x, y, s=1.0, drops=3, **_):
    """Skin cross-section with a coiled sweat gland and drops on the surface."""
    k = s
    top = y - 90 * k
    out = [f'<rect x="{x - 170 * k:.1f}" y="{top:.1f}" width="{340 * k:.1f}" height="{70 * k:.1f}" fill="{c("#f6d7c3")}" '
           f'stroke="{INK}" stroke-width="{6 * k:.1f}"/>',
           f'<rect x="{x - 170 * k:.1f}" y="{top + 70 * k:.1f}" width="{340 * k:.1f}" height="{110 * k:.1f}" '
           f'fill="{c("#f3e0c4")}" stroke="{INK}" stroke-width="{6 * k:.1f}"/>',
           line([(x, top), (x - 10 * k, top + 50 * k), (x + 10 * k, top + 90 * k), (x, top + 120 * k)], 6 * k)]
    d = f"M{x},{top + 120 * k}"
    for i in range(5):
        d += f" a{22 * k},{14 * k} 0 1 {i % 2} {0},{12 * k}"
    out.append(path(d, w=6 * k, stroke=c("#c2615f")))
    for i in range(int(drops)):
        dx = (-60 + i * 55) * k
        out.append(path(f"M{x + dx},{top - 50 * k} q{-14 * k},{24 * k} 0,{36 * k} q{14 * k},{-12 * k} 0,{-36 * k}z",
                        fill="sweat", w=4 * k))
    return "".join(out)


@prop("fat_cell", floating=True)
def fat_cell(x, y, s=1.0, size=1.0, n=7, **_):
    """Cluster of fat cells; size: 0.5 (lean) .. 1.5 (filled)."""
    r = 40 * s * float(size)
    out = []
    for i in range(max(1, int(n))):
        a = i * 2.4
        rr = 0 if i == 0 else r * 1.6 * math.sqrt(i) * 0.75
        cx, cy = x + rr * math.cos(a), y + rr * math.sin(a) * 0.85
        out.append(circle(cx, cy, r, fill="fat", w=5 * s))
        out.append(dot(cx + r * 0.45, cy + r * 0.35, 5 * s, color="#b08a3a"))
    return "".join(out)
