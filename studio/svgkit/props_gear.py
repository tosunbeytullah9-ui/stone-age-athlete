"""Equipment, weapons, buildings and objects from the history of fitness.
Floor objects: (x, y) = bottom centre. Icons marked floating: (x, y) = centre."""
from __future__ import annotations

import math

from .props import prop
from .style import INK, RED, band, c, circle, dot, ellipse, line, path, poly, polar, rect


# ---------------- training equipment (floor) ----------------
@prop("kettlebell")
def kettlebell(x, y, s=1.0, **_):
    return (path(f"M{x - 38 * s},{y - 95 * s} Q{x - 45 * s},{y - 160 * s} {x},{y - 160 * s} "
                 f"Q{x + 45 * s},{y - 160 * s} {x + 38 * s},{y - 95 * s}", w=18 * s)
            + path(f"M{x - 60 * s},{y - 8 * s} Q{x - 85 * s},{y - 70 * s} {x - 40 * s},{y - 100 * s} "
                   f"Q{x},{y - 118 * s} {x + 40 * s},{y - 100 * s} Q{x + 85 * s},{y - 70 * s} {x + 60 * s},{y - 8 * s} Z",
                   fill="metal", w=7 * s))


def _club(x, y, s, L, R, fill):
    return path(f"M{x - 9 * s},{y - L * s} L{x - 7 * s},{y - L * 0.72 * s} Q{x - R * s},{y - L * 0.35 * s} "
                f"{x - R * 0.7 * s},{y} L{x + R * 0.7 * s},{y} Q{x + R * s},{y - L * 0.35 * s} {x + 7 * s},{y - L * 0.72 * s} "
                f"L{x + 9 * s},{y - L * s} Z", fill=fill, w=6 * s) + ellipse(x, y - L * s, 14 * s, 8 * s, fill=fill, w=5 * s)


@prop("indian_club")
def indian_club(x, y, s=1.0, pair=True, **_):
    """Bottle-shaped wooden club(s) standing upright."""
    xs = (x - 45 * s, x + 45 * s) if pair else (x,)
    return "".join(_club(cx, y, s, 190, 42, "#e6c89a") for cx in xs)


@prop("meel")
def meel(x, y, s=1.0, pair=True, **_):
    """Heavy Persian/Indian meels (zurkhaneh clubs), standing upright."""
    xs = (x - 70 * s, x + 70 * s) if pair else (x,)
    return "".join(_club(cx, y, s, 300, 70, "bark") for cx in xs)


@prop("barbell")
def barbell(x, y, s=1.0, **_):
    """Loaded barbell lying on the floor (side view, plates facing you)."""
    out = [line([(x - 330 * s, y - 95 * s), (x + 330 * s, y - 95 * s)], 12 * s)]
    for dx, r in ((-250, 95), (-200, 80), (200, 80), (250, 95)):
        out.append(rect(x + dx * s - 20 * s, y - 95 * s - r * s, 40 * s, 2 * r * s, "metal", rx=8 * s, w=6 * s))
    return "".join(out)


@prop("pullup_bar")
def pullup_bar(x, y, s=1.0, ancient=False, **_):
    """Two posts and a bar; a `hang` figure at the same x and scale grips it. ancient: a tree branch."""
    from .figure import HANG_HANDS
    top = y - HANG_HANDS * s
    if ancient:
        return (band([(x - 260 * s, y), (x - 245 * s, top - 40 * s)], 34 * s, "bark", 6 * s)
                + band([(x - 250 * s, top), (x + 230 * s, top + 8 * s)], 16 * s, "bark", 5 * s)
                + circle(x - 250 * s, top - 90 * s, 90 * s, fill="leaf", w=7 * s))
    return (band([(x - 200 * s, y), (x - 200 * s, top - 20 * s)], 16 * s, "metal", 5 * s)
            + band([(x + 200 * s, y), (x + 200 * s, top - 20 * s)], 16 * s, "metal", 5 * s)
            + line([(x - 215 * s, top), (x + 215 * s, top)], 12 * s))


