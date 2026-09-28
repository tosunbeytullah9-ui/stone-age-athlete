"""Stick figures built from poses. A pose is a set of joint positions relative to the hip (0,0),
y grows downward, a standing figure's feet are at y=180 and head centre at y=-222.

Figure spec (all optional except pose):
  pose: see POSES (stand, walk, run, ... swim, dive, ride, wrestle, ...)
  x: hip x (0-1920)            ground: y of the floor under the feet (default from background)
  lift: px to raise the figure above `ground` (jumps, swimmers mid-water, people on a ledge)
  rotate: degrees to tilt the whole pose around the hip (+ = clockwise when facing right)
  scale: 1.0                   flip: false (true = faces left)
  face: neutral | smile | strain | tired | surprised | sad | focused | sleep
  look: -10..10 (eye shift)    wear: see WEAR
  hold: one name or a list, see HOLDS (e.g. [sword, shield])
  sweat: true | false
"""
from __future__ import annotations

import math

from .style import INK, RED, c, circle, line, path, rect

HEAD_R = 44
SH = (0, -150)  # default shoulder
# limb lengths shared by every pose (upper arm, forearm, thigh, shin)
UA, FA, TH, SN = 85, 80, 95, 92

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


# ---------------------------------------------------------------- pose builder
def _at(o, length, deg):
    a = math.radians(deg)
    return (round(o[0] + length * math.cos(a), 1), round(o[1] + length * math.sin(a), 1))


def _ik(a, t, l1, l2, bend):
    """Elbow/knee so that a limb from `a` ends at `t` (clamped to reach). bend: +1 / -1 picks the side."""
    dx, dy = t[0] - a[0], t[1] - a[1]
    d = min(max(math.hypot(dx, dy), abs(l1 - l2) + 0.5), l1 + l2 - 0.5)
    ang = math.atan2(dy, dx)
    k = math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    e = (a[0] + l1 * math.cos(ang + bend * k), a[1] + l1 * math.sin(ang + bend * k))
    u = math.atan2(t[1] - e[1], t[0] - e[0])
    return (round(e[0], 1), round(e[1], 1)), (round(e[0] + l2 * math.cos(u), 1), round(e[1] + l2 * math.sin(u), 1))


def _build(torso=-90, head=None, la=(100, 95), ra=(80, 85), ll=(108, 99), rl=(72, 81), air=0,
           lh_to=None, rh_to=None, bend_l=1, bend_r=1, **extra):
    """Pose from angles (deg; 0 = right/forward, 90 = down, -90 = up). Every limb keeps the shared
    lengths, so new poses match the old ones. `air` lifts the lowest point off the floor.
    lh_to / rh_to: a point (x, y) or a joint name ("lk", "rf", ...) the hand must reach (simple IK)."""
    hip = (0, 0)
    neck, sh = _at(hip, 170, torso), _at(hip, 150, torso)
    hd = _at(neck, 52, torso if head is None else head)
    lk = _at(hip, TH, ll[0]); lf = _at(lk, SN, ll[1])
    rk = _at(hip, TH, rl[0]); rf = _at(rk, SN, rl[1])
    p = dict(neck=neck, head=hd, sh=sh, lk=lk, lf=lf, rk=rk, rf=rf)
    le = _at(sh, UA, la[0]); lh = _at(le, FA, la[1])
    re = _at(sh, UA, ra[0]); rh = _at(re, FA, ra[1])
    if lh_to is not None:
        le, lh = _ik(sh, p[lh_to] if isinstance(lh_to, str) else lh_to, UA, FA, bend_l)
    if rh_to is not None:
        re, rh = _ik(sh, p[rh_to] if isinstance(rh_to, str) else rh_to, UA, FA, bend_r)
    p.update(le=le, lh=lh, re=re, rh=rh)
    if "baseline" not in extra:
        low = max(v[1] for k, v in p.items() if k != "head")
        low = max(low, hd[1] + HEAD_R)
        extra["baseline"] = round(low + 4 + air, 1)
    p.update(extra)
    return p


