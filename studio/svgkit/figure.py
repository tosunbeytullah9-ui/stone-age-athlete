"""Stick figures built from poses. A pose is a set of joint positions relative to the hip (0,0),
y grows downward, a standing figure's feet are at y=180 and head centre at y=-222.

Figure spec (all optional except pose):
  pose: stand | walk | run | overhead_lift | sit | sit_slouch | kneel_grind | kneel | point | carry |
        squat_rest | throw | lie | wave | celebrate | think | bend_dig | climb | tired_bent
  x: hip x (0-1920)            ground: y of the floor under the feet (default from background)
  scale: 1.0                   flip: false (true = faces left)
  face: neutral | smile | strain | tired | surprised | sad | focused | sleep
  look: -10..10 (eye shift)    wear: [headband, whistle, hair_bun, hide, beard, cap]
  hold: barbell | dumbbell | phone | spear | pointer | rock | log | stick | torch | bowl | none
  sweat: true | false
"""
from __future__ import annotations

from .style import INK, RED, c, circle, line, path, rect

HEAD_R = 44
SH = (0, -150)  # default shoulder

POSES: dict[str, dict] = {
    "stand": dict(neck=(0, -170), head=(0, -222), sh=SH,
                  le=(-40, -75), lh=(-52, 5), re=(40, -75), rh=(52, 5),
                  lk=(-30, 90), lf=(-45, 180), rk=(30, 90), rf=(45, 180)),
    "walk": dict(neck=(8, -170), head=(12, -222), sh=(6, -150),
                 le=(40, -80), lh=(62, -12), re=(-32, -80), rh=(-60, -14),
                 lk=(40, 85), lf=(70, 180), rk=(-25, 92), rf=(-75, 178)),
    "run": dict(neck=(34, -162), head=(46, -212), sh=(30, -142),
                le=(-30, -95), lh=(0, -45), re=(88, -108), rh=(128, -160),
                lk=(-15, 95), lf=(-95, 180), rk=(85, 55), rf=(55, 135)),
    "overhead_lift": dict(neck=(0, -170), head=(0, -222), sh=SH,
                          le=(-85, -230), lh=(-115, -340), re=(85, -230), rh=(115, -340),
                          lk=(-55, 95), lf=(-75, 180), rk=(55, 95), rf=(75, 180)),
    "sit": dict(neck=(-5, -170), head=(-5, -222), sh=(-4, -150),
                le=(30, -80), lh=(95, -40), re=(15, -70), rh=(80, -30),
                lk=(140, 5), lf=(150, 185), rk=(160, 15), rf=(175, 185)),
    "sit_slouch": dict(neck=(-40, -150), head=(-52, -205), sh=(-32, -120),
                       le=(30, -45), lh=(100, -80), re=(5, -30), rh=(85, -65),
                       lk=(150, 10), lf=(160, 195), rk=(175, 35), rf=(200, 195)),
    "kneel_grind": dict(neck=(135, -125), head=(178, -170), sh=(125, -112),
                        le=(220, -50), lh=(298, 18), re=(205, -32), rh=(328, 22),
                        lk=(80, 100), lf=(-55, 108), rk=(100, 98), rf=(-30, 106), baseline=106),
    "kneel": dict(neck=(10, -170), head=(14, -222), sh=(10, -150),
                  le=(50, -85), lh=(90, -40), re=(40, -80), rh=(70, -30),
                  lk=(75, 100), lf=(-60, 108), rk=(90, 100), rf=(-40, 108), baseline=106),
    "point": dict(neck=(0, -170), head=(0, -222), sh=SH,
                  le=(-70, -70), lh=(-25, -20), re=(110, -190), rh=(220, -245),
                  lk=(-45, 90), lf=(-65, 180), rk=(45, 90), rf=(70, 180)),
    "carry": dict(neck=(-8, -168), head=(-10, -220), sh=(-6, -148),
                  le=(-25, -85), lh=(45, -105), re=(15, -75), rh=(70, -98),
                  lk=(-40, 85), lf=(-55, 180), rk=(40, 88), rf=(55, 180)),
    "squat_rest": dict(neck=(45, -150), head=(62, -198), sh=(40, -130),
                       le=(95, -75), lh=(140, -45), re=(110, -70), rh=(155, -40),
                       lk=(100, -50), lf=(75, 55), rk=(118, -44), rf=(95, 55), baseline=55),
    "throw": dict(neck=(-22, -168), head=(-28, -220), sh=(-20, -148),
                  le=(60, -150), lh=(120, -162), re=(-90, -190), rh=(-60, -262),
                  lk=(60, 85), lf=(110, 180), rk=(-50, 92), rf=(-100, 180), hold_dir=(1, -0.15)),
    "lie": dict(neck=(-170, -8), head=(-222, -14), sh=(-150, -8),
                le=(-90, 10), lh=(-20, 18), re=(-80, -2), rh=(-10, 6),
                lk=(90, 4), lf=(180, 8), rk=(90, -6), rf=(180, -2), baseline=30),
    "wave": dict(neck=(0, -170), head=(0, -222), sh=SH,
                 le=(-40, -75), lh=(-52, 5), re=(85, -215), rh=(110, -300),
                 lk=(-30, 90), lf=(-45, 180), rk=(30, 90), rf=(45, 180)),
    "celebrate": dict(neck=(0, -170), head=(0, -222), sh=SH,
                      le=(-80, -220), lh=(-120, -300), re=(80, -220), rh=(120, -300),
                      lk=(-35, 90), lf=(-60, 180), rk=(35, 90), rf=(60, 180)),
    "think": dict(neck=(0, -170), head=(0, -222), sh=SH,
                  le=(-55, -85), lh=(15, -95), re=(55, -95), rh=(22, -190),
                  lk=(-25, 90), lf=(-40, 180), rk=(30, 90), rf=(45, 180)),
    "bend_dig": dict(neck=(115, -110), head=(160, -150), sh=(105, -100),
                     le=(150, -20), lh=(185, 55), re=(175, -30), rh=(215, 40),
                     lk=(-20, 90), lf=(-40, 180), rk=(35, 90), rf=(20, 180)),
    "climb": dict(neck=(20, -170), head=(28, -222), sh=(18, -150),
                  le=(70, -210), lh=(95, -300), re=(90, -170), rh=(135, -240),
                  lk=(85, 20), lf=(70, 110), rk=(-10, 90), rf=(10, 180)),
    "tired_bent": dict(neck=(70, -140), head=(105, -178), sh=(64, -128),
                       le=(80, -60), lh=(70, 10), re=(100, -55), rh=(95, 12),
                       lk=(40, 90), lf=(20, 180), rk=(-20, 90), rf=(-40, 180)),
}