@prop("treadwheel")
def treadwheel(x, y, s=1.0, **_):
    """1818 prison treadwheel: a big stepped drum on a frame with a handrail. A `walk` figure at the
    same x with ground = y − 505·scale (same scale) treads its top steps and holds the rail."""
    R = 230 * s
    cy = y - 255 * s
    top = cy - R - 20 * s                       # where the walker's feet are
    rail = top - 175 * s
    out = [poly([(x - 150 * s, y), (x - 40 * s, cy), (x + 40 * s, cy), (x + 150 * s, y)], fill="stone_dark", w=7 * s),
           circle(x, cy, R, fill="bark", w=8 * s)]
    for a in range(0, 360, 20):
        out.append(line([polar(x, cy, R * 0.2, a), polar(x, cy, R, a)], 4 * s, color="#5a4029"))
        out.append(poly([polar(x, cy, R, a), polar(x, cy, R + 22 * s, a), polar(x, cy, R + 22 * s, a + 9),
                         polar(x, cy, R, a + 9)], fill="clay", w=4 * s))
    out.append(circle(x, cy, R * 0.18, fill="stone", w=6 * s))
    for px in (x - 330 * s, x + 330 * s):
        out.append(line([(px, y), (px, rail)], 12 * s, color=c("stone_dark")))
    out.append(line([(x - 345 * s, rail), (x + 345 * s, rail)], 12 * s, color=c("stone_dark")))
    return "".join(out)


@prop("bed")
def bed(x, y, s=1.0, **_):
    """Modern bed; a `lie` figure fits on it with ground = y − 150·s."""
    return "".join([rect(x - 330 * s, y - 150 * s, 660 * s, 80 * s, "#e8eef2", rx=18 * s, w=7 * s),
                    rect(x - 350 * s, y - 250 * s, 40 * s, 250 * s, "furniture", rx=10 * s, w=7 * s),
                    rect(x + 310 * s, y - 180 * s, 40 * s, 180 * s, "furniture", rx=10 * s, w=7 * s),
                    rect(x - 330 * s, y - 75 * s, 660 * s, 30 * s, "furniture", rx=8 * s, w=6 * s),
                    ellipse(x - 245 * s, y - 165 * s, 60 * s, 26 * s, fill="#fff", w=6 * s)])


@prop("oxygen_tank")
def oxygen_tank(x, y, s=1.0, **_):
    return "".join([rect(x - 45 * s, y - 260 * s, 90 * s, 260 * s, "#6fa36a", rx=40 * s, w=7 * s),
                    rect(x - 16 * s, y - 295 * s, 32 * s, 40 * s, "metal", rx=4 * s, w=5 * s),
                    path(f"M{x + 10 * s},{y - 290 * s} q{90 * s},{-40 * s} {110 * s},{60 * s} q{10 * s},{50 * s} {-10 * s},{90 * s}",
                         w=6 * s),
                    ellipse(x + 95 * s, y - 130 * s, 30 * s, 22 * s, fill="#dfe8ec", w=5 * s)])


@prop("microscope")
def microscope(x, y, s=1.0, **_):
    return "".join([rect(x - 110 * s, y - 30 * s, 220 * s, 30 * s, "metal", rx=8 * s, w=6 * s),
                    band([(x + 50 * s, y - 30 * s), (x + 60 * s, y - 150 * s), (x + 20 * s, y - 230 * s)], 26 * s,
                         "metal", 5 * s),
                    rect(x - 80 * s, y - 120 * s, 150 * s, 16 * s, "#dfe4e7", rx=4 * s, w=5 * s),
                    f'<rect x="{x - 45 * s:.1f}" y="{y - 300 * s:.1f}" width="{40 * s:.1f}" height="{170 * s:.1f}" rx="{8 * s:.1f}" '
                    f'fill="{c("#dfe4e7")}" stroke="{INK}" stroke-width="{6 * s:.1f}" transform="rotate(20 {x - 25 * s:.1f} {y - 215 * s:.1f})"/>'])