POSES.update({
    # --- water ---------------------------------------------------------------------------
    "swim": _build(torso=-4, la=(115, 165), ra=(-6, -2), ll=(176, 184), rl=(186, 196)),
    "dive": _build(torso=62, la=(50, 56), ra=(74, 70), ll=(-118, -112), rl=(-128, -138)),
    "float": _build(torso=-80, la=(-150, -165), ra=(-25, -15), ll=(118, 112), rl=(62, 68)),
    "tread": _build(torso=-90, la=(165, 190), ra=(15, -10), ll=(55, 125), rl=(110, 150)),
    # --- jumps -----------------------------------------------------------------------------
    "jump": _build(torso=-90, la=(110, 100), ra=(70, 80), ll=(94, 88), rl=(86, 80), air=90),
    "leap": _build(torso=-86, la=(-125, -110), ra=(-55, -70), ll=(35, 125), rl=(150, 110), air=80),
    # --- floor exercise --------------------------------------------------------------------
    "push_up": _build(torso=-24, head=-18, la=(92, 88), ra=(88, 84), ll=(156, 156), rl=(157, 157)),
    "plank": _build(torso=-15, head=-10, la=(92, 0), ra=(88, -4), ll=(165, 165), rl=(166, 166)),
    "lunge": _build(torso=-90, la=(95, 100), ra=(80, 95), ll=(15, 95), rl=(110, 162)),
    "deep_squat": dict(neck=(0, -170), head=(0, -222), sh=SH,
                       le=(-75, -110), lh=(-95, -186), re=(75, -110), rh=(95, -186),
                       lk=(-93, -10), lf=(-104, 82), rk=(93, -10), rf=(104, 82), baseline=86),
    "sprint_start": _build(torso=5, head=15, la=(92, 90), ra=(86, 88), ll=(70, 110), rl=(122, 138)),
    "stretch": _build(torso=-100, head=-112, la=(-150, -178), ra=(-112, -160), ll=(114, 100), rl=(66, 80)),
    "sit_floor": dict(neck=(0, -170), head=(0, -222), sh=SH,
                      le=(-55, -85), lh=(-80, -8), re=(55, -85), rh=(80, -8),
                      lk=(-88, 8), lf=(4, 30), rk=(88, 8), rf=(-4, 30), baseline=36),
    # --- work & carrying ---------------------------------------------------------------------
    "carry_head": dict(neck=(0, -170), head=(0, -222), sh=SH,
                       le=(-66, -204), lh=(-30, -275), re=(66, -204), rh=(30, -275),
                       lk=(-30, 90), lf=(-45, 180), rk=(30, 90), rf=(45, 180), head_load=True),
    "crawl": _build(torso=-12, head=-35, la=(96, 84), ra=(84, 96), ll=(95, 180), rl=(85, 176)),
    "push": _build(torso=-32, head=-25, la=(-18, -12), ra=(-10, -6), ll=(55, 115), rl=(128, 128)),
    "pull": _build(torso=-118, head=-100, la=(12, 2), ra=(4, -6), ll=(72, 60), rl=(115, 110),
                   hold_dir=(1, 0.08)),
    "hang": _build(torso=-90, la=(-135, -100), ra=(-45, -80), ll=(96, 100), rl=(84, 80), air=45),
    # --- sport & war -------------------------------------------------------------------------
    "draw_bow": _build(torso=-92, ra=(-3, -3), ll=(118, 100), rl=(62, 80), lh_to=(30, -178), bend_l=1),
    "ride": _build(torso=-84, la=(60, -12), ra=(55, -20), ll=(62, 102), rl=(58, 98), baseline=340),
    "row": _build(torso=-82, ll=(-6, 14), rl=(-2, 20), lh_to=(45, -245), rh_to=(125, -95),
                  bend_l=1, bend_r=1),
    "wrestle": _build(torso=-38, head=-30, la=(-5, 20), ra=(10, 35), ll=(58, 112), rl=(128, 105)),
    "march": _build(torso=-90, la=(115, 110), ra=(60, -15), ll=(62, 98), rl=(118, 112)),
    "shiko": _build(torso=-76, ll=(-150, -168), rl=(66, 96), lh_to="lk", rh_to="rk", bend_l=-1, bend_r=1),
    "club_swing": _build(torso=-90, ll=(106, 98), rl=(74, 82), lh_to=(-78, -125), rh_to=(78, -125),
                         bend_l=1, bend_r=-1),
    "guard": _build(torso=-84, la=(30, -20), ra=(-150, -75), ll=(58, 100), rl=(125, 110)),
})

# how far apart (in px at scale 1) two facing `wrestle` figures stand so that their hands meet
WRESTLE_GAP = round(2 * POSES["wrestle"]["rh"][0] - 30)
# y of the hands above the floor for `hang` (use for a pullup_bar / branch at the same scale)
HANG_HANDS = round(POSES["hang"]["baseline"] - min(POSES["hang"]["lh"][1], POSES["hang"]["rh"][1]))

FACES = {"neutral", "smile", "strain", "tired", "surprised", "sad", "focused", "sleep"}
WEAR = ["headband", "whistle", "hair_bun", "hide", "beard", "cap",
        "roman_helmet", "knight_helmet", "samurai_helmet", "goggles", "turban", "janissary_hat", "beanie",
        "fur_hood", "topknot", "headscarf", "armor", "tunic", "parka", "loincloth", "mawashi", "tights",
        "shoes", "sandals", "backpack", "medal"]
HOLDS = ["barbell", "dumbbell", "phone", "spear", "pointer", "rock", "log", "stick", "torch", "bowl",
         "bow", "sword", "shield", "scutum", "indian_club", "meel", "gada", "kettlebell", "fish", "paddle",
         "rope", "jar", "basket", "bundle", "baby", "shaker", "none"]


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


def _band(pts, width, fill, s, outline=5.0):
    """Thick outlined stroke (sleeves, trousers, blades)."""
    return line(pts, width + 2 * outline * s, color=INK) + line(pts, width, color=c(fill))


def _unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = max(math.hypot(dx, dy), 1e-6)
    return dx / n, dy / n


def _poly(pts, fill, w):
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
    return path(d, fill=fill, w=w)


