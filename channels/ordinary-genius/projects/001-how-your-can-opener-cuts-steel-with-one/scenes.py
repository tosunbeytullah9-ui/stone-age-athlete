"""Scene plan of 001 (Ordinary Genius), written as code: python scenes.py > plan.yaml, then
python -m studio apply-plan 001-how-your-can-opener-cuts-steel-with-one plan.yaml --channel ordinary-genius

Most scenes are code-drawn (`comp: mech`, docs/REMOTION.md → mech); every movement starts on a spoken word
("@crank" = when "crank" is said in the scene). Six scenes are AI pictures (people and history only).
The drawings (can, opener, rim cross-section, lever, gears...) are helpers below, so every scene draws the same
object the same way. Change a helper, re-run, apply-plan: only the scenes whose props changed are re-rendered.
"""
from __future__ import annotations

import sys

import yaml


# ------------------------------------------------------------------ primitives
def it(kind: str, **k) -> dict:
    d = {"kind": kind}
    d.update({a: b for a, b in k.items() if b is not None})
    return d


def grp(items: list, **k) -> dict:
    return it("group", items=items, **k)


def text(s: str, x: float, y: float, size: int = 60, at=None, **k) -> dict:
    return it("text", text=s, x=x, y=y, size=size, **({"in": at} if at is not None else {}), **k)


def formula(s: str, x: float, y: float, size: int = 64, at=None, **k) -> dict:
    return it("formula", text=s, x=x, y=y, size=size, bg="bg2", **({"in": at} if at is not None else {}), **k)


def label(s: str, x: float, y: float, to, at=None, **k) -> dict:
    return it("label", text=s, x=x, y=y, to=list(to), **({"in": at} if at is not None else {}), **k)


def arrow(x, y, to, color="yellow", at=None, **k) -> dict:
    return it("arrow", x=x, y=y, to=list(to), color=color, **({"in": at} if at is not None else {}), **k)


def mech(items: list, camera=None, drift=None, bg=None) -> dict:
    v = {"comp": "mech", "items": items}
    if camera:
        v["camera"] = camera
    if drift is not None:
        v["drift"] = drift
    if bg is not None:
        v["bg"] = bg
    return v


# ------------------------------------------------------------------ drawings
def can_side(x, y, w=340, h=420, id="can", band="coral", ridges=True, glow_ridges=None, at=None, **k) -> dict:
    hw, ry = w / 2, w * 0.13
    items = [
        it("ellipse", y=h / 2, rx=hw, ry=ry, fill="steel2"),
        it("rect", w=w, h=h, fill="steel"),
        it("rect", y=h * 0.06, w=w, h=h * 0.48, fill=band),
    ]
    if ridges:
        for i, dy in enumerate((-h * 0.38, -h * 0.30, h * 0.37, h * 0.44)):
            items.append(it("line", id=f"{id}-r{i}", x=-hw + 12, y=dy, to=[w - 24, 0], stroke="steel2", sw=6,
                            glow="yellow" if glow_ridges else None,
                            **({"in": glow_ridges, "keys": [{"at": glow_ridges, "stroke": "yellow", "dur": 0.4}]}
                               if glow_ridges else {})))
    items += [
        it("ellipse", y=-h / 2, rx=hw, ry=ry, fill="steel"),
        it("ellipse", y=-h / 2, rx=hw - 18, ry=ry - 7, fill="steel2", sw=4),
    ]
    return grp(items, id=id, x=x, y=y, **({"in": at} if at is not None else {}), **k)


def opener(x, y, s=1.0, id="op", squeeze=None, twist=None, glow_wheel=None, glow_handles=None, at=None, **k) -> dict:
    """Side view of a hand crank opener; origin = where the cutting wheel meets the rim."""
    up = it("rect", id=f"{id}-up", x=40, y=-58, w=430, h=46, r=23, ax=0, ay=0.5, fill="coral", rotate=-36,
            glow="yellow" if glow_handles else None,
            keys=([{"at": squeeze, "rotate": -27, "dur": 0.5, "ease": "back"}] if squeeze else None))
    lo = it("rect", id=f"{id}-lo", x=40, y=-22, w=430, h=46, r=23, ax=0, ay=0.5, fill="teal", rotate=-18,
            glow="yellow" if glow_handles else None)
    head = it("rect", x=40, y=-44, w=170, h=120, r=22, fill="dark")
    wheel = grp([it("circle", r=34, fill="steel"), it("circle", r=12, fill="steel2", sw=4)], id=f"{id}-cw", y=-6,
                glow="yellow" if glow_wheel else None,
                **({"keys": [{"at": glow_wheel, "scale": 1.15, "dur": 0.3, "ease": "back"}]} if glow_wheel else {}))
    key = grp([it("ellipse", y=-58, rx=24, ry=56, fill="yellow"), it("ellipse", y=58, rx=24, ry=56, fill="yellow"),
               it("circle", r=18, fill="dark")], id=f"{id}-key", x=100, y=-46,
              **({"spin": {"speed": 260, "from": twist}} if twist else {}))
    return grp([lo, up, head, wheel, key], id=id, x=x, y=y, scale=s, **({"in": at} if at is not None else {}), **k)


def rim_section(id="rim", lid_cut=None) -> list:
    """Close-up cross-section of the rim: the lid, the rolled seam and the wall (fixed layout, 1920×1080)."""
    items = [
        it("rect", id=f"{id}-lid", x=330, y=600, w=1000, h=26, ax=0, fill="steel"),
        it("rect", id=f"{id}-wall", x=1352, y=860, w=26, h=440, fill="steel"),
        it("rect", id=f"{id}-seam", x=1352, y=600, w=110, h=90, r=36, fill="steel2"),
    ]
    if lid_cut:
        items.append(it("line", x=1230, y=588, to=[0, 26], stroke="yellow", sw=7, glow="yellow", **{"in": lid_cut}))
    return items