@prop("radio")
def radio(x, y, s=1.0, **_):
    """1930s radio set (radio calisthenics)."""
    out = [rect(x - 120 * s, y - 190 * s, 240 * s, 190 * s, "bark", rx=40 * s, w=7 * s),
           circle(x - 25 * s, y - 100 * s, 55 * s, fill="#e8d8b6", w=6 * s)]
    for i in range(-2, 3):
        out.append(line([(x - 25 * s + i * 18 * s, y - 145 * s), (x - 25 * s + i * 18 * s, y - 55 * s)], 3 * s))
    out += [circle(x + 70 * s, y - 130 * s, 16 * s, fill="grain", w=5 * s),
            circle(x + 70 * s, y - 70 * s, 16 * s, fill="grain", w=5 * s)]
    return "".join(out)


@prop("protein_tub")
def protein_tub(x, y, s=1.0, **_):
    return "".join([rect(x - 70 * s, y - 180 * s, 140 * s, 180 * s, "#2f3b45", rx=16 * s, w=7 * s),
                    rect(x - 76 * s, y - 205 * s, 152 * s, 34 * s, RED, rx=8 * s, w=6 * s),
                    rect(x - 45 * s, y - 130 * s, 90 * s, 70 * s, "#f3f5f6", rx=8 * s, w=5 * s),
                    circle(x, y - 95 * s, 18 * s, fill=RED, w=0)])


@prop("amphora")
def amphora(x, y, s=1.0, **_):
    """Clay jar (olive oil, wine, water)."""
    return path(f"M{x - 20 * s},{y} Q{x - 85 * s},{y - 100 * s} {x - 60 * s},{y - 170 * s} L{x - 25 * s},{y - 205 * s} "
                f"L{x - 25 * s},{y - 245 * s} L{x + 25 * s},{y - 245 * s} L{x + 25 * s},{y - 205 * s} "
                f"L{x + 60 * s},{y - 170 * s} Q{x + 85 * s},{y - 100 * s} {x + 20 * s},{y} Z", fill="clay", w=7 * s) \
        + path(f"M{x - 25 * s},{y - 230 * s} q{-50 * s},0 {-40 * s},{50 * s}", w=7 * s) \
        + path(f"M{x + 25 * s},{y - 230 * s} q{50 * s},0 {40 * s},{50 * s}", w=7 * s)


# ---------------- buildings & monuments (floor) ----------------
@prop("pyramid")
def pyramid(x, y, s=1.0, **_):
    out = [poly([(x - 420 * s, y), (x, y - 380 * s), (x + 420 * s, y)], fill="#e2c48a", w=8 * s),
           poly([(x, y - 380 * s), (x + 420 * s, y), (x + 150 * s, y)], fill="#c9a86c", w=0)]
    for i in range(1, 7):
        yy = y - i * 54 * s
        half = 420 * s * (1 - i * 54 / 380)
        out.append(line([(x - half, yy), (x + half, yy)], 3 * s, color="#9c7f4c"))
    out.append(poly([(x - 420 * s, y), (x, y - 380 * s), (x + 420 * s, y)], w=8 * s))
    return "".join(out)


@prop("column")
def column(x, y, s=1.0, broken=False, **_):
    """Greek/Roman column (broken: a ruin)."""
    top = y - (260 if broken else 440) * s
    out = [rect(x - 70 * s, y - 30 * s, 140 * s, 30 * s, "#e9e0cc", w=6 * s)]
    if broken:
        out.append(path(f"M{x - 48 * s},{y - 30 * s} L{x - 48 * s},{top + 20 * s} L{x - 10 * s},{top} L{x + 12 * s},{top + 28 * s} "
                        f"L{x + 48 * s},{top + 8 * s} L{x + 48 * s},{y - 30 * s} Z", fill="#e9e0cc", w=6 * s))
    else:
        out.append(rect(x - 48 * s, top + 40 * s, 96 * s, y - 30 * s - top - 40 * s, "#e9e0cc", w=6 * s))
        out.append(rect(x - 80 * s, top, 160 * s, 42 * s, "#e9e0cc", rx=6 * s, w=6 * s))
    for dx in (-24, 0, 24):
        out.append(line([(x + dx * s, y - 38 * s), (x + dx * s, top + (50 if not broken else 40) * s)], 3 * s,
                        color="#b9ad93"))
    return "".join(out)