def _rot(pt, deg):
    if not deg:
        return pt
    a = math.radians(deg)
    x, y = pt
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def draw_figure(spec: dict, default_ground: float) -> str:
    pose = POSES.get(spec.get("pose", "stand"))
    if pose is None:
        raise ValueError(f"unknown pose: {spec.get('pose')} (options: {', '.join(POSES)})")
    s = float(spec.get("scale", 1.0))
    flip = -1 if spec.get("flip") else 1
    ground = float(spec.get("ground", default_ground))
    rot = float(spec.get("rotate", 0) or 0)
    joints = {k: _rot(v, rot) for k, v in pose.items()
              if k in ("neck", "head", "sh", "le", "lh", "re", "rh", "lk", "lf", "rk", "rf")}
    if rot:
        baseline = max(max(v[1] for k, v in joints.items() if k != "head"), joints["head"][1] + HEAD_R) + 4
    else:
        baseline = pose.get("baseline", max(pose["lf"][1], pose["rf"][1]))
    hx0 = float(spec.get("x", 960))
    hy0 = ground - baseline * s - float(spec.get("lift", 0) or 0)

    def P(name):
        x, y = joints[name]
        return hx0 + flip * x * s, hy0 + y * s

    w = 8 * s
    wear = set(spec.get("wear", []) or [])
    hold_raw = spec.get("hold", "none") or "none"
    holds = set([hold_raw] if isinstance(hold_raw, str) else hold_raw)
    hold_dir = pose.get("hold_dir")
    if hold_dir is not None:
        hold_dir = _rot(hold_dir, rot)
    out = []
    hip, neck, sh = (hx0, hy0), P("neck"), P("sh")
    hx, hy = P("head")
    r = HEAD_R * s
    up = _unit(hip, neck)                       # along the torso, towards the head
    fwd = (-up[1] * flip, up[0] * flip)         # chest side
    lk, rk, lf, rf = P("lk"), P("rk"), P("lf"), P("rf")
    lh, rh = P("lh"), P("rh")
    head_load = pose.get("head_load", False)

    # ---------------- back items (drawn behind body)
    if "log" in holds:
        a, b = lh, rh
        out.append(rect(min(a[0], b[0]) - 150 * s, min(a[1], b[1]) - 30 * s, abs(a[0] - b[0]) + 300 * s, 42 * s,
                        "bark", rx=18 * s, w=6 * s))
    if "backpack" in wear:
        mid = (hip[0] + up[0] * 95 * s - fwd[0] * 34 * s, hip[1] + up[1] * 95 * s - fwd[1] * 34 * s)
        pts = [(mid[0] + up[0] * a * s + fwd[0] * b * s, mid[1] + up[1] * a * s + fwd[1] * b * s)
               for a, b in ((60, 22), (60, -34), (-55, -38), (-55, 22))]
        out.append(_poly(pts, "clay", 6 * s))
    if "fur_hood" in wear or "parka" in wear:
        out.append(circle(hx, hy, r * 1.42, fill="hide", w=7 * s))
        out.append(circle(hx, hy, r * 1.18, fill="#efe3c8", w=0))
    if "hide" in wear:
        out.append(path(f"M{hip[0] - 24 * s},{hip[1] - 14 * s} L{hip[0] + 24 * s},{hip[1] - 14 * s} "
                        f"L{hip[0] + 16 * flip * s},{hip[1] + 26 * s} Q{hip[0]},{hip[1] + 34 * s} "
                        f"{hip[0] - 14 * flip * s},{hip[1] + 24 * s} Z", fill="hide", w=4 * s))

    if pose.get("hold_behind"):
        out.append(_held(holds, pose, P, s, flip, hold_dir, hx, hy, r, head_load))

    # ---------------- legs + leg wear
    out.append(line([hip, lk, lf], w))
    out.append(line([hip, rk, rf], w))
    if "tights" in wear:
        for k, f in ((lk, lf), (rk, rf)):
            below = (k[0] + (f[0] - k[0]) * 0.3, k[1] + (f[1] - k[1]) * 0.3)
            out.append(_band([hip, k, below], 20 * s, "#4a3526", s, 3))
    if "parka" in wear:
        for k, f in ((lk, lf), (rk, rf)):
            out.append(_band([hip, k, f], 22 * s, "#8a6a48", s, 3))
    if "shoes" in wear or "sandals" in wear:
        for k, f in ((lk, lf), (rk, rf)):
            d = _unit(k, f)
            # sole points forward, perpendicular to the shin
            fx = (-d[1] * flip, d[0] * flip)
            if fx[0] * flip < 0:
                fx = (-fx[0], -fx[1])
            a = (f[0] - fx[0] * 8 * s, f[1] - fx[1] * 8 * s)
            b = (f[0] + fx[0] * 34 * s, f[1] + fx[1] * 34 * s)
            if "shoes" in wear:
                out.append(_band([a, b], 16 * s, "#e9edf0", s, 3.5))
                out.append(line([(a[0] + d[0] * 6 * s, a[1] + d[1] * 6 * s),
                                 (b[0] + d[0] * 6 * s, b[1] + d[1] * 6 * s)], 4 * s, color=RED))
            else:
                out.append(line([(a[0] + d[0] * 7 * s, a[1] + d[1] * 7 * s),
                                 (b[0] + d[0] * 7 * s, b[1] + d[1] * 7 * s)], 7 * s, color=c("bark")))
                out.append(line([(f[0] - d[0] * 14 * s, f[1] - d[1] * 14 * s), (b[0], b[1])], 3 * s))

    # ---------------- torso + torso wear
    out.append(line([hip, neck], w))
    P2 = lambda o, a, b: (o[0] + up[0] * a * s + fwd[0] * b * s, o[1] + up[1] * a * s + fwd[1] * b * s)  # noqa: E731
    if "tunic" in wear:
        out.append(_poly([P2(sh, 4, -26), P2(sh, 4, 26), P2(hip, -62, 46), P2(hip, -62, -46)], "#e8dcc0", 6 * s))
        out.append(line([P2(hip, 6, -34), P2(hip, 6, 34)], 6 * s, color=c("bark")))
    if "parka" in wear:
        out.append(_poly([P2(sh, 8, -32), P2(sh, 8, 32), P2(hip, -40, 44), P2(hip, -40, -44)], "hide", 6 * s))
        out.append(line([P2(hip, -34, -40), P2(hip, -34, 40)], 12 * s, color="#efe3c8"))
    if "armor" in wear:
        out.append(_poly([P2(sh, 6, -30), P2(sh, 6, 30), P2(hip, -8, 30), P2(hip, -8, -30)], "#aeb6bb", 6 * s))
        for t in (0.3, 0.52, 0.74):
            a = (hip[0] + (sh[0] - hip[0]) * t, hip[1] + (sh[1] - hip[1]) * t)
            out.append(line([P2(a, 0, -28), P2(a, 0, 28)], 4 * s))
        # skirt of leather strips
        for b in (-24, -8, 8, 24):
            out.append(line([P2(hip, -6, b), P2(hip, -44, b * 1.15)], 8 * s, color=c("bark")))
    if "mawashi" in wear:
        out.append(_poly([P2(hip, 18, -36), P2(hip, 18, 36), P2(hip, -16, 32), P2(hip, -16, -32)], "#3d4f7a", 5 * s))
        out.append(_poly([P2(hip, -10, 8), P2(hip, -10, 26), P2(hip, -50, 24), P2(hip, -50, 10)], "#3d4f7a", 4 * s))
    if "loincloth" in wear:
        out.append(_poly([P2(hip, 12, -30), P2(hip, 12, 30), P2(hip, -8, 28), P2(hip, -8, -28)], "#e8dcc0", 4 * s))
        out.append(_poly([P2(hip, -6, 4), P2(hip, -6, 26), P2(hip, -52, 22), P2(hip, -52, 8)], "#e8dcc0", 4 * s))
    if "medal" in wear:
        c0 = P2(neck, -70, 6)
        out.append(line([P2(neck, 0, -16), c0, P2(neck, 0, 22)], 5 * s, color=RED))
        out.append(circle(c0[0], c0[1], 15 * s, fill="grain", w=5 * s))

    # ---------------- arms (+ sleeves)
    out.append(line([sh, P("le"), lh], w))
    out.append(line([sh, P("re"), rh], w))
    if "parka" in wear:
        for e, hnd in ((P("le"), lh), (P("re"), rh)):
            cuff = (e[0] + (hnd[0] - e[0]) * 0.8, e[1] + (hnd[1] - e[1]) * 0.8)
            out.append(_band([sh, e, cuff], 20 * s, "hide", s, 3))

    # ---------------- held items
    if not pose.get("hold_behind"):
        out.append(_held(holds, pose, P, s, flip, hold_dir, hx, hy, r, head_load))

    # ---------------- head + wear
    if "hair_bun" in wear:
        out.append(circle(hx - flip * 0.85 * r, hy - 0.7 * r, 0.38 * r, fill=INK, w=2))
    if "topknot" in wear:
        out.append(path(f"M{hx - 0.25 * r},{hy - 0.92 * r} q{0.2 * r},{-0.55 * r} {0.55 * r},{-0.35 * r} "
                        f"q{0.2 * r},{0.15 * r} {-0.05 * r},{0.45 * r} z", fill=INK, w=3 * s))
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
    out.append(_headwear(wear, hx, hy, r, s, flip))
    if "knight_helmet" not in wear:
        out.append(_face(hx, hy, r, spec.get("face", "neutral"), float(spec.get("look", 0)) * flip, s))
    if "goggles" in wear:
        dx, ey = 0.32 * r, hy - 0.1 * r
        out.append(line([(hx - r, ey), (hx + r, ey)], 6 * s, color="#2f3b45"))
        for ex in (hx - dx, hx + dx):
            out.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{12 * s:.1f}" fill="{c("screen")}" fill-opacity="0.55" '
                       f'stroke="{INK}" stroke-width="{5 * s:.1f}"/>')
        for ex in (hx - dx, hx + dx):
            out.append(f'<circle cx="{ex + float(spec.get("look", 0)) * flip * s:.1f}" cy="{ey:.1f}" '
                       f'r="{4 * s:.1f}" fill="{INK}"/>')

    if "whistle" in wear:
        out.append(line([(neck[0] - 16 * s, neck[1] + 2 * s), (neck[0] - 6 * s, neck[1] + 72 * s),
                         (neck[0] + 14 * s, neck[1] + 2 * s)], 3 * s))
        out.append(rect(neck[0] - 26 * s, neck[1] + 68 * s, 40 * s, 22 * s, "#9aa4ab", rx=9 * s, w=5 * s))

    # load balanced on the head (carry_head pose) goes on top of everything
    if head_load:
        out.append(_head_load(holds, hx, hy, r, s))

    if spec.get("sweat"):
        out.append(_drop(hx + flip * 1.25 * r, hy - 1.1 * r, s))
        out.append(_drop(hx - flip * 1.15 * r, hy - 0.4 * r, 0.8 * s))
    return "".join(out)


