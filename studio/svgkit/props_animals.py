"""Animals. All stand on the floor ((x, y) = bottom centre) and face right; flip: true faces left.
Except fish (floating, centre)."""
from __future__ import annotations

from .props import prop
from .style import INK, band, c, circle, dot, ellipse, line, path, poly


def _frame(x, y, s, flip):
    f = -1 if flip else 1
    return (lambda dx: x + f * dx * s), (lambda dy: y - dy * s), f


@prop("horse")
def horse(x, y, s=1.0, flip=False, color="#9a6a42", saddle=True, **_):
    """Rideable horse. Its back (saddle top) is 340·scale above the floor at x — a `ride` figure with the
    same x and scale sits on it."""
    X, Y, f = _frame(x, y, s, flip)
    dark = "#3b2a1c"
    out = [band([(X(-160), Y(300)), (X(-205), Y(230)), (X(-195), Y(150))], 16 * s, dark, 5 * s)]  # tail
    for dx, knee in ((-150, -160), (130, 140)):                                              # far legs
        out.append(band([(X(dx), Y(230)), (X(knee), Y(110)), (X(dx + 5), Y(8))], 20 * s, "#7d5534", 5 * s))
    out.append(band([(X(135), Y(285)), (X(215), Y(415))], 72 * s, color, 6 * s))             # neck
    out.append(band([(X(128), Y(330)), (X(205), Y(458))], 14 * s, dark, 4 * s))              # mane
    out.append(ellipse(X(0), Y(270), 172 * s, 72 * s, fill=color, w=7 * s))                 # body
    for dx, knee in ((-118, -124), (100, 108)):                                              # near legs
        out.append(band([(X(dx), Y(225)), (X(knee), Y(110)), (X(dx), Y(8))], 22 * s, color, 5 * s))
    for dx in (-150, 135, -118, 100):
        out.append(poly([(X(dx - 16), Y(0)), (X(dx + 18), Y(0)), (X(dx + 14), Y(20)), (X(dx - 14), Y(20))],
                        fill=dark, w=4 * s))
    out.append(ellipse(X(262), Y(418), 66 * s, 31 * s, fill=color, w=7 * s, rot=f * 38))     # head
    out.append(poly([(X(220), Y(452)), (X(214), Y(492)), (X(240), Y(460))], fill=color, w=5 * s))  # ear
    out.append(dot(X(250), Y(435), 5 * s))
    out.append(dot(X(300), Y(378), 3.5 * s))
    if saddle:
        out.append(path(f"M{X(-58)},{Y(336)} Q{X(0)},{Y(352)} {X(58)},{Y(336)} L{X(50)},{Y(262)} "
                        f"L{X(-50)},{Y(262)} Z", fill="#b8452f", w=6 * s))
        out.append(line([(X(-50), Y(280)), (X(50), Y(280))], 4 * s, color=c("grain")))
    return "".join(out)


def _ape(x, y, s, flip, fur, face, big=1.0, silver=False):
    X, Y, f = _frame(x, y, s * big, flip)
    ss = s * big
    out = [band([(X(-55), Y(140)), (X(-30), Y(78)), (X(-70), Y(10))], 34 * ss, fur, 5 * ss),      # far leg
           band([(X(45), Y(190)), (X(65), Y(95)), (X(60), Y(14))], 30 * ss, fur, 5 * ss),         # far arm
           ellipse(X(0), Y(158), 98 * ss, 66 * ss, fill=fur, w=7 * ss, rot=-f * 18)]
    if silver:
        out.append(ellipse(X(-25), Y(185), 55 * ss, 26 * ss, fill="#b9bcbd", w=0, rot=-f * 18))
    out += [band([(X(-70), Y(130)), (X(-45), Y(70)), (X(-90), Y(10))], 36 * ss, fur, 5 * ss),        # near leg
            band([(X(70), Y(180)), (X(95), Y(90)), (X(92), Y(14))], 34 * ss, fur, 5 * ss),         # near arm
            ellipse(X(96), Y(12), 26 * ss, 14 * ss, fill=fur, w=5 * ss),
            ellipse(X(-95), Y(10), 30 * ss, 12 * ss, fill=fur, w=5 * ss)]
    hx, hy = X(118), Y(222)
    if silver:
        out.append(path(f"M{X(80)},{Y(240)} Q{X(112)},{Y(300)} {X(145)},{Y(248)} Z", fill=fur, w=6 * ss))
    out += [circle(X(88), Y(232), 15 * ss, fill=face, w=5 * ss),
            circle(hx, hy, 48 * ss, fill=fur, w=7 * ss),
            ellipse(X(134), Y(214), 32 * ss, 30 * ss, fill=face, w=0),
            ellipse(X(146), Y(196), 25 * ss, 16 * ss, fill=face, w=5 * ss),
            line([(X(118), Y(236)), (X(158), Y(236))], 7 * ss),
            dot(X(128), Y(224), 5 * ss), dot(X(150), Y(224), 5 * ss),
            line([(X(138), Y(189)), (X(158), Y(191))], 4 * ss)]
    return "".join(out)