@prop("stone_block")
def stone_block(x, y, s=1.0, sled=False, **_):
    """Big cut stone block (pyramids, monuments). sled: on a wooden sledge for hauling."""
    out = []
    base = y
    if sled:
        out.append(path(f"M{x - 200 * s},{y - 30 * s} L{x + 170 * s},{y - 30 * s} Q{x + 230 * s},{y - 30 * s} "
                        f"{x + 240 * s},{y - 80 * s}", w=14 * s, stroke=c("bark")))
        out.append(line([(x - 200 * s, y - 12 * s), (x + 190 * s, y - 12 * s)], 12 * s, color=c("bark")))
        base = y - 40 * s
    out.append(rect(x - 170 * s, base - 200 * s, 340 * s, 200 * s, "#d9bf8c", rx=6 * s, w=8 * s))
    out.append(line([(x - 120 * s, base - 150 * s), (x - 60 * s, base - 140 * s)], 3 * s, color="#9c7f4c"))
    return "".join(out)


@prop("pillar")
def pillar(x, y, s=1.0, **_):
    """T-shaped Göbekli Tepe pillar with relief arms."""
    out = [rect(x - 55 * s, y - 440 * s, 110 * s, 440 * s, "#d8c9a8", rx=6 * s, w=8 * s),
           rect(x - 150 * s, y - 540 * s, 300 * s, 110 * s, "#d8c9a8", rx=8 * s, w=8 * s),
           path(f"M{x - 45 * s},{y - 360 * s} Q{x - 20 * s},{y - 250 * s} {x + 30 * s},{y - 240 * s}", w=5 * s),
           path(f"M{x + 45 * s},{y - 330 * s} Q{x + 30 * s},{y - 230 * s} {x - 10 * s},{y - 225 * s}", w=5 * s),
           rect(x - 45 * s, y - 180 * s, 90 * s, 20 * s, "clay", rx=4 * s, w=4 * s)]
    return "".join(out)


# ---------------- boats ----------------
@prop("boat")
def boat(x, y, s=1.0, flip=False, outrigger=False, sail=False, **_):
    """Dugout canoe; (x, y) = centre on the waterline. People inside: figure ground = y − 25·scale
    (use order: figures_first so the hull hides their legs)."""
    f = -1 if flip else 1
    X = lambda d: x + f * d * s  # noqa: E731
    out = []
    if sail:
        out.append(line([(X(0), y - 30 * s), (X(0), y - 420 * s)], 8 * s, color=c("bark")))
        out.append(path(f"M{X(10)},{y - 400 * s} Q{X(170)},{y - 250 * s} {X(10)},{y - 80 * s} Z", fill="cloth", w=6 * s))
    if outrigger:
        for d in (-110, 110):
            out.append(line([(X(d), y - 45 * s), (X(d + 40), y - 75 * s)], 7 * s, color=c("bark")))
    out.append(path(f"M{X(-300)},{y - 60 * s} L{X(300)},{y - 60 * s} Q{X(250)},{y + 30 * s} {X(150)},{y + 30 * s} "
                    f"L{X(-150)},{y + 30 * s} Q{X(-250)},{y + 30 * s} {X(-300)},{y - 60 * s} Z", fill="bark", w=7 * s))
    out.append(line([(X(-270), y - 38 * s), (X(270), y - 38 * s)], 4 * s, color="#5a4029"))
    if outrigger:
        out.append(line([(X(-110), y - 60 * s), (X(-60), y - 120 * s), (X(60), y - 120 * s), (X(110), y - 60 * s)],
                        7 * s, color=c("bark")))
    return "".join(out)


# ---------------- icons (floating) ----------------
@prop("shield", floating=True)
def shield(x, y, s=1.0, kind="round", **_):
    """kind: round (Greek hoplon / Viking) | scutum (Roman, red rectangle)."""
    if kind == "scutum":
        return (rect(x - 80 * s, y - 130 * s, 160 * s, 260 * s, RED, rx=22 * s, w=8 * s)
                + circle(x, y, 26 * s, fill="bronze", w=6 * s)
                + line([(x, y - 110 * s), (x, y - 32 * s)], 7 * s, color=c("grain"))
                + line([(x, y + 32 * s), (x, y + 110 * s)], 7 * s, color=c("grain")))
    return circle(x, y, 120 * s, fill="bronze", w=8 * s) + circle(x, y, 80 * s, fill="none", w=5 * s) \
        + circle(x, y, 22 * s, fill="steel", w=6 * s)