def cutting_wheel(x=1230, y=470, r=110, id="cw", at=None, **k) -> dict:
    return grp([it("circle", r=r, fill="steel"), it("circle", r=r * 0.72, fill="steel2", sw=4),
                it("circle", r=r * 0.2, fill="dark")], id=id, x=x, y=y, **({"in": at} if at is not None else {}), **k)


def feed_wheel(x=1395, y=740, r=100, id="fw", at=None, **k) -> dict:
    return it("gear", id=id, x=x, y=y, r=r, teeth=22, depth=18, hole=20, fill="yellow",
              **({"in": at} if at is not None else {}), **k)


def lid_top(x, y, r=300, id="lid", at=None, **k) -> dict:
    return grp([it("circle", r=r, fill="steel"), it("circle", r=r - 26, fill="steel2", sw=4)], id=id, x=x, y=y,
               **({"in": at} if at is not None else {}), **k)


def arc_path(r: float, a0: float = -90, a1: float = 270) -> str:
    import math
    p0 = (r * math.cos(math.radians(a0)), r * math.sin(math.radians(a0)))
    if a1 - a0 >= 359.9:
        return (f"M{p0[0]:.1f} {p0[1]:.1f} A {r} {r} 0 1 1 {-p0[0]:.1f} {-p0[1]:.1f} "
                f"A {r} {r} 0 1 1 {p0[0]:.1f} {p0[1]:.1f}")
    p1 = (r * math.cos(math.radians(a1)), r * math.sin(math.radians(a1)))
    return f"M{p0[0]:.1f} {p0[1]:.1f} A {r} {r} 0 {1 if a1 - a0 > 180 else 0} 1 {p1[0]:.1f} {p1[1]:.1f}"


def lever_bar(x, y, length=1100, pivot_at=0.78, id="lev", tilt=None, at=None) -> list:
    """A bar on a triangular pivot. Returns the bar group (rotates about the pivot) and the pivot."""
    px = x + length * pivot_at
    bar = grp([it("rect", x=-length * pivot_at, w=length, h=34, r=17, ax=0, fill="violet")], id=id, x=px, y=y,
              **({"keys": [{"at": tilt[0], "rotate": tilt[1], "dur": 0.9, "ease": "back"}]} if tilt else {}),
              **({"in": at} if at is not None else {}))
    tri = it("poly", id=f"{id}-pv", x=px, y=y + 17, points=[[0, 0], [-60, 100], [60, 100]], fill="yellow",
             **({"in": at} if at is not None else {}))
    return [bar, tri]


def person(x, y, s=1.0, id="kid", fill="sky", at=None, **k) -> dict:
    return grp([it("circle", y=-120, r=42, fill="cream"), it("rect", y=-30, w=90, h=120, r=40, fill=fill),
                it("circle", x=-14, y=-126, r=5, fill="line", sw=0), it("circle", x=14, y=-126, r=5, fill="line", sw=0)],
               id=id, x=x, y=y, scale=s, **({"in": at} if at is not None else {}), **k)


def gemini(prompt: str) -> dict:
    return {"prompt": prompt, "characters": []}


# ------------------------------------------------------------------ the scenes
SCENES: list[tuple[str, int, dict, dict | None]] = []   # (head shot, number of shots, visual, sound)


def scene(head: str, n: int, visual: dict, sound: dict | None = None) -> None:
    SCENES.append((head, n, visual, sound))


# 1 · A dinner you opened with a hammer
scene("s001", 3, gemini("Wide shot of a wooden sailing ship of the 1820s frozen into Arctic sea ice under a pale "
                        "sky, two sailors in heavy wool coats and caps on the snowy deck beside an open wooden crate "
                        "full of plain metal food tins, breath steaming, icebergs on the horizon"))
scene("s004", 1, mech([
    can_side(820, 600, id="can"),
    grp([it("rect", w=34, h=230, fill="steel", ax=0.5, ay=1), it("poly", points=[[-17, 0], [17, 0], [0, 40]], fill="steel2")],
        id="chisel", x=760, y=360, rotate=-22, **{"in": "@chisel"}),
    grp([it("rect", w=36, h=300, r=14, fill="gold", ay=0), it("rect", y=-10, w=150, h=70, r=12, fill="dark")],
        id="hammer", x=1010, y=150, rotate=40, pivot=[0, 300], **{"in": "@hammer"},
        keys=[{"at": "@chisel+0.1", "rotate": 8, "dur": 0.18, "ease": "in"}, {"at": "@chisel+0.3", "rotate": 30, "dur": 0.4}]),
    it("particles", id="sparks", x=740, y=330, w=120, h=90, count=10, size=7, mode="steam", color="yellow",
       **{"in": "@chisel+0.28"}, out="@chisel+0.9"),
    text("Cut around the top", 1420, 560, 58, at=0, bg="cream", fill="line", outline=False, rotate=-4),
], drift=0.04), {"sfx": [{"id": "knock", "at": "chisel"}]})
scene("s005", 2, mech([
    it("line", x=260, y=640, to=[1400, 0], stroke="muted", sw=8, **{"in": 0}),
    grp([can_side(0, -150, w=150, h=180, id="can1"), it("circle", r=18, fill="coral")], x=360, y=640, **{"in": "@patented"}),
    text("1810", 360, 760, 72, at="@ten"),
    it("rect", id="gap", x=380, y=640, w=1200, h=26, r=13, ax=0, fill="coral", sx=0, **{"in": "@ten+0.3"},
       keys=[{"at": "@ten+0.3", "sx": 1, "dur": 2.4, "ease": "linear"}]),
    grp([opener(0, -110, s=0.45, id="op1"), it("circle", r=18, fill="teal")], x=1580, y=640, **{"in": "@opener"}),
    text("1858", 1580, 760, 72, at="@fifty"),
]))

