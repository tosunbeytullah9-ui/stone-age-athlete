"""Full-frame backgrounds. Each returns (fill colour, svg body, ground_y).
Modern scenes use cool grey-blue, ancient scenes warm earth tones — the viewer
always knows which era they are in."""
from __future__ import annotations

from .props import PROPS
from .style import INK, W, c, line, path, rect

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


@bg("gym")
def gym(clock=None, rack=True, **_):
    g = 830
    body = _floor(g, c("floor_cool"))
    if rack:
        body += PROPS["dumbbell_rack"](1500, g, 1.0)
    if clock:
        body += PROPS["clock"](1560, 250, 1.0, time=clock)
    return "wall_cool", body, g


@bg("living_room")
def living_room(night=False, clock=None, **_):
    g = 860
    body = _floor(g, "#8e9ca7") + PROPS["window"](335, 300, 1.0, night=night)
    if clock:
        body += PROPS["clock"](1560, 230, 1.0, time=clock)
    return "#c3ccd3", body, g


@bg("office")
def office(clock=None, **_):
    g = 860
    body = _floor(g, "#8e9ca7") + PROPS["window"](1550, 300, 1.0)
    if clock:
        body += PROPS["clock"](330, 230, 1.0, time=clock)
    return "#c9d1d6", body, g


@bg("savanna")
def savanna(sun="low", hut=False, trees=True, **_):
    g = 770
    body = ""
    if sun:
        body += PROPS["sun"](1600, 200 if sun == "low" else 130, 1.0)
    body += path("M0,640 C300,560 520,600 760,620 C1050,560 1350,590 1920,560 L1920,780 L0,780 Z", fill="olive", w=7)
    body += _floor(g, c("sand"))
    if trees:
        body += PROPS["acacia"](1700, g, 0.9)
    if hut:
        body += PROPS["hut"](330, g, 1.0)
    return "sky_warm", body, g


@bg("forest")
def forest(**_):
    g = 800
    body = _floor(g, "#9c8a5a")
    for x, s in ((150, 1.1), (520, 0.9), (1450, 1.0), (1800, 1.15)):
        body += PROPS["tree"](x, g, s)
    return "#dfe3c0", body, g


@bg("cave")
def cave(fire=True, **_):
    g = 850
    body = path("M0,0 L1920,0 L1920,1080 L0,1080 Z M160,1080 Q140,300 960,180 Q1780,300 1760,1080 Z",
                fill="#3e3026", w=0, extra=' fill-rule="evenodd"')
    body += path("M160,1080 Q140,300 960,180 Q1780,300 1760,1080", w=9)
    body += _floor(g, "#7a6450")
    if fire:
        body += PROPS["campfire"](960, g, 1.0)
    return "#a88a68", body, g


@bg("night_camp")
def night_camp(fire=True, **_):
    g = 800
    body = PROPS["stars"](0, 0, 1.0) + PROPS["moon"](1600, 170, 1.0)
    body += path("M0,700 C400,620 800,660 1200,640 C1500,620 1700,650 1920,630 L1920,810 L0,810 Z", fill="#2f3b2c", w=7)
    body += _floor(g, "#5a4a3a")
    if fire:
        body += PROPS["campfire"](960, g, 1.0)
    return "#26314d", body, g


@bg("classroom")
def classroom(**_):
    g = 880
    body = _floor(g, "#c9ad85") + PROPS["board"](1240, 485, 1.0)
    body += line([(900, 830), (880, 880)], 10) + line([(1580, 830), (1600, 880)], 10)
    return "#ecdfc6", body, g


@bg("split")
def split(**_):
    """Left half ancient (warm), right half modern (cool) — for then-vs-now shots."""
    g = 840
    body = rect(-10, -10, 970, 1100, "sky_warm", w=0) + rect(960, -10, 970, 1100, "wall_cool", w=0)
    body += rect(-10, g, 970, 300, "sand", w=0) + rect(960, g, 970, 300, "floor_cool", w=0)
    body += line([(0, g), (W, g)], 6) + line([(960, 0), (960, 1080)], 9)
    return "sky_warm", body, g


def get(name: str, **opts):
    fn = BACKGROUNDS.get(name)
    if fn is None:
        raise ValueError(f"unknown background: {name} (options: {', '.join(BACKGROUNDS)})")
    return fn(**opts)


__all__ = ["BACKGROUNDS", "get", "INK"]