@prop("sword", floating=True)
def sword(x, y, s=1.0, **_):
    a, b = (x - 150 * s, y + 150 * s), (x + 150 * s, y - 150 * s)
    g = (x - 80 * s, y + 80 * s)
    return (poly([(g[0] + 10 * s, g[1] - 10 * s), (g[0] - 2 * s, g[1] - 22 * s), b, (g[0] + 22 * s, g[1] + 2 * s)],
                 fill="#dfe4e7", w=6 * s)
            + line([(g[0] - 35 * s, g[1] - 35 * s), (g[0] + 35 * s, g[1] + 35 * s)], 12 * s, color=c("bark"))
            + line([g, a], 12 * s, color=c("bark")) + circle(a[0], a[1], 12 * s, fill="bronze", w=5 * s))


@prop("bow", floating=True)
def bow(x, y, s=1.0, **_):
    t1, t2 = (x - 40 * s, y - 170 * s), (x - 40 * s, y + 170 * s)
    return (line([t1, t2], 3 * s, color="#5a5a5a")
            + path(f"M{t1[0]},{t1[1]} Q{x + 150 * s},{y} {t2[0]},{t2[1]}", w=18 * s)
            + path(f"M{t1[0]},{t1[1]} Q{x + 150 * s},{y} {t2[0]},{t2[1]}", w=9 * s, stroke=c("bark"))
            + line([(x - 90 * s, y), (x + 120 * s, y)], 5 * s)
            + poly([(x + 120 * s, y - 12 * s), (x + 155 * s, y), (x + 120 * s, y + 12 * s)], fill="stone", w=4 * s)
            + poly([(x - 90 * s, y), (x - 110 * s, y - 16 * s), (x - 70 * s, y - 16 * s), (x - 60 * s, y)], fill=RED, w=3 * s))


@prop("helmet", floating=True)
def helmet(x, y, s=1.0, kind="roman", **_):
    """kind: roman (crest) | knight (great helm) | samurai."""
    if kind == "knight":
        return (path(f"M{x - 95 * s},{y + 110 * s} L{x - 95 * s},{y - 40 * s} Q{x},{y - 140 * s} {x + 95 * s},{y - 40 * s} "
                     f"L{x + 95 * s},{y + 110 * s} Z", fill="steel", w=8 * s)
                + line([(x - 70 * s, y), (x + 70 * s, y)], 14 * s) + line([(x, y + 20 * s), (x, y + 95 * s)], 6 * s))
    if kind == "samurai":
        return (path(f"M{x - 100 * s},{y + 10 * s} A{100 * s},{100 * s} 0 0 1 {x + 100 * s},{y + 10 * s} Z", fill="#2f3b45", w=7 * s)
                + path(f"M{x - 100 * s},{y + 10 * s} Q{x - 160 * s},{y + 60 * s} {x - 140 * s},{y + 110 * s} L{x - 85 * s},{y + 30 * s} Z",
                       fill="#2f3b45", w=6 * s)
                + path(f"M{x + 100 * s},{y + 10 * s} Q{x + 160 * s},{y + 60 * s} {x + 140 * s},{y + 110 * s} L{x + 85 * s},{y + 30 * s} Z",
                       fill="#2f3b45", w=6 * s)
                + path(f"M{x - 15 * s},{y - 85 * s} L{x - 80 * s},{y - 170 * s} M{x + 15 * s},{y - 85 * s} L{x + 80 * s},{y - 170 * s}",
                       w=10 * s, stroke=c("grain")))
    return (path(f"M{x - 100 * s},{y + 20 * s} A{100 * s},{105 * s} 0 0 1 {x + 100 * s},{y + 20 * s} Z", fill="bronze", w=7 * s)
            + path(f"M{x - 95 * s},{y + 10 * s} L{x - 90 * s},{y + 110 * s} L{x - 55 * s},{y + 90 * s} L{x - 60 * s},{y + 15 * s} Z",
                   fill="bronze", w=6 * s)
            + path(f"M{x - 85 * s},{y - 55 * s} Q{x},{y - 180 * s} {x + 85 * s},{y - 55 * s} Q{x},{y - 90 * s} {x - 85 * s},{y - 55 * s} Z",
                   fill=RED, w=6 * s)
            + line([(x - 100 * s, y + 20 * s), (x + 110 * s, y + 20 * s)], 9 * s))