# 2 · The tool in your drawer
scene("s007", 4, mech([
    can_side(720, 640, id="can", at=0),
    opener(560, 432, s=1.15, id="op", at="@drawer", squeeze="@squeeze", twist="@twist"),
    label("handles", 1040, 250, (200, -90), at="@handles"),
    label("crank", 700, 340, (-260, -120), at="@crank"),
    label("wheels", 560, 425, (-300, 60), at="@wheels"),
    it("ellipse", id="ring", x=720, y=430, rx=152, ry=38, fill="none", stroke="yellow", sw=10, glow="yellow",
       **{"in": "@ring"}, keys=[{"at": "@ring", "y": 330, "rotate": -14, "dur": 1.0, "ease": "back"}]),
], camera=[{"at": "@squeeze", "x": 800, "y": 520, "zoom": 1.12, "dur": 1.5}]), {"sfx": [{"id": "tick", "at": "twist"}]})
scene("s011", 3, mech([
    can_side(820, 660, id="can"),
    opener(660, 452, s=1.15, id="op", glow_wheel="@slice"),
    text("?", 1360, 420, 260, at="@question", fill="yellow"),
], camera=[{"at": "@slice", "x": 700, "y": 470, "zoom": 1.6, "dur": 1.6}]))
scene("s014", 4, mech([
    grp(lever_bar(-300, 0, length=600, pivot_at=0.7, id="i1"), x=300, y=430, scale=0.7, **{"in": "@three"},
        keys=[{"at": "@folded", "x": 760, "y": 520, "scale": 0.3, "opacity": 0, "dur": 0.8}]),
    grp([it("poly", points=[[0, -150], [-90, 120], [90, 120]], fill="sky")], x=960, y=430, **{"in": "@oldest"},
        keys=[{"at": "@folded", "y": 520, "scale": 0.3, "opacity": 0, "dur": 0.8}]),
    grp([it("circle", r=120, fill="none", stroke="teal", sw=14), it("circle", r=30, fill="teal"),
         it("rect", w=130, h=26, r=13, ax=0, fill="teal")], x=1560, y=430, spin={"speed": 120, "from": "@machines"},
        **{"in": "@machines"}, keys=[{"at": "@folded", "x": 1160, "y": 520, "scale": 0.3, "opacity": 0, "dur": 0.8}]),
    opener(840, 560, s=1.3, id="op", at="@fist"),
    can_side(1500, 640, w=260, h=320, id="can", at="@can"),
]))

# 3 · Cans that fought back
scene("s018", 2, mech([
    it("line", x=960, y=300, to=[0, 520], stroke="steel2", sw=14, **{"in": 0}),
    it("poly", x=960, y=820, points=[[0, 0], [-80, 120], [80, 120]], fill="steel2", **{"in": 0}),
    grp([it("line", x=-420, y=0, to=[840, 0], stroke="steel", sw=16),
         grp([it("line", to=[0, 120], stroke="steel2", sw=5), it("rect", y=170, w=200, h=100, r=12, fill="dark"),
              can_side(0, 105, w=150, h=170, id="ironcan", band="dark", ridges=False)], x=-380),
         grp([it("line", to=[0, 120], stroke="steel2", sw=5), it("rect", y=170, w=200, h=100, r=12, fill="dark"),
              it("ellipse", y=190, rx=60, ry=40, fill="food")], x=380)],
        id="beam", x=960, y=300, **{"in": 0}, keys=[{"at": "@weighed", "rotate": -12, "dur": 1.2, "ease": "back"}]),
    text("wrought iron", 560, 960, 56, at="@wrought", fill="muted"),
    text("food", 1360, 960, 56, at="@food", fill="muted"),
]))
scene("s020", 1, gemini("A soldier of the early 1800s in a plain blue coat sitting on a crate at a field camp, frowning "
                        "as he pries open a heavy dark iron food tin with a long bayonet, other tins stacked beside him"))