FACES = {"neutral", "smile", "strain", "tired", "surprised", "sad", "focused", "sleep"}


def _face(hx, hy, r, kind, look, s):
    dx, ey = 0.32 * r, hy - 0.1 * r
    lx = look * s
    er = 4.6 * s
    out = []
    if kind == "sleep":
        out.append(line([(hx - dx - 7 * s, ey), (hx - dx + 7 * s, ey)], 4 * s))
        out.append(line([(hx + dx - 7 * s, ey), (hx + dx + 7 * s, ey)], 4 * s))
    elif kind == "tired":
        for ex in (hx - dx + lx, hx + dx + lx):
            out.append(f'<circle cx="{ex:.1f}" cy="{ey + 2 * s:.1f}" r="{er:.1f}" fill="{INK}"/>')
            out.append(line([(ex - 9 * s, ey - 4 * s), (ex + 9 * s, ey - 3 * s)], 4 * s))
    else:
        for ex in (hx - dx + lx, hx + dx + lx):
            out.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{er:.1f}" fill="{INK}"/>')
    my = hy + 0.38 * r
    mx = hx + lx * 0.6
    if kind == "smile":
        out.append(path(f"M{mx - 14 * s},{my - 3 * s} q{14 * s},{14 * s} {28 * s},0", w=4 * s))
    elif kind == "strain":
        out.append(path(f"M{mx - 14 * s},{my} q{7 * s},{-8 * s} {14 * s},0 q{7 * s},{8 * s} {14 * s},0", w=4 * s))
    elif kind == "surprised":
        out.append(circle(mx, my, 8 * s, fill="#fff", w=4 * s))
    elif kind == "sad":
        out.append(path(f"M{mx - 13 * s},{my + 6 * s} q{13 * s},{-12 * s} {26 * s},0", w=4 * s))
    elif kind == "focused":
        out.append(line([(mx - 10 * s, my), (mx + 10 * s, my)], 4 * s))
        for ex in (hx - dx + lx, hx + dx + lx):
            out.append(line([(ex - 9 * s, ey - 10 * s), (ex + 9 * s, ey - 7 * s)], 4 * s))
    elif kind == "sleep":
        out.append(circle(mx, my, 5 * s, fill="#fff", w=3 * s))
    else:
        out.append(line([(mx - 12 * s, my), (mx + 12 * s, my)], 4 * s))
    return "".join(out)