@prop("sandal", floating=True)
def sandal(x, y, s=1.0, **_):
    """Huarache / ancient sandal from above-side."""
    return (path(f"M{x - 130 * s},{y + 20 * s} Q{x - 140 * s},{y - 20 * s} {x - 90 * s},{y - 25 * s} L{x + 110 * s},{y - 30 * s} "
                 f"Q{x + 150 * s},{y - 10 * s} {x + 120 * s},{y + 25 * s} Z", fill="#b98b52", w=7 * s)
            + path(f"M{x + 60 * s},{y - 28 * s} Q{x - 10 * s},{y - 110 * s} {x - 80 * s},{y - 25 * s}", w=7 * s, stroke=c("bark"))
            + line([(x + 80 * s, y - 30 * s), (x - 20 * s, y - 85 * s)], 6 * s, color=c("bark")))


@prop("shoe", floating=True)
def shoe(x, y, s=1.0, **_):
    """Modern cushioned running shoe."""
    return (path(f"M{x - 140 * s},{y + 40 * s} L{x - 135 * s},{y - 50 * s} Q{x - 90 * s},{y - 70 * s} {x - 40 * s},{y - 40 * s} "
                 f"L{x + 60 * s},{y - 10 * s} Q{x + 150 * s},{y} {x + 145 * s},{y + 40 * s} Z", fill="#e9edf0", w=7 * s)
            + rect(x - 145 * s, y + 30 * s, 295 * s, 35 * s, "#f7f7f7", rx=14 * s, w=6 * s)
            + path(f"M{x - 110 * s},{y + 5 * s} Q{x - 20 * s},{y - 10 * s} {x + 60 * s},{y + 15 * s}", w=8 * s, stroke=RED)
            + line([(x - 60 * s, y - 45 * s), (x - 40 * s, y - 25 * s)], 4 * s)
            + line([(x - 30 * s, y - 35 * s), (x - 10 * s, y - 15 * s)], 4 * s))


@prop("pedometer", floating=True)
def pedometer(x, y, s=1.0, value=0.7, **_):
    """1960s step counter; value 0..1 = needle position."""
    out = [rect(x - 90 * s, y - 120 * s, 180 * s, 240 * s, "#e9e3d6", rx=40 * s, w=7 * s),
           circle(x, y - 10 * s, 68 * s, fill="#fff", w=6 * s)]
    for a in range(-210, 31, 30):
        out.append(line([polar(x, y - 10 * s, 50 * s, a), polar(x, y - 10 * s, 62 * s, a)], 4 * s))
    out.append(line([(x, y - 10 * s), polar(x, y - 10 * s, 52 * s, -210 + 240 * float(value))], 6 * s, color=RED))
    out.append(rect(x - 30 * s, y - 150 * s, 60 * s, 34 * s, "metal", rx=6 * s, w=5 * s))
    out.append(rect(x - 40 * s, y + 70 * s, 80 * s, 26 * s, "metal", rx=6 * s, w=5 * s))
    return "".join(out)