scene("s021", 3, mech([
    it("rect", id="wall", x=960, y=560, w=300, h=420, fill="dark", keys=[{"at": "@thinner", "w": 40, "fill": "steel", "dur": 2.0}]),
    text("can wall", 960, 860, 56, at=0, fill="muted"),
    arrow(620, 560, (230, 0), color="sky", at="@thinner"),
    arrow(1300, 560, (-230, 0), color="sky", at="@thinner"),
    opener(1500, 420, s=0.8, id="op", at="@openers"),
]))
scene("s024", 3, mech([
    it("line", x=200, y=620, to=[1520, 0], stroke="muted", sw=8, **{"in": 0}),
    it("circle", x=600, y=620, r=26, fill="coral", **{"in": "@yeates"}),
    text("1855", 600, 540, 76, at="@fifty"),
    text("Yeates · England", 600, 730, 50, at="@england", fill="muted"),
    it("circle", x=1320, y=620, r=26, fill="teal", **{"in": "@warner"}),
    text("1858", 1320, 540, 76, at="@later"),
    text("Warner · Connecticut", 1320, 730, 50, at="@connecticut", fill="muted"),
]))
scene("s027", 3, mech([
    can_side(700, 700, w=520, h=360, id="can", ridges=False),
    grp([it("path", d="M0 0 L380 -120", stroke="steel", sw=34),
         it("path", d="M0 0 Q-60 50 -20 120", stroke="steel2", sw=18, id="blade"),
         it("rect", x=60, y=-10, w=110, h=26, r=10, fill="coral", rotate=-18, id="guard")],
        id="warner", x=600, y=520, rotate=-6, **{"in": "@warner"},
        keys=[{"at": "@saw", "rotate": 6, "dur": 0.4}, {"at": "@saw+0.45", "rotate": -6, "dur": 0.4}, {"at": "@saw+0.9", "rotate": 4, "dur": 0.4}]),
    label("point", 590, 640, (-280, 40), at="@point"),
    label("curved blade", 610, 560, (-360, -160), at="@curved"),
    label("guard", 720, 480, (260, -170), at="@guard"),
]))
scene("s030", 1, gemini("An 1860s Civil War army camp beside a campfire, a cook in a blue Union uniform kneeling and "
                        "levering open a food tin with a curved, sickle-shaped hand tool, canvas tents behind him"))
scene("s031", 1, gemini("A Victorian family kitchen, a housewife in a long dress and apron holding a curved, "
                        "sickle-shaped can-opening tool at arm's length with an alarmed face, a small child peeking "
                        "around the doorway"))
scene("s032", 4, mech([
    can_side(1180, 640, w=300, h=360, id="can", band="teal"),
    grp([it("path", d="M-130 -40 Q-200 -140 -150 -200", stroke="cream", sw=22),
         it("path", d="M130 -40 Q200 -140 150 -200", stroke="cream", sw=22),
         it("ellipse", rx=140, ry=110, fill="coral"),
         it("circle", x=-50, y=-20, r=12, fill="line", sw=0), it("circle", x=50, y=-20, r=12, fill="line", sw=0),
         it("ellipse", y=55, rx=70, ry=40, fill="pink"),
         it("rect", x=150, y=20, w=260, h=30, r=12, ax=0, fill="steel")],
        id="bull", x=620, y=520, **{"in": "@bull"}, keys=[{"at": "@packed", "x": 760, "dur": 0.8}]),
    text("cast iron", 620, 840, 56, at="@cast", fill="muted"),
]))
scene("s036", 4, mech([
    grp([it("rect", w=760, h=440, r=90, fill="steel"), it("rect", w=700, h=380, r=70, fill="steel2", sw=4)],
        id="tin", x=960, y=600, **{"in": 0}),
    it("rect", id="strip", x=600, y=600, w=720, h=60, r=20, ax=0, fill="yellow", sx=0.02, **{"in": "@soldered"},
       keys=[{"at": "@peeled", "sx": 1, "dur": 2.2, "ease": "linear"}]),
    grp([it("rect", w=50, h=240, r=20, fill="gold"), it("ellipse", y=-150, rx=60, ry=40, fill="gold"),
         it("rect", y=-6, w=12, h=200, fill="dark", sw=0)],
        id="key", x=600, y=600, **{"in": "@key"}, spin={"speed": 220, "from": "@peeled"},
        keys=[{"at": "@peeled", "x": 1320, "dur": 2.2, "ease": "linear"}]),
    label("still used on some fish tins", 1330, 380, (-120, -150), at="@fish"),
]))
scene("s040", 3, mech([
    it("rect", id="wall", x=760, y=560, w=220, h=380, fill="dark", keys=[{"at": "@slim", "w": 36, "fill": "steel", "dur": 1.4}]),
    opener(1240, 520, s=0.9, id="op", at="@slim+0.8"),
    text("tool", 1240, 830, 60, at="@tool", fill="muted"),
    text("problem", 760, 830, 60, at="@problem", fill="muted"),
]))