def _headwear(wear, hx, hy, r, s, flip):
    out = []
    if "roman_helmet" in wear:
        out.append(path(f"M{hx - 1.08 * r},{hy - 0.05 * r} A{1.08 * r},{1.1 * r} 0 0 1 {hx + 1.08 * r},{hy - 0.05 * r} "
                        f"L{hx + 0.95 * r},{hy - 0.3 * r} L{hx - 0.95 * r},{hy - 0.3 * r} Z", fill="#c9a24a", w=6 * s))
        # cheek guards
        for sx in (-1, 1):
            out.append(path(f"M{hx + sx * 1.02 * r},{hy - 0.2 * r} L{hx + sx * 0.98 * r},{hy + 0.45 * r} "
                            f"L{hx + sx * 0.72 * r},{hy + 0.3 * r} L{hx + sx * 0.78 * r},{hy - 0.2 * r} Z",
                            fill="#c9a24a", w=5 * s))
        # crest
        out.append(path(f"M{hx - 0.9 * r},{hy - 1.0 * r} Q{hx},{hy - 1.9 * r} {hx + 0.9 * r},{hy - 1.0 * r} "
                        f"Q{hx},{hy - 1.25 * r} {hx - 0.9 * r},{hy - 1.0 * r} Z", fill=RED, w=5 * s))
    if "knight_helmet" in wear:
        out.append(path(f"M{hx - 1.05 * r},{hy + 0.9 * r} L{hx - 1.05 * r},{hy - 0.6 * r} "
                        f"Q{hx},{hy - 1.35 * r} {hx + 1.05 * r},{hy - 0.6 * r} L{hx + 1.05 * r},{hy + 0.9 * r} Z",
                        fill="#aeb6bb", w=7 * s))
        out.append(line([(hx - 0.75 * r, hy - 0.12 * r), (hx + 0.75 * r, hy - 0.12 * r)], 9 * s))
        out.append(line([(hx, hy + 0.1 * r), (hx, hy + 0.75 * r)], 4 * s))
        for yy in (0.3, 0.5):
            out.append(f'<circle cx="{hx + flip * 0.5 * r:.1f}" cy="{hy + yy * r:.1f}" r="{3 * s:.1f}" fill="{INK}"/>')
    if "samurai_helmet" in wear:
        out.append(path(f"M{hx - 0.95 * r},{hy - 0.35 * r} A{0.95 * r},{0.95 * r} 0 0 1 {hx + 0.95 * r},{hy - 0.35 * r} Z",
                        fill="#2f3b45", w=6 * s))
        out.append(path(f"M{hx - 1.1 * r},{hy - 0.4 * r} Q{hx - 1.55 * r},{hy + 0.1 * r} {hx - 1.35 * r},{hy + 0.55 * r} "
                        f"L{hx - 0.95 * r},{hy - 0.25 * r} Z", fill="#2f3b45", w=5 * s))
        out.append(path(f"M{hx + 1.1 * r},{hy - 0.4 * r} Q{hx + 1.55 * r},{hy + 0.1 * r} {hx + 1.35 * r},{hy + 0.55 * r} "
                        f"L{hx + 0.95 * r},{hy - 0.25 * r} Z", fill="#2f3b45", w=5 * s))
        out.append(path(f"M{hx - 0.15 * r},{hy - 1.2 * r} L{hx - 0.7 * r},{hy - 1.9 * r} M{hx + 0.15 * r},{hy - 1.2 * r} "
                        f"L{hx + 0.7 * r},{hy - 1.9 * r}", w=7 * s, stroke=c("grain")))
    if "turban" in wear:
        out.append(path(f"M{hx - 1.05 * r},{hy - 0.3 * r} Q{hx - 1.2 * r},{hy - 1.5 * r} {hx},{hy - 1.55 * r} "
                        f"Q{hx + 1.2 * r},{hy - 1.5 * r} {hx + 1.05 * r},{hy - 0.3 * r} Z", fill="#f3ead8", w=6 * s))
        out.append(path(f"M{hx - 0.95 * r},{hy - 0.55 * r} Q{hx},{hy - 1.2 * r} {hx + 0.95 * r},{hy - 0.95 * r}", w=4 * s))
        out.append(path(f"M{hx - 0.85 * r},{hy - 0.95 * r} Q{hx},{hy - 1.5 * r} {hx + 0.8 * r},{hy - 1.25 * r}", w=4 * s))
    if "janissary_hat" in wear:
        # tall white felt börk folding down the back, with a gold band
        out.append(path(f"M{hx - 0.8 * r},{hy - 0.55 * r} L{hx - 0.55 * r},{hy - 2.3 * r} Q{hx - flip * 0.2 * r},{hy - 2.55 * r} "
                        f"{hx + 0.55 * r},{hy - 2.3 * r} L{hx + 0.8 * r},{hy - 0.55 * r} Z", fill="#f7f2e6", w=6 * s))
        bx = hx - flip * 0.55 * r
        out.append(path(f"M{bx},{hy - 2.3 * r} Q{bx - flip * 1.1 * r},{hy - 1.9 * r} {bx - flip * 1.0 * r},{hy - 0.2 * r} "
                        f"L{bx - flip * 0.5 * r},{hy - 0.3 * r} Z", fill="#f7f2e6", w=5 * s))
        out.append(rect(hx - 0.9 * r, hy - 0.8 * r, 1.8 * r, 0.32 * r, "grain", rx=4 * s, w=5 * s))
    if "beanie" in wear:
        out.append(path(f"M{hx - 1.02 * r},{hy - 0.3 * r} A{1.02 * r},{1.05 * r} 0 0 1 {hx + 1.02 * r},{hy - 0.3 * r} Z",
                        fill=RED, w=6 * s))
        out.append(rect(hx - 1.06 * r, hy - 0.52 * r, 2.12 * r, 0.3 * r, "#f3ead8", rx=6 * s, w=5 * s))
        out.append(circle(hx, hy - 1.38 * r, 0.26 * r, fill="#f3ead8", w=5 * s))
    if "headscarf" in wear:
        out.append(path(f"M{hx - 1.1 * r},{hy + 0.2 * r} Q{hx - 1.2 * r},{hy - 1.3 * r} {hx},{hy - 1.2 * r} "
                        f"Q{hx + 1.2 * r},{hy - 1.3 * r} {hx + 1.1 * r},{hy + 0.2 * r} Q{hx + 0.9 * r},{hy - 0.55 * r} {hx},{hy - 0.62 * r} "
                        f"Q{hx - 0.9 * r},{hy - 0.55 * r} {hx - 1.1 * r},{hy + 0.2 * r} Z", fill="ochre", w=5 * s))
        tx = hx - flip * 1.0 * r
        out.append(path(f"M{tx},{hy} q{-flip * 0.5 * r},{0.5 * r} {-flip * 0.2 * r},{1.1 * r} "
                        f"l{flip * 0.35 * r},{-0.2 * r} z", fill="ochre", w=4 * s))
    return "".join(out)