@prop("chimp")
def chimp(x, y, s=1.0, flip=False, **_):
    """Knuckle-walking chimpanzee (~ a standing figure's hip height)."""
    return _ape(x, y, s, flip, "#3d2f26", "#caa27c")


@prop("gorilla")
def gorilla(x, y, s=1.0, flip=False, **_):
    """Silverback gorilla, 1.45× the chimp."""
    return _ape(x, y, s, flip, "#2c2c2c", "#6f6f6f", big=1.45, silver=True)


@prop("bear")
def bear(x, y, s=1.0, flip=False, **_):
    X, Y, f = _frame(x, y, s, flip)
    fur, light = "#6b4a2e", "#8f6a45"
    out = [band([(X(-120), Y(150)), (X(-130), Y(10))], 44 * s, "#5a3d25", 5 * s),
           band([(X(95), Y(150)), (X(100), Y(10))], 44 * s, "#5a3d25", 5 * s),
           ellipse(X(0), Y(178), 172 * s, 92 * s, fill=fur, w=7 * s),
           circle(X(85), Y(220), 62 * s, fill=fur, w=0),
           path(f"M{X(20)},{Y(265)} Q{X(85)},{Y(300)} {X(140)},{Y(240)}", w=7 * s),
           band([(X(-95), Y(150)), (X(-100), Y(10))], 46 * s, fur, 5 * s),
           band([(X(125), Y(150)), (X(130), Y(10))], 46 * s, fur, 5 * s),
           circle(X(188), Y(248), 17 * s, fill=fur, w=5 * s),
           circle(X(212), Y(198), 56 * s, fill=fur, w=7 * s),
           ellipse(X(258), Y(182), 36 * s, 25 * s, fill=light, w=6 * s),
           dot(X(290), Y(186), 8 * s), dot(X(222), Y(212), 5 * s),
           line([(X(250), Y(165)), (X(272), Y(166))], 4 * s)]
    return "".join(out)


@prop("cheetah")
def cheetah(x, y, s=1.0, flip=False, run=True, **_):
    """Sprinting cheetah (run: false = standing)."""
    X, Y, f = _frame(x, y, s, flip)
    coat = "#e2b563"
    if run:
        far = [[(95, 135), (160, 80), (228, 22)], [(-100, 140), (-165, 88), (-238, 25)]]
        near = [[(80, 130), (135, 68), (196, 12)], [(-85, 138), (-140, 80), (-200, 12)]]
    else:
        far = [[(95, 135), (100, 70), (98, 5)], [(-100, 140), (-115, 70), (-100, 5)]]
        near = [[(75, 130), (78, 70), (80, 5)], [(-80, 138), (-95, 70), (-80, 5)]]
    out = [band([(X(-128), Y(165)), (X(-220), Y(185)), (X(-290), Y(150))], 12 * s, coat, 4 * s)]
    for pts in far:
        out.append(band([(X(a), Y(b)) for a, b in pts], 15 * s, "#c99a4c", 4 * s))
    out.append(ellipse(X(0), Y(152), 140 * s, 40 * s, fill=coat, w=7 * s, rot=f * 2))
    for pts in near:
        out.append(band([(X(a), Y(b)) for a, b in pts], 16 * s, coat, 4 * s))
    for dx, dy in ((-80, 160), (-40, 145), (0, 165), (40, 150), (-110, 145), (75, 162), (-20, 175), (20, 140)):
        out.append(dot(X(dx), Y(dy), 6 * s))
    for dx in (-240, -270):
        out.append(line([(X(dx), Y(185 if dx == -240 else 170)), (X(dx + 8), Y(165 if dx == -240 else 152))], 4 * s))
    out += [poly([(X(150), Y(200)), (X(158), Y(222)), (X(170), Y(203))], fill=coat, w=4 * s),
            ellipse(X(172), Y(178), 38 * s, 28 * s, fill=coat, w=6 * s),
            dot(X(182), Y(186), 4.5 * s), dot(X(208), Y(172), 5 * s),
            line([(X(182), Y(182)), (X(190), Y(158))], 3.5 * s)]
    return "".join(out)


