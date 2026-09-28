"""Full-frame backgrounds. Each returns (fill colour, svg body, ground_y).
Modern scenes use cool grey-blue, ancient scenes warm earth tones — the viewer
always knows which era they are in."""
from __future__ import annotations

from .props import PROPS
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


# ---------------------------------------------------------------- extended kit
def _wavy_floor(y, color, amp=14, period=240):
    d = f"M-10,{y}"
    x = -10
    i = 0
    while x < W + 10:
        d += f" q{period / 4},{-amp if i % 2 == 0 else amp} {period / 2},0"
        x += period / 2
        i += 1
    return path(d + " L1930,1090 L-10,1090 Z", fill=color, w=6)


def _hills(y, color, amp=60):
    return path(f"M0,{y} C300,{y - amp} 520,{y - amp * 0.3} 760,{y - amp * 0.6} C1050,{y - amp * 1.2} 1350,{y - amp * 0.4} "
                f"1920,{y - amp} L1920,{y + 200} L0,{y + 200} Z", fill=color, w=7)


@bg("underwater")
def underwater(surface=True, rays=True, plants=True, **_):
    """Under the sea. Surface line at y 120, seabed (floor) at 960. Put swimmers mid-water with `lift`."""
    g = 960
    body = ""
    if surface:
        body += rect(-10, -10, W + 20, 130, "#9cc4da", w=0)
        body += path("M-10,120 " + " ".join(f"q60,{-16 if i % 2 == 0 else 16} 120,0" for i in range(17)), w=6,
                     stroke=c("foam"))
    if rays:
        for x0, x1 in ((300, 180), (760, 700), (1250, 1320), (1650, 1780)):
            body += (f'<path d="M{x0 - 40},120 L{x0 + 40},120 L{x1 + 110},{g} L{x1 - 110},{g} Z" '
                     f'fill="#ffffff" opacity="0.10"/>')
    body += _wavy_floor(g, "#d9c28f")
    if plants:
        body += PROPS["seaweed"](170, g + 20, 1.0) + PROPS["coral"](420, g + 25, 0.9)
        body += PROPS["rock"](1600, g + 25, 0.8) + PROPS["seaweed"](1780, g + 20, 0.8) + PROPS["coral"](1450, g + 30, 0.6,
                                                                                                    color="#e3a447")
    return "#5f93b8", body, g


@bg("sea")
def sea(boat=False, stilts=False, island=False, sun="low", **_):
    """Open sea, horizon at y 560, water line (floor) at 760. boat: dugout at x 960 (figures in it:
    ground 735); stilts: stilt house at x 1520 (deck = ground 540); island: sand + palm on the left."""
    g = 760
    body = ""
    if sun:
        body += PROPS["sun"](1560, 220 if sun == "low" else 140, 1.0)
    body += rect(-10, 560, W + 20, 530, "sea", w=0) + line([(0, 560), (W, 560)], 6)
    for x, y in ((200, 640), (620, 610), (1100, 660), (1500, 620), (1780, 690), (380, 860), (1320, 900), (860, 980)):
        body += path(f"M{x - 60},{y} q30,-18 60,0 q30,18 60,0", w=5, stroke=c("foam"))
    if island:
        body += path("M-10,780 Q200,680 480,760 L480,800 L-10,800 Z", fill="sand", w=7)
        body += PROPS["palm"](200, 740, 0.9)
    if stilts:
        body += PROPS["stilt_house"](1520, g, 1.0)
    if boat:
        body += PROPS["boat"](960, g, 1.0, outrigger=True)
    return "sky_warm", body, g


@bg("mountain")
def mountain(flag=False, camp=False, snow=True, **_):
    """High mountains (Himalaya / Andes). Snowy slope floor at 820. flag: on the summit; camp: tent at x 1500."""
    g = 820
    body = PROPS["sun"](1680, 150, 0.8)
    body += path("M-10,640 L260,300 L420,470 L700,140 L980,520 L1180,330 L1500,600 L1700,380 L1930,560 L1930,900 L-10,900 Z",
                 fill="rock_cool", w=8)
    # snow caps
    for px, py, lft, rgt in ((260, 300, 80, 70), (700, 140, 120, 110), (1180, 330, 80, 90), (1700, 380, 70, 70)):
        body += path(f"M{px},{py} L{px - lft},{py + lft * 1.2} L{px - lft * 0.4},{py + lft * 0.9} L{px},{py + lft * 1.25} "
                     f"L{px + rgt * 0.5},{py + rgt * 0.9} L{px + rgt},{py + rgt * 1.1} Z", fill="snow", w=6)
    if flag:
        body += line([(700, 140), (700, 40)], 7) + path("M702,42 L780,62 L702,86 Z", fill="bad", w=5)
    body += path(f"M-10,{g} C400,{g - 60} 900,{g - 20} 1930,{g - 70} L1930,1090 L-10,1090 Z", fill="snow", w=7)
    if camp:
        body += PROPS["tent"](1500, g - 45, 0.8)
    return "#dfe7ea" if snow else "sky_warm", body, g