# 4 · Machine one: the squeeze
scene("s043", 4, mech([
    can_side(720, 680, id="can"),
    opener(560, 472, s=1.15, id="op", squeeze="@close", glow_handles="@handles"),
    arrow(1300, 120, (-110, 150), color="coral", at="@close"),
    arrow(560, 300, (0, 120), color="yellow", at="@clamp"),
    label("lever", 1040, 250, (240, -60), at="@lever"),
], camera=[{"at": "@clamp", "x": 700, "y": 480, "zoom": 1.3, "dur": 1.4}]))
scene("s047", 4, mech([
    *lever_bar(360, 560, id="lev", tilt=("@trades", -8)),
    arrow(400, 260, (0, 260), color="coral", at="@force#2"),
    arrow(1218, 760, (0, -150), color="yellow", at="@out"),
    formula("advantage = force out ÷ force in", 960, 920, 64, at="@divided"),
]))
scene("s051", 3, mech([
    *lever_bar(360, 560, id="lev"),
    it("line", x=380, y=470, to=[858, 0], stroke="coral", sw=8, **{"in": "@push"}),
    text("distance to your push", 800, 430, 48, at="@push", fill="coral"),
    it("line", x=1238, y=470, to=[200, 0], stroke="yellow", sw=8, **{"in": "@work"}),
    text("to the work", 1340, 430, 48, at="@work", fill="yellow"),
    formula("advantage = long ÷ short", 960, 900, 64, at="@ratio"),
]))
scene("s054", 4, mech([
    *lever_bar(300, 700, length=1300, pivot_at=0.62, id="saw", tilt=("@lift", -9)),
    grp([person(0, 0, s=1.0, id="kid")], id="kidg", x=380, y=683, **{"in": "@child"},
        keys=[{"at": "@lift", "y": 815, "dur": 0.9, "ease": "back"}]),
    grp([it("rect", w=220, h=170, r=40, fill="gold"), it("rect", y=-95, w=80, h=30, r=12, fill="dark")],
        id="bag", x=1270, y=600, **{"in": "@bag"}, keys=[{"at": "@lift", "y": 560, "dur": 0.9, "ease": "back"}]),
    text("distance does the lifting", 960, 220, 64, at="@distance"),
]))
scene("s058", 3, mech([
    can_side(720, 680, id="can"),
    opener(560, 472, s=1.15, id="op"),
    it("line", x=560, y=470, to=[560, -330], stroke="coral", sw=8, dash=[18, 14], **{"in": "@fingers"}),
    it("line", x=560, y=470, to=[14, -14], stroke="yellow", sw=12, **{"in": "@wheels"}),
    text("×5", 1180, 200, 110, at="@five", fill="coral", example=True),
    text("example", 1180, 290, 44, at="@five", fill="muted"),
]))
scene("s061", 3, mech([
    can_side(720, 680, id="can"),
    opener(560, 472, s=1.15, id="op", squeeze="@grip"),
    arrow(1130, 60, (0, 90), color="coral", at="@pound", sw=8),
    text("1 lb", 1240, 120, 64, at="@pound", example=True),
    arrow(560, 120, (0, 250), color="yellow", at="@five", sw=24),
    text("5 lb", 380, 260, 90, at="@five", example=True),
    text("example", 960, 1010, 44, at="@five", fill="muted"),
]))
scene("s064", 2, mech([
    can_side(820, 660, id="can"),
    opener(660, 452, s=1.15, id="op", squeeze=0),
    text("?", 1340, 420, 260, at="@cutting", fill="yellow"),
]))

# 5 · Machine two: the edge
scene("s066", 3, mech([
    *rim_section(),
    cutting_wheel(at=0, glow="yellow"),
    label("bevelled edge", 1230, 575, (-260, -230), at="@bevelled"),
    it("circle", id="spot", x=1230, y=587, r=12, fill="yellow", glow="yellow", **{"in": "@sliver"}, pulse={"amount": 0.4, "period": 0.8, "from": "@sliver"}),
], camera=[{"at": "@sliver", "x": 1180, "y": 560, "zoom": 1.5, "dur": 1.4}]))
scene("s069", 4, mech([
    it("rect", id="block", x=760, y=640, w=420, h=160, r=12, fill="sky", keys=[{"at": "@shrink", "w": 60, "dur": 1.2}]),
    it("rect", id="floor", x=960, y=740, w=1100, h=40, fill="steel2"),
    arrow(760, 340, (0, 200), color="coral", at="@force"),
    formula("pressure = force ÷ area", 960, 200, 70, at="@divided"),
    it("gauge", id="g", x=1460, y=480, r=150, value=0.15, **{"in": "@pressure"}, keys=[{"at": "@climbs", "value": 0.92, "dur": 1.2}]),
]))
scene("s073", 2, mech([
    it("rect", x=960, y=780, w=1500, h=120, fill="pink"),
    text("skin", 300, 800, 50, fill="line", outline=False, at=0),
    grp([it("poly", points=[[0, 0], [-10, -300], [10, -300]], fill="steel")], id="needle", x=620, y=690,
        **{"in": "@needle"}, keys=[{"at": "@breaks", "y": 790, "dur": 0.5, "ease": "in"}]),
    arrow(620, 220, (0, 120), color="coral", at="@needle"),
    grp([it("rect", w=160, h=320, r=80, fill="cream")], id="finger", x=1300, y=560, **{"in": "@fingertip"},
        keys=[{"at": "@hard", "y": 575, "dur": 0.4}]),
    arrow(1300, 220, (0, 120), color="coral", at="@fingertip"),
    text("same push", 960, 140, 60, at="@pressing"),
]))
scene("s075", 5, mech([
    it("circle", id="tip", x=560, y=560, r=200, fill="cream", **{"in": "@fingertip"}),
    it("circle", id="edge", x=1360, y=560, r=20, fill="yellow", glow="yellow", **{"in": "@patch"}),
    text("fingertip", 560, 860, 56, at="@fingertip", fill="muted"),
    text("wheel edge", 1360, 860, 56, at="@patch", fill="muted"),
    text("×100 pressure", 960, 230, 96, at="@hundred#2", fill="yellow", example=True),
    text("example", 960, 320, 44, at="@hundred#2", fill="muted"),
]))
scene("s080", 3, mech([
    it("rect", id="strip", x=960, y=560, w=900, h=70, r=10, fill="steel"),
    arrow(420, 560, (-200, 0), color="coral", at="@stress"),
    arrow(1500, 560, (200, 0), color="coral", at="@stress"),
    formula("stress = force ÷ area", 960, 820, 70, at="@stress"),
    text("inside a solid", 960, 340, 56, at="@solid", fill="muted"),
]))
scene("s083", 3, mech([
    grp([it("rect", w=400, h=56, r=8, fill="steel", ax=1)], id="left", x=960, y=560, pivot=[0, 0],
        keys=[{"at": "@springs", "rotate": 10, "dur": 0.35}, {"at": "@springs+0.4", "rotate": 0, "dur": 0.5, "ease": "elastic"},
              {"at": "@bends", "rotate": 18, "dur": 0.6}, {"at": "@fractures", "rotate": 34, "x": 900, "y": 600, "dur": 0.4, "ease": "out"}]),
    grp([it("rect", w=400, h=56, r=8, fill="steel", ax=0)], id="right", x=960, y=560,
        keys=[{"at": "@springs", "rotate": -10, "dur": 0.35}, {"at": "@springs+0.4", "rotate": 0, "dur": 0.5, "ease": "elastic"},
              {"at": "@bends", "rotate": -18, "dur": 0.6}, {"at": "@fractures", "rotate": -34, "x": 1020, "y": 600, "dur": 0.4, "ease": "out"}]),
    arrow(960, 300, (0, 180), color="coral", at="@push"),
    text("springs back", 520, 860, 52, at="@springs", fill="teal"),
    text("bends for good", 960, 860, 52, at="@bends", fill="yellow"),
    text("fractures", 1400, 860, 52, at="@fractures", fill="coral"),
], drift=0))
scene("s086", 3, mech([
    lid_top(960, 560, r=380, id="lid", at=0),
    it("path", id="cut", x=960, y=560, d=arc_path(330, -90, 40), stroke="yellow", sw=8, glow="yellow", **{"in": {"at": "@hairline", "fx": "draw", "dur": 1.6}}),
    label("hairline", 1215, 350, (220, -120), at="@hairline+0.6"),
    text("the rest of the lid: untouched", 960, 1000, 50, at="@never", fill="muted"),
]))
scene("s089", 3, mech([
    grp([it("rect", w=1400, h=40, fill="steel")], id="sheet", x=960, y=560, **{"in": 0}),
    grp([it("rect", y=-120, w=60, h=200, r=10, fill="coral"), it("rect", y=120, w=60, h=200, r=10, fill="coral")],
        id="caliper", x=960, y=560, **{"in": "@roll"}),
    text("0.20 – 0.35 mm", 960, 860, 96, at="@millimetre", fill="yellow"),
    text("food-can steel", 960, 250, 56, at="@steelmakers", fill="muted"),
], camera=[{"at": "@steelmakers", "zoom": 1.25, "dur": 2}]))
scene("s092", 3, mech([
    grp([it("rect", x=-20, w=600, h=40, fill="steel", ax=1)], id="left", x=960, y=640,
        keys=[{"at": "@apart", "x": 900, "rotate": 6, "dur": 0.8}]),
    grp([it("rect", x=20, w=600, h=40, fill="steel", ax=0)], id="right", x=960, y=640,
        keys=[{"at": "@apart", "x": 1020, "rotate": -6, "dur": 0.8}]),
    grp([it("poly", points=[[0, 40], [-70, -200], [70, -200]], fill="yellow")], id="wedge", x=960, y=420,
        **{"in": "@wedge"}, keys=[{"at": "@apart", "y": 600, "dur": 0.8}]),
    arrow(880, 760, (-220, 0), color="sky", at="@apart"),
    arrow(1040, 760, (220, 0), color="sky", at="@apart"),
    text("wedge", 960, 180, 64, at="@wedge"),
]))
scene("s095", 3, mech([
    lid_top(960, 560, r=380, id="lid", at=0),
    it("circle", id="dent", x=960, y=210, r=14, fill="yellow", glow="yellow", **{"in": "@dent"}),
    it("path", id="route", x=960, y=560, d=arc_path(350), stroke="yellow", sw=6, dash=[20, 18], **{"in": {"at": "@around", "fx": "fade"}}),
    text("?", 1560, 420, 220, at="@turning", fill="yellow"),
]))