def _head_load(holds, hx, hy, r, s):
    top = hy - r
    if "basket" in holds:
        return (path(f"M{hx - 1.4 * r},{top - 1.3 * r} L{hx + 1.4 * r},{top - 1.3 * r} L{hx + 1.0 * r},{top} "
                     f"L{hx - 1.0 * r},{top} Z", fill="grain", w=6 * s)
                + line([(hx - 1.2 * r, top - 0.65 * r), (hx + 1.2 * r, top - 0.65 * r)], 4 * s))
    if "bundle" in holds:
        out = []
        for i, dy in enumerate((0.35, 0.75, 1.15)):
            out.append(rect(hx - 2.2 * r + i * 0.2 * r, top - dy * r - 0.3 * r, 4.2 * r, 0.36 * r, "bark", rx=8 * s, w=5 * s))
        out.append(line([(hx - 1.1 * r, top), (hx - 1.1 * r, top - 1.5 * r)], 5 * s, color=c("ochre")))
        out.append(line([(hx + 1.1 * r, top), (hx + 1.1 * r, top - 1.5 * r)], 5 * s, color=c("ochre")))
        return "".join(out)
    # default: a clay water jar
    return path(f"M{hx - 0.45 * r},{top} Q{hx - 1.5 * r},{top - 0.9 * r} {hx - 0.35 * r},{top - 1.9 * r} "
                f"L{hx - 0.35 * r},{top - 2.3 * r} L{hx + 0.35 * r},{top - 2.3 * r} L{hx + 0.35 * r},{top - 1.9 * r} "
                f"Q{hx + 1.5 * r},{top - 0.9 * r} {hx + 0.45 * r},{top} Z", fill="clay", w=6 * s)