@bg("arctic")
def arctic(igloo=False, sun=True, **_):
    """Snow plain and sea ice (Inuit). Floor at 800. igloo: at x 1450."""
    g = 800
    body = ""
    if sun:
        body += PROPS["sun"](1500, 260, 0.7)
    body += path("M-10,640 L300,600 L420,625 L700,590 L760,620 L1100,600 L1300,630 L1600,595 L1930,620 L1930,810 L-10,810 Z",
                 fill="ice", w=7)
    body += _floor(g, c("snow"))
    for x, y in ((300, 900), (820, 960), (1500, 930)):
        body += path(f"M{x - 90},{y} q90,-24 180,0", w=4, stroke=c("#b9cbd6"))
    if igloo:
        body += PROPS["igloo"](1450, g, 1.0)
    return "#e6eef2", body, g


@bg("desert")
def desert(pyramids=False, sun="high", **_):
    """Sand dunes under a hot sun (Egypt, Sahara). Floor at 800. pyramids: two on the horizon."""
    g = 800
    body = ""
    if sun:
        body += PROPS["sunbeam"](1580, 170 if sun == "high" else 260, 0.8)
    if pyramids:
        body += PROPS["pyramid"](560, 650, 0.8) + PROPS["pyramid"](1060, 650, 0.55)
    body += path("M-10,650 C300,600 500,640 800,660 C1100,610 1400,640 1930,630 L1930,810 L-10,810 Z", fill="#e7c98f", w=7)
    body += _floor(g, c("#dcb57a"))
    body += path(f"M200,900 q150,-30 300,0 M1200,960 q150,-30 300,0", w=4, stroke=c("#c29a5c"))
    return "#f3dfae", body, g


@bg("shore")
def shore(reeds=True, boat=False, **_):
    """River or lake shore: water band behind (y 640-800), sandy bank floor at 800."""
    g = 800
    body = _hills(560, "olive", 40)
    body += rect(-10, 640, W + 20, 170, "sea", w=0) + line([(0, 640), (W, 640)], 6)
    for x, y in ((250, 700), (900, 690), (1450, 720), (650, 760)):
        body += path(f"M{x - 60},{y} q30,-14 60,0 q30,14 60,0", w=5, stroke=c("foam"))
    if boat:
        body += PROPS["boat"](1300, 700, 0.6)
    body += _wavy_floor(g, c("sand"), amp=8, period=400)
    if reeds:
        body += PROPS["reeds"](140, g + 10, 1.0) + PROPS["reeds"](1800, g + 10, 0.8)
    return "sky_warm", body, g


@bg("steppe")
def steppe(yurt=False, **_):
    """Endless grassland (Mongolia, Central Asia). Floor at 790. yurt: ger at x 1500."""
    g = 790
    body = PROPS["sun"](360, 190, 0.8)
    body += _hills(620, "#a9ad72", 70)
    body += _floor(g, c("grass"))
    for x in (150, 520, 980, 1350, 1750):
        body += path(f"M{x},{g + 80} l-10,-26 M{x + 12},{g + 80} l0,-30 M{x + 24},{g + 80} l10,-26", w=4, stroke=c("#6f7f3e"))
    if yurt:
        body += PROPS["yurt"](1500, g, 0.9)
    return "sky_warm", body, g


@bg("village")
def village(stilts=False, **_):
    """Traditional village. stilts: wooden stilt houses over the water (sea nomads, floor = shallow
    water at 820); otherwise thatched huts on dry ground (floor 800)."""
    if stilts:
        g = 820
        body = rect(-10, 600, W + 20, 490, "sea", w=0) + line([(0, 600), (W, 600)], 6)
        body += PROPS["stilt_house"](320, 700, 0.8) + PROPS["stilt_house"](1560, 720, 0.9)
        body += PROPS["palm"](1000, 640, 0.6)
        return "sky_warm", body, g
    g = 800
    body = _hills(600, "olive", 50) + _floor(g, c("sand"))
    body += PROPS["hut"](260, g - 60, 0.8) + PROPS["hut"](600, g - 90, 0.6) + PROPS["hut"](1650, g - 50, 0.9)
    body += PROPS["acacia"](1300, g - 100, 0.7)
    return "sky_warm", body, g