# 6 · Machine three: the turning
scene("s098", 3, mech([
    it("circle", id="path", x=960, y=560, r=320, fill="none", stroke="muted", sw=6, dash=[18, 16], **{"in": "@crank"}),
    it("circle", id="shaft", x=960, y=560, r=40, fill="teal", **{"in": "@crank"}),
    grp([it("rect", w=320, h=40, r=20, ax=0, fill="yellow"), it("circle", x=320, r=46, fill="coral")], id="arm",
        x=960, y=560, **{"in": "@crank"}, spin={"speed": 120, "from": "@round"}),
    label("a lever too", 1280, 560, (160, -260), at="@lever"),
]))
scene("s101", 3, mech([
    it("circle", id="big", x=960, y=560, r=320, fill="none", stroke="coral", sw=10, **{"in": {"at": "@wide", "fx": "pop"}}, glow="coral"),
    it("circle", id="small", x=960, y=560, r=40, fill="teal", glow="teal", **{"in": "@tiny"}),
    grp([it("rect", w=320, h=40, r=20, ax=0, fill="yellow"), it("circle", x=320, r=46, fill="coral")], id="arm",
        x=960, y=560, **{"in": 0}, spin={"speed": 120, "from": 0}),
    text("your twist ×", 960, 990, 64, at="@multiplies"),
]))
scene("s104", 4, mech([
    it("line", x=960, y=560, to=[320, 0], stroke="coral", sw=10, **{"in": "@knob"}),
    it("line", x=960, y=600, to=[54, 0], stroke="teal", sw=10, **{"in": "@shaft"}),
    text("×6", 1300, 430, 120, at="@six", fill="coral", example=True),
    text("example", 1300, 520, 44, at="@six", fill="muted"),
    arrow(1280, 820, (0, -90), color="coral", at="@sixth", sw=8),
    arrow(990, 940, (0, -360), color="teal", at="@delivers", sw=20),
    it("circle", x=960, y=560, r=40, fill="teal", **{"in": 0}),
    it("circle", x=1280, y=560, r=46, fill="coral", **{"in": 0}),
]))
scene("s108", 4, mech([
    *rim_section(),
    cutting_wheel(at=0),
    feed_wheel(at="@second", spin={"speed": -110, "from": "@drives"}, glow="yellow"),
    label("small teeth", 1395, 640, (-560, 160), at="@teeth"),
    arrow(1300, 520, (-300, 0), color="sky", at="@drag", bend=-30),
    text("the can walks itself", 1150, 300, 64, at="@walks"),
], camera=[{"at": "@second", "x": 1260, "y": 640, "zoom": 1.3, "dur": 1.4}]))
scene("s112", 2, mech([
    grp([lid_top(0, 0, r=380, id="lid"), it("circle", x=0, y=-360, r=10, fill="steel2")], id="can", x=900, y=560,
        spin={"speed": -40, "from": 0}),
    it("path", id="cut", x=900, y=560, d=arc_path(340, -60, 10), stroke="yellow", sw=8, glow="yellow",
       **{"in": {"at": "@rolls", "fx": "draw", "dur": 2.5}}),
    grp([it("circle", r=70, fill="steel"), it("circle", r=22, fill="dark")], id="wheel", x=1240, y=560,
        spin={"speed": 160, "from": 0}, **{"in": 0}),
    label("cutting wheel", 1240, 560, (140, -260), at="@cutting"),
]))
scene("s114", 5, mech([
    it("gear", id="g1", x=860, y=430, r=150, teeth=20, depth=22, fill="steel", **{"in": "@gears"}, spin={"speed": 70, "from": "@opposite"}),
    it("gear", id="g2", x=860 + 150 + 130 - 22, y=430, r=150, teeth=20, depth=22, rotate=9, fill="yellow",
       **{"in": "@gears"}, spin={"speed": -70, "from": "@opposite"}),
    it("rect", id="rimstrip", x=960, y=760, w=1700, h=40, fill="steel2", **{"in": "@pinch"}),
    arrow(1400, 700, (-500, 0), color="sky", at="@pulling"),
    text("opposite directions", 960, 950, 60, at="@opposite"),
]))
scene("s119", 2, mech([
    feed_wheel(960, 540, r=260, id="fw", at=0, spin={"speed": 30, "from": 0}, glow="yellow"),
    text("feed wheel", 960, 940, 72, at="@toothed"),
]))
scene("s121", 5, mech([
    lid_top(960, 560, r=400, id="lid", at=0),
    it("circle", id="spike", x=960, y=560, r=26, fill="coral", glow="coral", **{"in": "@spike"}),
    grp([it("rect", w=360, h=34, r=17, ax=0, fill="coral"), it("circle", x=360, r=40, fill="steel")], id="arm",
        x=960, y=560, **{"in": "@cutting"}, spin={"speed": 90, "from": "@swing"}),
    text("1870 · Lyman", 960, 110, 64, at="@seventy"),
]))
scene("s126", 5, mech([
    lid_top(800, 560, r=330, id="lid", at=0),
    it("circle", id="spike", x=800, y=560, r=26, fill="coral", **{"in": 0}, out="@spike"),
    feed_wheel(800 + 360, 560, r=70, id="fw", at="@serrated", spin={"speed": -120, "from": "@serrated"}, glow="yellow"),
    it("circle", id="track", x=800, y=560, r=330, fill="none", stroke="yellow", sw=10, glow="yellow", **{"in": "@track"}),
    text("1925 · feed wheel", 800, 110, 64, at="@twenty"),
    lid_top(1560, 400, r=110, id="small", at="@size"),
    lid_top(1560, 760, r=170, id="big", at="@size+0.3"),
]))