@prop("fish", floating=True)
def fish(x, y, s=1.0, flip=False, color="#e39a4f", **_):
    X, Y, f = _frame(x, y, s, flip)
    return "".join([poly([(X(-50), Y(0)), (X(-92), Y(28)), (X(-88), Y(-28))], fill=color, w=5 * s),
                    ellipse(x, y, 62 * s, 28 * s, fill=color, w=6 * s),
                    path(f"M{X(-5)},{Y(25)} Q{X(10)},{Y(48)} {X(25)},{Y(24)}", fill=color, w=4 * s),
                    path(f"M{X(28)},{Y(22)} Q{X(18)},{Y(0)} {X(28)},{Y(-22)}", w=4 * s),
                    dot(X(40), Y(6), 4.5 * s)])


@prop("seal")
def seal(x, y, s=1.0, flip=False, **_):
    X, Y, f = _frame(x, y, s, flip)
    grey = "#8e979c"
    return "".join([poly([(X(-120), Y(30)), (X(-175), Y(10)), (X(-170), Y(60))], fill=grey, w=5 * s),
                    ellipse(X(0), Y(52), 135 * s, 50 * s, fill=grey, w=7 * s, rot=-f * 6),
                    circle(X(118), Y(100), 42 * s, fill=grey, w=7 * s),
                    poly([(X(40), Y(20)), (X(80), Y(2)), (X(20), Y(4))], fill="#737c81", w=5 * s),
                    dot(X(132), Y(112), 5 * s), dot(X(160), Y(96), 6 * s),
                    line([(X(150), Y(88)), (X(185), Y(80))], 3 * s), line([(X(150), Y(84)), (X(182), Y(70))], 3 * s)])


@prop("calf")
def calf(x, y, s=1.0, flip=False, **_):
    """Young cow (Milo of Croton's calf; farming scenes)."""
    X, Y, f = _frame(x, y, s, flip)
    hide_, patch = "#f3ead8", "#8a5a3a"
    out = [band([(X(-95), Y(150)), (X(-120), Y(95))], 8 * s, patch, 3 * s)]
    for dx in (-85, 70):
        out.append(band([(X(dx), Y(120)), (X(dx + 4), Y(4))], 14 * s, "#ddd2bb", 4 * s))
    out.append(ellipse(X(0), Y(150), 112 * s, 50 * s, fill=hide_, w=7 * s))
    out.append(ellipse(X(-30), Y(160), 38 * s, 24 * s, fill=patch, w=0))
    out.append(ellipse(X(45), Y(140), 22 * s, 16 * s, fill=patch, w=0))
    for dx in (-65, 90):
        out.append(band([(X(dx), Y(120)), (X(dx + 2), Y(4))], 15 * s, hide_, 4 * s))
    out += [ellipse(X(118), Y(212), 16 * s, 9 * s, fill=hide_, w=4 * s, rot=-f * 25),
            ellipse(X(140), Y(175), 34 * s, 42 * s, fill=hide_, w=6 * s, rot=-f * 20),
            ellipse(X(152), Y(145), 22 * s, 16 * s, fill="#e8b8a8", w=5 * s),
            dot(X(145), Y(190), 4.5 * s)]
    return "".join(out)