@bg("arena")
def arena(**_):
    """Roman amphitheatre / colosseum: two tiers of arches behind a sand floor at 820."""
    g = 820
    body = rect(-10, 250, W + 20, 580, "#d8c29a", w=7)
    for tier, (top, h) in enumerate(((290, 230), (540, 250))):
        for i in range(10):
            x = 40 + i * 190
            body += path(f"M{x},{top + h} L{x},{top + 70} A70,70 0 0 1 {x + 140},{top + 70} L{x + 140},{top + h} Z",
                         fill="#8a6f4f", w=6)
        body += line([(0, top + h + 12), (W, top + h + 12)], 8)
    body += rect(-10, 225, W + 20, 40, "#c9b087", w=7)
    body += _floor(g, c("#e0c48e"))
    return "sky_warm", body, g


@bg("gymnasium")
def gymnasium(**_):
    """Ancient Greek gymnasium / palaestra: colonnade and roof, sand floor at 820."""
    g = 820
    body = path("M160,250 L960,110 L1760,250 Z", fill="#e9e0cc", w=8)
    body += rect(140, 250, 1640, 50, "#e9e0cc", w=8)
    for i in range(8):
        body += PROPS["column"](230 + i * 208, g - 20, 1.18)
    body += rect(-10, g - 30, W + 20, 30, "#d8cdb5", w=6)
    body += _floor(g, c("sand"))
    return "sky_warm", body, g


@bg("dojo")
def dojo(ring=False, **_):
    """Japanese training hall: paper walls, wooden floor at 860. ring: raised clay sumo ring (dohyo)
    from x 380 to 1540; then the floor is the ring top at 800."""
    g = 860
    body = rect(-10, -10, W + 20, 120, "bark", w=7)
    for i in range(5):
        x0 = 40 + i * 380
        body += rect(x0, 160, 320, 520, "#f7f1e1", w=7)
        for k in range(1, 4):
            body += line([(x0 + k * 80, 160), (x0 + k * 80, 680)], 4)
        for k in range(1, 5):
            body += line([(x0, 160 + k * 104), (x0 + 320, 160 + k * 104)], 4)
    body += rect(-10, 680, W + 20, 30, "bark", w=7)
    body += _floor(g, c("#c49a63"))
    for x in range(0, W, 240):
        body += line([(x, g), (x - 80, 1080)], 3, color="#a57d4a")
    if ring:
        g = 800
        body += path("M300,1000 L420,800 L1500,800 L1620,1000 Z", fill="#c98f58", w=8)
        body += line([(470, 800), (1450, 800)], 16, color="#e8d9a8")
    return "#e9dcc0", body, g


@bg("track")
def track(**_):
    """Modern running track (cool era). Lanes from y 780; floor at 860."""
    g = 860
    body = rect(-10, 520, W + 20, 200, "#b3c0c8", w=7)
    for i in range(14):
        for r in range(3):
            body += circle(80 + i * 135 + (r % 2) * 40, 560 + r * 55, 18, fill="#8a9aa5", w=4)
    body += rect(-10, 720, W + 20, 60, "grass", w=6)
    body += rect(-10, 780, W + 20, 310, "track", w=6)
    for y in (840, 910, 990):
        body += line([(0, y), (W, y)], 5, color="#f3f3f3")
    return "wall_cool", body, g


@bg("lab")
def lab(**_):
    """Modern science lab: bench with glassware along the back wall. Floor at 860."""
    g = 860
    body = _floor(g, "#8e9ca7")
    body += rect(160, 520, 1600, 40, "#e8eef2", w=7) + rect(180, 560, 1560, 300, "furniture", w=7)
    for i in range(1, 6):
        body += line([(180 + i * 260, 560), (180 + i * 260, 860)], 5)
    body += PROPS["microscope"](420, 520, 0.8)
    for x, col, h in ((820, "#8fd18a", 110), (930, "#f08a8a", 80), (1030, "#8ab8f0", 130)):
        body += path(f"M{x - 18},{520 - h} L{x - 18},{520 - 55} L{x - 55},520 L{x + 55},520 L{x + 18},{520 - 55} "
                     f"L{x + 18},{520 - h} Z", fill=col, w=6)
    body += rect(1300, 300, 360, 200, "screen", w=7) + path("M1330,460 L1400,400 L1460,430 L1530,340 L1620,380", w=7,
                                                            stroke=c("bad"))
    return "#d3dde3", body, g


def get(name: str, **opts):
    fn = BACKGROUNDS.get(name)
    if fn is None:
        raise ValueError(f"unknown background: {name} (options: {', '.join(BACKGROUNDS)})")
    return fn(**opts)


__all__ = ["BACKGROUNDS", "get", "INK"]