# 7 · Today's opener
scene("s131", 3, gemini("A bright 1930s American kitchen, a woman in a patterned apron at the counter opening a food "
                        "tin with a hand-held pliers-style can opener, turning its butterfly key, morning light from a "
                        "window, simple period cabinets"))
scene("s134", 3, mech([
    can_side(720, 680, id="can"),
    opener(560, 472, s=1.15, id="op", squeeze="@grip", twist="@turn"),
    label("grip", 1040, 260, (220, -60), at="@grip"),
    label("turn", 700, 380, (-300, -150), at="@turn"),
    label("geared wheels", 560, 470, (-330, 90), at="@geared"),
]))
scene("s137", 3, gemini("A cheerful 1950s American kitchen counter with a new white electric can opener next to a "
                        "toaster, a family of three looking at the gadget with curious smiles, pastel cabinets"))
scene("s140", 2, mech([
    grp([it("rect", w=420, h=560, r=60, fill="cream"), it("rect", y=-120, w=300, h=160, r=30, fill="sky")],
        id="body", x=960, y=560, **{"in": 0}),
    cutting_wheel(960, 520, r=60, id="cw", at=0, spin={"speed": 200, "from": "@cutting"}, glow="yellow"),
    label("motor", 960, 700, (300, 120), at="@motor"),
]))
scene("s142", 4, mech([
    it("rect", x=380, y=520, w=900, h=26, ax=0, fill="steel"),
    it("rect", x=1352, y=780, w=26, h=440, fill="steel"),
    it("rect", id="seam", x=1352, y=520, w=110, h=90, r=36, fill="steel2"),
    grp([it("circle", r=90, fill="steel"), it("circle", r=24, fill="dark")], id="side", x=1560, y=500,
        **{"in": "@side"}, spin={"speed": 140, "from": "@split"}),
    it("circle", id="roller", x=1560, y=700, r=60, fill="teal", **{"in": "@roller"}, spin={"speed": -140, "from": "@split"}),
    it("line", x=1400, y=500, to=[0, 40], stroke="yellow", sw=8, glow="yellow", **{"in": "@split"}),
    label("seam", 1352, 520, (-330, -230), at="@seam"),
], camera=[{"at": "@side", "x": 1300, "y": 560, "zoom": 1.2, "dur": 1.4}]))
scene("s146", 4, mech([
    can_side(960, 700, w=420, h=360, id="can"),
    it("ellipse", id="lid", x=960, y=520, rx=210, ry=55, fill="steel", sw=6,
       keys=[{"at": "@smooth", "y": 330, "dur": 0.9, "ease": "back"}, {"at": "@rest", "y": 515, "dur": 0.8, "ease": "bounce"}]),
    it("particles", id="air", x=960, y=470, w=360, h=80, count=12, size=10, mode="steam", color="sky", **{"in": "@seal"}),
    label("smooth edge", 1170, 520, (220, -120), at="@smooth"),
    text("safer edge", 960, 980, 64, at="@safer", fill="teal"),
]))