def _drop(x, y, s=1.0):
    return path(f"M{x},{y} q{-9 * s},{16 * s} 0,{24 * s} q{9 * s},{-8 * s} 0,{-24 * s}z",
                fill="sweat", w=3 * s)


def draw_figure(spec: dict, default_ground: float) -> str:
    pose = POSES.get(spec.get("pose", "stand"))
    if pose is None:
        raise ValueError(f"unknown pose: {spec.get('pose')} (options: {', '.join(POSES)})")
    s = float(spec.get("scale", 1.0))
    flip = -1 if spec.get("flip") else 1
    ground = float(spec.get("ground", default_ground))
    baseline = pose.get("baseline", max(pose["lf"][1], pose["rf"][1]))
    hx0 = float(spec.get("x", 960))
    hy0 = ground - baseline * s

    def P(name):
        x, y = pose[name]
        return hx0 + flip * x * s, hy0 + y * s

    w = 8 * s
    wear = set(spec.get("wear", []) or [])
    hold = spec.get("hold", "none") or "none"
    out = []
    hip, neck, sh = (hx0, hy0), P("neck"), P("sh")
    hx, hy = P("head")
    r = HEAD_R * s

    # back items (drawn behind body)
    if hold == "log":
        a, b = P("lh"), P("rh")
        out.append(rect(min(a[0], b[0]) - 150 * s, min(a[1], b[1]) - 30 * s, abs(a[0] - b[0]) + 300 * s, 42 * s,
                        "bark", rx=18 * s, w=6 * s))
    if "hide" in wear:
        out.append(path(f"M{hip[0] - 24 * s},{hip[1] - 14 * s} L{hip[0] + 24 * s},{hip[1] - 14 * s} "
                        f"L{hip[0] + 16 * flip * s},{hip[1] + 26 * s} Q{hip[0]},{hip[1] + 34 * s} "
                        f"{hip[0] - 14 * flip * s},{hip[1] + 24 * s} Z", fill="hide", w=4 * s))

    out.append(line([hip, P("lk"), P("lf")], w))
    out.append(line([hip, P("rk"), P("rf")], w))
    out.append(line([hip, neck], w))
    out.append(line([sh, P("le"), P("lh")], w))
    out.append(line([sh, P("re"), P("rh")], w))

    # held items
    lh, rh = P("lh"), P("rh")
    if hold == "barbell":
        y = (lh[1] + rh[1]) / 2
        x1, x2 = min(lh[0], rh[0]) - 200 * s, max(lh[0], rh[0]) + 200 * s
        out.append(line([(x1, y), (x2, y)], 12 * s))
        for x, hh in ((x1 + 40 * s, 190), (x1 + 90 * s, 150), (x2 - 90 * s, 150), (x2 - 40 * s, 190)):
            out.append(rect(x - 20 * s, y - hh * s / 2, 40 * s, hh * s, "metal", rx=8 * s, w=6 * s))
    elif hold == "dumbbell":
        out.append(line([(rh[0] - 30 * s, rh[1]), (rh[0] + 30 * s, rh[1])], 9 * s))
        for x in (rh[0] - 38 * s, rh[0] + 38 * s):
            out.append(rect(x - 11 * s, rh[1] - 26 * s, 22 * s, 52 * s, "metal", rx=6 * s, w=5 * s))
    elif hold == "phone":
        out.append(rect(rh[0] - 15 * s, rh[1] - 30 * s, 30 * s, 52 * s, "#263238", rx=6 * s, w=5 * s))
        out.append(f'<rect x="{rh[0] - 9 * s:.1f}" y="{rh[1] - 23 * s:.1f}" width="{18 * s:.1f}" '
                   f'height="{36 * s:.1f}" rx="3" fill="{c("screen")}"/>')
    elif hold in ("spear", "stick", "pointer", "torch"):
        ex, ey = P("re")
        dx, dy = rh[0] - ex, rh[1] - ey
        if "hold_dir" in pose:
            dx, dy = flip * pose["hold_dir"][0], pose["hold_dir"][1]
        n = max((dx * dx + dy * dy) ** 0.5, 1)
        ux, uy = dx / n, dy / n
        L = {"spear": 300, "stick": 220, "pointer": 280, "torch": 90}[hold] * s
        back = {"spear": 140, "stick": 60, "pointer": 20, "torch": 60}[hold] * s
        a = (rh[0] - ux * back, rh[1] - uy * back)
        b = (rh[0] + ux * L, rh[1] + uy * L)
        out.append(line([a, b], (7 if hold != "pointer" else 5) * s, color=c("bark") if hold != "pointer" else INK))
        if hold == "spear":
            px, py = -uy, ux
            tip = (b[0] + ux * 45 * s, b[1] + uy * 45 * s)
            out.append(path(f"M{b[0] + px * 14 * s},{b[1] + py * 14 * s} L{tip[0]},{tip[1]} "
                            f"L{b[0] - px * 14 * s},{b[1] - py * 14 * s} Z", fill="stone", w=5 * s))
        if hold == "torch":
            out.append(path(f"M{b[0]},{b[1] - 50 * s} q{28 * s},{30 * s} 0,{50 * s} q{-28 * s},{-20 * s} 0,{-50 * s}z",
                            fill="fire", w=5 * s))
    elif hold == "rock":
        mx, my = (lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2 - 20 * s
        out.append(path(f"M{mx - 55 * s},{my + 20 * s} q{-5 * s},{-55 * s} {50 * s},{-60 * s} "
                        f"q{60 * s},{0} {60 * s},{50 * s} q{-10 * s},{30 * s} {-110 * s},{10 * s}z", fill="stone", w=6 * s))
    elif hold == "bowl":
        mx, my = (lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2
        out.append(path(f"M{mx - 45 * s},{my - 10 * s} q{45 * s},{55 * s} {90 * s},0 z", fill="clay", w=5 * s))

    # head + wear
    if "hair_bun" in wear:
        out.append(circle(hx - flip * 0.85 * r, hy - 0.7 * r, 0.38 * r, fill=INK, w=2))
    out.append(circle(hx, hy, r, fill="#fff", w=7 * s))
    if "headband" in wear:
        cid = f"hc{abs(hash((hx, hy))) % 10**8}"
        out.append(f'<clipPath id="{cid}"><circle cx="{hx:.1f}" cy="{hy:.1f}" r="{r - 3 * s:.1f}"/></clipPath>')
        out.append(f'<rect x="{hx - r:.1f}" y="{hy - 0.82 * r:.1f}" width="{2 * r:.1f}" height="{0.4 * r:.1f}" '
                   f'fill="{RED}" clip-path="url(#{cid})"/>')
        out.append(circle(hx, hy, r, fill="none", w=7 * s))
        tx = hx - flip * r
        out.append(line([(tx, hy - 0.62 * r), (tx - flip * 30 * s, hy - 0.95 * r), (tx - flip * 24 * s, hy - 0.4 * r)],
                        6 * s, color=RED))
    if "cap" in wear:
        out.append(path(f"M{hx - r},{hy - 0.35 * r} q{r},{-1.5 * r} {2 * r},0 z", fill="water", w=6 * s))
        out.append(line([(hx + flip * r * 0.6, hy - 0.35 * r), (hx + flip * r * 1.5, hy - 0.3 * r)], 7 * s))
    if "beard" in wear:
        out.append(path(f"M{hx - 0.7 * r},{hy + 0.35 * r} q{0.7 * r},{0.95 * r} {1.4 * r},0",
                        fill="#5b4636", w=5 * s))
    out.append(_face(hx, hy, r, spec.get("face", "neutral"), float(spec.get("look", 0)) * flip, s))

    if "whistle" in wear:
        out.append(line([(neck[0] - 16 * s, neck[1] + 2 * s), (neck[0] - 6 * s, neck[1] + 72 * s),
                         (neck[0] + 14 * s, neck[1] + 2 * s)], 3 * s))
        out.append(rect(neck[0] - 26 * s, neck[1] + 68 * s, 40 * s, 22 * s, "#9aa4ab", rx=9 * s, w=5 * s))

    if spec.get("sweat"):
        out.append(_drop(hx + flip * 1.25 * r, hy - 1.1 * r, s))
        out.append(_drop(hx - flip * 1.15 * r, hy - 0.4 * r, 0.8 * s))
    return "".join(out)