@prop("stopwatch", floating=True)
def stopwatch(x, y, s=1.0, value=0.25, **_):
    """value 0..1 = hand position around the dial (shaded sector = elapsed)."""
    r = 110 * s
    v = max(0.0, min(0.999, float(value)))
    out = [rect(x - 22 * s, y - r - 45 * s, 44 * s, 30 * s, "metal", rx=6 * s, w=5 * s),
           line([polar(x, y, r, -45), polar(x, y, r + 25 * s, -45)], 12 * s),
           circle(x, y, r, fill="#fff", w=8 * s)]
    if v > 0:
        ex, ey = polar(x, y, r - 12 * s, -90 + 360 * v)
        big = 1 if v > 0.5 else 0
        out.append(f'<path d="M{x:.1f},{y:.1f} L{x:.1f},{y - r + 12 * s:.1f} A{r - 12 * s:.1f},{r - 12 * s:.1f} 0 {big} 1 '
                   f'{ex:.1f},{ey:.1f} Z" fill="{c("#f3c9a8")}"/>')
    for a in range(0, 360, 30):
        out.append(line([polar(x, y, r - 18 * s, a), polar(x, y, r - 6 * s, a)], 4 * s))
    out.append(line([(x, y), polar(x, y, r * 0.8, -90 + 360 * v)], 7 * s, color=RED))
    out.append(dot(x, y, 9 * s))
    return "".join(out)


@prop("thermometer", floating=True)
def thermometer(x, y, s=1.0, value=0.6, **_):
    """value 0..1 = liquid level (cold .. hot)."""
    v = max(0.0, min(1.0, float(value)))
    col = "vein" if v < 0.35 else RED
    top, bot = y - 150 * s, y + 90 * s
    lvl = bot - (bot - top) * v
    return "".join([rect(x - 26 * s, top - 20 * s, 52 * s, bot - top + 40 * s, "#fff", rx=26 * s, w=7 * s),
                    f'<rect x="{x - 12 * s:.1f}" y="{lvl:.1f}" width="{24 * s:.1f}" height="{bot - lvl + 20 * s:.1f}" fill="{c(col)}"/>',
                    circle(x, y + 125 * s, 44 * s, fill=col, w=7 * s)]
                   + [line([(x + 26 * s, top + i * 40 * s), (x + 44 * s, top + i * 40 * s)], 4 * s) for i in range(6)])


@prop("scroll", floating=True)
def scroll(x, y, s=1.0, **_):
    """Ancient text/parchment (wavy lines stand for writing — no real text)."""
    out = [rect(x - 150 * s, y - 100 * s, 300 * s, 200 * s, "#f3e6c4", w=7 * s),
           rect(x - 175 * s, y - 115 * s, 40 * s, 230 * s, "#e3cf9e", rx=20 * s, w=7 * s),
           rect(x + 135 * s, y - 115 * s, 40 * s, 230 * s, "#e3cf9e", rx=20 * s, w=7 * s)]
    for i in range(4):
        yy = y - 60 * s + i * 40 * s
        out.append(path(f"M{x - 110 * s},{yy} q{20 * s},{-10 * s} {40 * s},0 t{40 * s},0 t{40 * s},0 t{40 * s},0 t{40 * s},0",
                        w=4 * s, stroke=c("#8c7a5a")))
    return "".join(out)


@prop("book", floating=True)
def book(x, y, s=1.0, **_):
    out = [path(f"M{x},{y - 90 * s} Q{x - 90 * s},{y - 120 * s} {x - 190 * s},{y - 95 * s} L{x - 190 * s},{y + 95 * s} "
                f"Q{x - 90 * s},{y + 70 * s} {x},{y + 100 * s} Q{x + 90 * s},{y + 70 * s} {x + 190 * s},{y + 95 * s} "
                f"L{x + 190 * s},{y - 95 * s} Q{x + 90 * s},{y - 120 * s} {x},{y - 90 * s} Z", fill="#fbf6ea", w=7 * s),
           line([(x, y - 90 * s), (x, y + 100 * s)], 5 * s)]
    for i in range(4):
        yy = y - 50 * s + i * 35 * s
        out.append(line([(x - 160 * s, yy), (x - 30 * s, yy)], 4 * s, color="#9aa4ab"))
        out.append(line([(x + 30 * s, yy), (x + 160 * s, yy)], 4 * s, color="#9aa4ab"))
    return "".join(out)


@prop("flag")
def flag(x, y, s=1.0, color=RED, **_):
    """Flag on a pole planted in the ground (summit, finish, army standard)."""
    top = y - 420 * s
    return (line([(x, y), (x, top)], 9 * s, color=c("bark"))
            + path(f"M{x + 4 * s},{top + 8 * s} Q{x + 90 * s},{top - 20 * s} {x + 200 * s},{top + 20 * s} "
                   f"L{x + 200 * s},{top + 130 * s} Q{x + 90 * s},{top + 90 * s} {x + 4 * s},{top + 118 * s} Z", fill=color, w=6 * s)
            + circle(x, top - 8 * s, 12 * s, fill="grain", w=5 * s))