# 8 · Three machines, one hand
scene("s150", 4, mech([
    grp(lever_bar(-300, 0, length=600, pivot_at=0.7, id="i1"), x=420, y=520, scale=0.7, **{"in": "@lever"}),
    grp([it("poly", points=[[0, -150], [-90, 120], [90, 120]], fill="sky"), it("circle", y=-150, r=14, fill="yellow", glow="yellow")],
        x=960, y=520, **{"in": "@pressure"}),
    text("lever", 420, 820, 60, at="@lever"),
    text("pressure", 960, 820, 60, at="@pressure"),
]))
scene("s154", 3, mech([
    grp(lever_bar(-300, 0, length=600, pivot_at=0.7, id="i1"), x=420, y=520, scale=0.7),
    grp([it("poly", points=[[0, -150], [-90, 120], [90, 120]], fill="sky")], x=960, y=520),
    it("gear", id="g", x=1500, y=500, r=150, teeth=18, depth=22, fill="yellow", **{"in": "@crank"}, spin={"speed": 90, "from": "@marched"}),
    text("turning", 1500, 820, 60, at="@crank"),
    it("rect", id="wall", x=960, y=980, w=600, h=20, fill="steel", **{"in": "@thin"}),
]))
scene("s157", 3, mech([
    can_side(960, 600, w=380, h=460, id="can", at=0, shake={"at": "@crumple", "amount": 10}),
    arrow(560, 600, (180, 0), color="coral", at="@crumple"),
    arrow(1360, 600, (-180, 0), color="coral", at="@crumple"),
    text("?", 960, 230, 200, at="@puzzle", fill="yellow"),
]))
scene("s160", 2, mech([
    can_side(960, 600, w=420, h=520, id="can", at=0, glow_ridges="@rings"),
    label("next: the rings", 1170, 380, (230, -160), at="@rings+0.4"),
], camera=[{"at": "@sides", "zoom": 1.15, "dur": 2}]))


def build(shot_ids: list[str]) -> dict:
    plan: dict = {}
    order = {sid: i for i, sid in enumerate(shot_ids)}
    covered = set()
    for head, n, visual, sound in SCENES:
        i = order[head]
        entry: dict = {"visual": visual}
        if sound:
            entry["sound"] = sound
        plan[head] = entry
        covered.add(head)
        for sid in shot_ids[i + 1:i + n]:
            plan[sid] = {"visual": {"same": True}}
            covered.add(sid)
    missing = [s for s in shot_ids if s not in covered]
    if missing:
        raise SystemExit(f"plansız shot: {missing}")
    return plan


if __name__ == "__main__":
    sb = yaml.safe_load(open("storyboard.yaml", encoding="utf-8"))
    ids = [s["id"] for s in sb["shots"]]
    yaml.safe_dump(build(ids), sys.stdout, sort_keys=False, allow_unicode=True, width=140)


# ------------------------------------------------------------------ thumbnails (code-drawn, words printed by the factory)
def thumbnails() -> list[dict]:
    rim = [
        it("rect", x=200, y=700, w=1250, h=40, ax=0, fill="steel"),
        it("rect", x=1500, y=980, w=40, h=520, fill="steel"),
        it("rect", x=1500, y=700, w=170, h=140, r=50, fill="steel2"),
        grp([it("circle", r=230, fill="steel"), it("circle", r=165, fill="steel2", sw=5), it("circle", r=46, fill="dark")],
            x=1290, y=455, glow="yellow"),
        it("gear", x=1530, y=930, r=150, teeth=24, depth=26, hole=30, fill="yellow"),
        it("line", x=1290, y=682, to=[0, 40], stroke="yellow", sw=12, glow="yellow"),
    ]
    big_opener = [can_side(1480, 800, w=480, h=520, id="can"),
                  opener(1260, 545, s=1.45, id="op", glow_wheel=0)]
    lid_lift = [can_side(1340, 720, w=560, h=560, id="can", band="teal"),
                it("ellipse", x=1340, y=330, rx=250, ry=64, fill="steel", rotate=-12, glow="yellow"),
                it("ellipse", x=1340, y=330, rx=210, ry=48, fill="steel2", rotate=-12, sw=4)]
    return [
        {"kind": "scene", "visual": mech(rim, drift=0), "text": {"en": "NOT A BLADE"}, "pos": "top-left"},
        {"kind": "correction", "visual": mech(big_opener, drift=0), "myth": {"en": "JUST A BLADE"},
         "note": {"en": "IT'S PRESSURE"}, "pos": "top-left", "claim": "c17"},
        {"kind": "stamp", "visual": mech(lid_lift, drift=0), "pos": "top-left"},
    ]