def _held(holds, pose, P, s, flip, hold_dir, hx, hy, r, head_load) -> str:
    out = []
    lh, rh = P("lh"), P("rh")
    re, le = P("re"), P("le")

    if "barbell" in holds:
        y = (lh[1] + rh[1]) / 2
        x1, x2 = min(lh[0], rh[0]) - 200 * s, max(lh[0], rh[0]) + 200 * s
        out.append(line([(x1, y), (x2, y)], 12 * s))
        for x, hh in ((x1 + 40 * s, 190), (x1 + 90 * s, 150), (x2 - 90 * s, 150), (x2 - 40 * s, 190)):
            out.append(rect(x - 20 * s, y - hh * s / 2, 40 * s, hh * s, "metal", rx=8 * s, w=6 * s))
    if "dumbbell" in holds:
        out.append(line([(rh[0] - 30 * s, rh[1]), (rh[0] + 30 * s, rh[1])], 9 * s))
        for x in (rh[0] - 38 * s, rh[0] + 38 * s):
            out.append(rect(x - 11 * s, rh[1] - 26 * s, 22 * s, 52 * s, "metal", rx=6 * s, w=5 * s))
    if "phone" in holds:
        out.append(rect(rh[0] - 15 * s, rh[1] - 30 * s, 30 * s, 52 * s, "#263238", rx=6 * s, w=5 * s))
        out.append(f'<rect x="{rh[0] - 9 * s:.1f}" y="{rh[1] - 23 * s:.1f}" width="{18 * s:.1f}" '
                   f'height="{36 * s:.1f}" rx="3" fill="{c("screen")}"/>')
    for hold in ("spear", "stick", "pointer", "torch"):
        if hold not in holds:
            continue
        dx, dy = rh[0] - re[0], rh[1] - re[1]
        if hold_dir is not None:
            dx, dy = flip * hold_dir[0], hold_dir[1]
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
    if "rock" in holds:
        mx, my = (lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2 - 20 * s
        out.append(path(f"M{mx - 55 * s},{my + 20 * s} q{-5 * s},{-55 * s} {50 * s},{-60 * s} "
                        f"q{60 * s},{0} {60 * s},{50 * s} q{-10 * s},{30 * s} {-110 * s},{10 * s}z", fill="stone", w=6 * s))
    if "bowl" in holds:
        mx, my = (lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2
        out.append(path(f"M{mx - 45 * s},{my - 10 * s} q{45 * s},{55 * s} {90 * s},0 z", fill="clay", w=5 * s))

    # ---- new holds
    if "bow" in holds:
        # the bow is in the right (front) hand, perpendicular to the forearm; string to the left hand
        d = _unit(re, rh)
        if pose is POSES.get("draw_bow"):
            d = (flip * 1.0, 0.0)
        px, py = -d[1], d[0]
        L = 150 * s
        t1 = (rh[0] - px * L, rh[1] - py * L)
        t2 = (rh[0] + px * L, rh[1] + py * L)
        bulge = (rh[0] + d[0] * 70 * s, rh[1] + d[1] * 70 * s)
        pull = lh if pose is POSES.get("draw_bow") else (rh[0] - d[0] * 20 * s, rh[1] - d[1] * 20 * s)
        out.append(line([t1, pull, t2], 3 * s, color="#5a5a5a"))
        out.append(path(f"M{t1[0]:.1f},{t1[1]:.1f} Q{2 * bulge[0] - (t1[0] + t2[0]) / 2:.1f},"
                        f"{2 * bulge[1] - (t1[1] + t2[1]) / 2:.1f} {t2[0]:.1f},{t2[1]:.1f}", w=16 * s))
        out.append(path(f"M{t1[0]:.1f},{t1[1]:.1f} Q{2 * bulge[0] - (t1[0] + t2[0]) / 2:.1f},"
                        f"{2 * bulge[1] - (t1[1] + t2[1]) / 2:.1f} {t2[0]:.1f},{t2[1]:.1f}", w=8 * s, stroke=c("bark")))
        if pose is POSES.get("draw_bow"):
            tip = (rh[0] + d[0] * 60 * s, pull[1] + (rh[1] - pull[1]) * 1.1)
            out.append(line([pull, tip], 5 * s))
            out.append(path(f"M{tip[0]},{tip[1] - 9 * s} L{tip[0] + d[0] * 24 * s},{tip[1]} L{tip[0]},{tip[1] + 9 * s} Z",
                            fill="stone", w=4 * s))
    if "sword" in holds:
        d = _unit(re, rh)
        px, py = -d[1], d[0]
        tip = (rh[0] + d[0] * 210 * s, rh[1] + d[1] * 210 * s)
        base = (rh[0] + d[0] * 22 * s, rh[1] + d[1] * 22 * s)
        out.append(_poly([(base[0] + px * 10 * s, base[1] + py * 10 * s), (tip[0], tip[1]),
                          (base[0] - px * 10 * s, base[1] - py * 10 * s)], "#dfe4e7", 5 * s))
        out.append(line([(base[0] + px * 26 * s, base[1] + py * 26 * s), (base[0] - px * 26 * s, base[1] - py * 26 * s)],
                        9 * s, color=c("bark")))
        out.append(line([rh, (rh[0] - d[0] * 26 * s, rh[1] - d[1] * 26 * s)], 9 * s, color=c("bark")))
    for name in ("shield", "scutum"):
        if name in holds:
            if name == "shield":
                out.append(circle(lh[0], lh[1], 78 * s, fill="#c9a24a", w=7 * s))
                out.append(circle(lh[0], lh[1], 50 * s, fill="none", w=4 * s))
                out.append(circle(lh[0], lh[1], 14 * s, fill="#aeb6bb", w=5 * s))
            else:
                out.append(rect(lh[0] - 58 * s, lh[1] - 105 * s, 116 * s, 210 * s, RED, rx=16 * s, w=7 * s))
                out.append(circle(lh[0], lh[1], 20 * s, fill="#c9a24a", w=5 * s))
                out.append(line([(lh[0], lh[1] - 90 * s), (lh[0], lh[1] - 25 * s)], 5 * s, color=c("grain")))
                out.append(line([(lh[0], lh[1] + 25 * s), (lh[0], lh[1] + 90 * s)], 5 * s, color=c("grain")))
    for name, L, R in (("indian_club", 120, 22), ("meel", 190, 36)):
        if name in holds:
            for e, h in ((le, lh), (re, rh)):
                side = 1 if h[0] >= P("sh")[0] else -1
                if hold_dir is not None:
                    d = _unit((0, 0), (flip * hold_dir[0] + side * 0.35, hold_dir[1]))
                else:
                    d = _unit((0, 0), (side * 0.3, -1.0))
                px, py = -d[1], d[0]
                n1 = (h[0] - d[0] * 14 * s, h[1] - d[1] * 14 * s)
                end = (h[0] + d[0] * L * s, h[1] + d[1] * L * s)
                mid = (h[0] + d[0] * L * 0.62 * s, h[1] + d[1] * L * 0.62 * s)
                out.append(path(f"M{n1[0] + px * 7 * s},{n1[1] + py * 7 * s} "
                                f"Q{mid[0] + px * R * 1.25 * s},{mid[1] + py * R * 1.5 * s} {end[0] + px * R * 0.6 * s},{end[1] + py * R * 0.6 * s} "
                                f"L{end[0] - px * R * 0.6 * s},{end[1] - py * R * 0.6 * s} "
                                f"Q{mid[0] - px * R * 1.25 * s},{mid[1] - py * R * 1.5 * s} {n1[0] - px * 7 * s},{n1[1] - py * 7 * s} Z",
                                fill="bark" if name == "meel" else "#e6c89a", w=6 * s))
    if "gada" in holds:
        d = (flip * hold_dir[0], hold_dir[1]) if hold_dir is not None else _unit(re, rh)
        if hold_dir is None:
            d = (0.0, -1.0) if abs(d[1]) > 0.2 else d
        end = (rh[0] + d[0] * 170 * s, rh[1] + d[1] * 170 * s)
        out.append(line([(rh[0] - d[0] * 20 * s, rh[1] - d[1] * 20 * s), end], 10 * s, color=c("bark")))
        out.append(circle(end[0] + d[0] * 30 * s, end[1] + d[1] * 30 * s, 48 * s, fill="stone", w=7 * s))
    if "kettlebell" in holds:
        cx, cy = rh[0], rh[1] + 62 * s
        out.append(path(f"M{cx - 26 * s},{cy - 30 * s} Q{cx - 30 * s},{rh[1] - 16 * s} {cx},{rh[1] - 16 * s} "
                        f"Q{cx + 30 * s},{rh[1] - 16 * s} {cx + 26 * s},{cy - 30 * s}", w=9 * s))
        out.append(circle(cx, cy, 44 * s, fill="metal", w=7 * s))
    if "fish" in holds:
        cx, cy = rh[0], rh[1] + 55 * s
        out.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{20 * s:.1f}" ry="{52 * s:.1f}" fill="{c("water")}" '
                   f'stroke="{INK}" stroke-width="{5 * s:.1f}"/>')
        out.append(_poly([(cx, cy + 46 * s), (cx - 22 * s, cy + 80 * s), (cx + 22 * s, cy + 80 * s)], "water", 5 * s))
        out.append(f'<circle cx="{cx + 6 * s:.1f}" cy="{cy - 30 * s:.1f}" r="{4 * s:.1f}" fill="{INK}"/>')
    if "paddle" in holds:
        if hold_dir is not None:
            d = (flip * hold_dir[0], hold_dir[1])
        else:
            lo, hi = (lh, rh) if lh[1] > rh[1] else (rh, lh)
            d = _unit(hi, lo) if math.dist(lh, rh) > 20 * s else (flip * 0.5, 0.85)
        mx, my = (lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2
        a = (mx - d[0] * 110 * s, my - d[1] * 110 * s)
        b = (mx + d[0] * 250 * s, my + d[1] * 250 * s)
        out.append(line([a, b], 8 * s, color=c("bark")))
        px, py = -d[1], d[0]
        e = (mx + d[0] * 330 * s, my + d[1] * 330 * s)
        out.append(_poly([(b[0] + px * 20 * s, b[1] + py * 20 * s), (e[0] + px * 14 * s, e[1] + py * 14 * s),
                          (e[0] - px * 14 * s, e[1] - py * 14 * s), (b[0] - px * 20 * s, b[1] - py * 20 * s)], "bark", 5 * s))
    if "rope" in holds:
        d = (flip * hold_dir[0], hold_dir[1]) if hold_dir is not None else _unit(re, rh)
        a = (lh[0] - d[0] * 120 * s, lh[1] - d[1] * 120 * s)
        b = (rh[0] + d[0] * 520 * s, rh[1] + d[1] * 520 * s)
        out.append(line([a, rh, b], 9 * s, color="#b08a55"))
    if not head_load:
        mx, my = (lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2
        if "jar" in holds:
            out.append(path(f"M{mx - 25 * s},{my - 55 * s} L{mx + 25 * s},{my - 55 * s} L{mx + 20 * s},{my - 40 * s} "
                            f"Q{mx + 70 * s},{my} {mx + 25 * s},{my + 45 * s} L{mx - 25 * s},{my + 45 * s} "
                            f"Q{mx - 70 * s},{my} {mx - 20 * s},{my - 40 * s} Z", fill="clay", w=6 * s))
        if "basket" in holds:
            out.append(path(f"M{mx - 70 * s},{my - 30 * s} L{mx + 70 * s},{my - 30 * s} L{mx + 50 * s},{my + 45 * s} "
                            f"L{mx - 50 * s},{my + 45 * s} Z", fill="grain", w=6 * s))
        if "bundle" in holds:
            for i in range(3):
                out.append(rect(mx - 110 * s, my - 40 * s + i * 22 * s, 220 * s, 20 * s, "bark", rx=8 * s, w=5 * s))
    if "baby" in holds:
        mx, my = (lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2 - 15 * s
        out.append(f'<ellipse cx="{mx:.1f}" cy="{my:.1f}" rx="{48 * s:.1f}" ry="{28 * s:.1f}" fill="{c("ochre")}" '
                   f'stroke="{INK}" stroke-width="{6 * s:.1f}"/>')
        out.append(circle(mx + flip * 48 * s, my - 18 * s, 20 * s, fill="#fff", w=5 * s))
    if "shaker" in holds:
        out.append(rect(rh[0] - 18 * s, rh[1] - 60 * s, 36 * s, 80 * s, "#f3f5f6", rx=6 * s, w=5 * s))
        out.append(rect(rh[0] - 20 * s, rh[1] - 75 * s, 40 * s, 18 * s, "metal", rx=4 * s, w=5 * s))
    return "".join(out)