@prop("map_pin", floating=True)
def map_pin(x, y, s=1.0, color=RED, **_):
    """Location marker; (x, y) = the tip that touches the map."""
    return (path(f"M{x},{y} C{x - 40 * s},{y - 60 * s} {x - 75 * s},{y - 95 * s} {x - 75 * s},{y - 140 * s} "
                 f"A{75 * s},{75 * s} 0 1 1 {x + 75 * s},{y - 140 * s} C{x + 75 * s},{y - 95 * s} {x + 40 * s},{y - 60 * s} {x},{y} Z",
                 fill=color, w=7 * s)
            + circle(x, y - 140 * s, 28 * s, fill="#fff", w=6 * s))


@prop("bread", floating=True)
def bread(x, y, s=1.0, **_):
    return (path(f"M{x - 130 * s},{y + 40 * s} Q{x - 150 * s},{y - 70 * s} {x},{y - 75 * s} Q{x + 150 * s},{y - 70 * s} "
                 f"{x + 130 * s},{y + 40 * s} Z", fill="#d99a4e", w=7 * s)
            + "".join(path(f"M{x + d * s},{y - 50 * s} q{20 * s},{25 * s} {10 * s},{55 * s}", w=5 * s, stroke=c("#9c6428"))
                      for d in (-70, -20, 30, 80)))


@prop("wreath", floating=True)
def wreath(x, y, s=1.0, **_):
    """Olive wreath (ancient Olympic victory)."""
    out = []
    for side in (-1, 1):
        for i in range(7):
            a = 110 + i * 22
            px, py = polar(x, y, 95 * s, a if side < 0 else 180 - a)
            out.append(ellipse(px, py, 26 * s, 11 * s, fill="leaf", w=4 * s, rot=(a + 90) if side < 0 else (90 - a)))
    out.insert(0, path(f"M{x - 20 * s},{y + 95 * s} A{95 * s},{95 * s} 0 1 1 {x + 20 * s},{y + 95 * s}", w=6 * s,
                       stroke=c("bark")))
    return "".join(out)


@prop("medal", floating=True)
def medal(x, y, s=1.0, color="grain", **_):
    return (poly([(x - 60 * s, y - 150 * s), (x - 20 * s, y - 150 * s), (x + 10 * s, y - 40 * s), (x - 30 * s, y - 40 * s)],
                 fill=RED, w=5 * s)
            + poly([(x + 60 * s, y - 150 * s), (x + 20 * s, y - 150 * s), (x - 10 * s, y - 40 * s), (x + 30 * s, y - 40 * s)],
                   fill="vein", w=5 * s)
            + circle(x, y + 20 * s, 70 * s, fill=color, w=7 * s) + circle(x, y + 20 * s, 45 * s, fill="none", w=4 * s))


@prop("dumbbell", floating=True)
def dumbbell(x, y, s=1.0, ancient=False, **_):
    """Dumbbell icon; ancient: Greek stone halteres."""
    if ancient:
        return (path(f"M{x - 120 * s},{y - 50 * s} Q{x - 150 * s},{y + 30 * s} {x - 70 * s},{y + 45 * s} L{x - 60 * s},{y} "
                     f"L{x + 60 * s},{y} L{x + 70 * s},{y + 45 * s} Q{x + 150 * s},{y + 30 * s} {x + 120 * s},{y - 50 * s} "
                     f"L{x + 70 * s},{y - 20 * s} L{x - 70 * s},{y - 20 * s} Z", fill="stone", w=7 * s))
    out = [line([(x - 110 * s, y), (x + 110 * s, y)], 16 * s)]
    for dx in (-100, -70, 70, 100):
        h = 70 if abs(dx) == 100 else 95
        out.append(rect(x + dx * s - 14 * s, y - h * s, 28 * s, 2 * h * s, "metal", rx=8 * s, w=6 * s))
    return "".join(out)
