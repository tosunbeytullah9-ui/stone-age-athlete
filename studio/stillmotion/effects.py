"""Effect library. Three families, all defined in picture space so they travel with the camera:

  warp      bends pixels (returns a displacement field):   sway ripple haze breathe swing drift boil shake
  light     changes colour/brightness of the source:        flicker glow pulse rays sweep fog
  particle  draws small moving things onto the source:      dust embers snow rain bubbles sparkle

Each effect is a class built once per clip (precomputes masks, noise, particle seeds) and called per frame.
Units: `amount` of warps is in pixels of the source picture (a 1920-px-wide picture: 3–8 px is subtle);
light `amount` is a 0..1 strength; particles take `count`, `size` (px) and `speed` (px/s).
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from .noise import Looping, field, wave1d
from .spec import bbox_px, box_of, envelope, mask

REGISTRY: dict[str, type] = {}


def effect(name: str, family: str):
    def deco(cls):
        cls.name, cls.family = name, family
        REGISTRY[name] = cls
        return cls
    return deco


class Base:
    family = "warp"

    def __init__(self, e: dict, h: int, w: int, depth, fps: int, total: float, seed: int, low: int = 4):
        self.e, self.h, self.w, self.fps, self.total = e, h, w, fps, total
        self.seed = int(e.get("seed", seed))
        self.depth = depth
        self.low = low

    def env(self, t: float) -> float:
        return envelope(self.e, t, self.total)

    def p(self, key, default):
        return type(default)(self.e.get(key, default)) if not isinstance(default, (list, tuple)) else self.e.get(key, default)


# =================================================================== warps (low-res displacement, image space)
class Warp(Base):
    family = "warp"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.lh, self.lw = max(8, self.h // self.low), max(8, self.w // self.low)
        self.m = mask(self.e, self.lh, self.lw, self.depth)
        ys = (np.arange(self.lh, dtype=np.float32) + 0.5) / self.lh
        xs = (np.arange(self.lw, dtype=np.float32) + 0.5) / self.lw
        self.X, self.Y = np.meshgrid(xs * self.w, ys * self.h)   # low-res grid in source pixels

    def anchor_weight(self) -> np.ndarray:
        """Grass/hair/cloth: the free end moves, the rooted end stays (anchor = the rooted side)."""
        x0, y0, x1, y1 = box_of(self.e)
        a = self.e.get("anchor", "none")
        ys = self.Y / self.h
        xs = self.X / self.w
        if a == "bottom":
            return np.clip((y1 - ys) / max(y1 - y0, 1e-3), 0, 1) ** 1.2
        if a == "top":
            return np.clip((ys - y0) / max(y1 - y0, 1e-3), 0, 1) ** 1.2
        if a == "left":
            return np.clip((xs - x0) / max(x1 - x0, 1e-3), 0, 1) ** 1.2
        if a == "right":
            return np.clip((x1 - xs) / max(x1 - x0, 1e-3), 0, 1) ** 1.2
        return np.ones_like(self.m)

    def disp(self, t: float):
        raise NotImplementedError


@effect("sway", "warp")
class Sway(Warp):
    """Grass, crops, leaves, hair, flags, cloth: rooted at `anchor` (default bottom), swaying with gusts."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.e.setdefault("anchor", "bottom")
        cells = int(self.e.get("detail", 8))
        self.n = Looping(self.lh, self.lw, cells, self.seed, float(self.e.get("speed", 0.35)))
        self.n2 = Looping(self.lh, self.lw, cells, self.seed + 9, float(self.e.get("speed", 0.35)) * 1.3)
        self.wm = self.m * self.anchor_weight()

    def disp(self, t):
        a = float(self.e.get("amount", 5)) * self.env(t)
        gust = 0.75 + 0.25 * wave1d(t, self.seed, 0.12)
        d = self.e.get("dir", "x")
        dx = a * gust * self.wm * self.n.at(t) if d in ("x", "xy") else 0
        dy = a * 0.5 * gust * self.wm * self.n2.at(t) if d in ("y", "xy") else 0
        return dx, dy


@effect("ripple", "warp")
class Ripple(Warp):
    """Water surface: horizontal bands that travel (lakes, sea, a drink). wavelength = fraction of picture height."""

    def disp(self, t):
        a = float(self.e.get("amount", 3)) * self.env(t)
        lam = float(self.e.get("wavelength", 0.035)) * self.h
        sp = float(self.e.get("speed", 0.5))
        ph = 2 * math.pi * (self.Y / lam - sp * t) + 0.002 * self.X
        return 0.6 * a * self.m * np.cos(ph * 0.73 + 1.1), a * self.m * np.sin(ph)


@effect("haze", "warp")
class Haze(Warp):
    """Heat shimmer above fire, hot ground, breath in cold air: fine fast wobble."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        sp = float(self.e.get("speed", 1.2))
        self.nx = Looping(self.lh, self.lw, int(self.e.get("detail", 22)), self.seed, sp)
        self.ny = Looping(self.lh, self.lw, int(self.e.get("detail", 22)), self.seed + 5, sp * 1.1)

    def disp(self, t):
        a = float(self.e.get("amount", 2.5)) * self.env(t)
        return a * self.m * self.nx.at(t), a * 0.6 * self.m * self.ny.at(t)


@effect("breathe", "warp")
class Breathe(Warp):
    """A body or object that gently swells and settles (chest breathing, a heart, a lung, a resting animal).
    amount = relative scale (0.012 = 1.2 %); anchor bottom keeps feet planted."""

    def disp(self, t):
        a = float(self.e.get("amount", 0.012)) * self.env(t)
        per = float(self.e.get("period", 4.0))
        s = a * (0.5 - 0.5 * math.cos(2 * math.pi * t / per))
        x0, y0, x1, y1 = box_of(self.e)
        cx = (x0 + x1) / 2 * self.w
        cy = (y1 if self.e.get("anchor", "bottom") == "bottom" else (y0 + y1) / 2) * self.h
        return (-(self.X - cx) * s * 0.45 * self.m, -(self.Y - cy) * s * self.m)


@effect("swing", "warp")
class Swing(Warp):
    """Pendulum rotation of a part around a pivot (a raised arm, a hanging lamp, a branch). angle in degrees."""

    def disp(self, t):
        ang = math.radians(float(self.e.get("angle", 2.0))) * self.env(t)
        per = float(self.e.get("period", 3.0))
        th = ang * math.sin(2 * math.pi * t / per + float(self.e.get("phase", 0)))
        x0, y0, x1, y1 = box_of(self.e)
        px, py = self.e.get("pivot", ((x0 + x1) / 2, y1))
        px, py = px * self.w, py * self.h
        c, s = math.cos(-th), math.sin(-th)
        rx, ry = self.X - px, self.Y - py
        return ((c * rx - s * ry - rx) * self.m, (s * rx + c * ry - ry) * self.m)


@effect("drift", "warp")
class Drift(Warp):
    """Slow travel of soft things: clouds, fog banks, smoke, a river's surface. speed px/s, angle degrees
    (0 = to the right). Keep it small (≤ 15 px/s) and the box soft."""

    def disp(self, t):
        sp = float(self.e.get("speed", 8.0)) * self.env(t)
        ang = math.radians(float(self.e.get("angle", 0)))
        return (-sp * t * math.cos(ang) * self.m, -sp * t * math.sin(ang) * self.m)


@effect("boil", "warp")
class Boil(Warp):
    """Hand-drawn 'line boil': ink lines redraw slightly a few times a second, like cel animation on twos/threes.
    For doodle/ink/sketch styles. amount ≈ 1–1.5 px, rate = new drawings per second."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.cache = {}

    def disp(self, t):
        rate = float(self.e.get("rate", 8))
        k = int(t * rate)
        if k not in self.cache:
            self.cache.clear()
            cells = int(self.e.get("detail", 60))
            self.cache[k] = (field(self.lh, self.lw, cells, self.seed * 1000 + 2 * k),
                             field(self.lh, self.lw, cells, self.seed * 1000 + 2 * k + 1))
        fx, fy = self.cache[k]
        a = float(self.e.get("amount", 1.2)) * self.env(t)
        return a * self.m * fx, a * self.m * fy


@effect("shake", "warp")
class Shake(Warp):
    """Impact jolt at given seconds (a stamp, a punch, a thunderclap): at: [1.2, 3.5]."""

    def disp(self, t):
        a = float(self.e.get("amount", 10))
        dec = float(self.e.get("decay", 0.35))
        dx = dy = 0.0
        for k, at in enumerate(self.e.get("at", [0.0])):
            u = t - float(at)
            if 0 <= u < dec * 4:
                g = a * math.exp(-u / dec)
                dx += g * math.sin(2 * math.pi * 11 * u + k)
                dy += g * 0.7 * math.sin(2 * math.pi * 13 * u + 2 * k)
        return dx * self.m, dy * self.m


# =================================================================== light (on the source frame, float32 0..255)
class Light(Base):
    family = "light"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.x0, self.y0, self.x1, self.y1 = bbox_px(self.e, self.h, self.w)
        ch, cw = self.y1 - self.y0, self.x1 - self.x0
        full = mask(self.e, self.h // 2, self.w // 2, self.depth)
        full = cv2.resize(full, (self.w, self.h), interpolation=cv2.INTER_LINEAR)
        self.m = full[self.y0:self.y1, self.x0:self.x1][..., None]
        self.ch, self.cw = ch, cw

    def color(self, key, default):
        c = self.e.get(key, default)
        if isinstance(c, str):
            c = c.lstrip("#")
            c = [int(c[i:i + 2], 16) for i in (0, 2, 4)]
        return np.array(c, np.float32)

    def region(self, f):
        # apply_region passes the box itself; apply(full_frame) passes the whole picture
        if f.shape[0] == self.ch and f.shape[1] == self.cw and getattr(self, "_reg", False):
            return f
        return f[self.y0:self.y1, self.x0:self.x1]

    def apply_region(self, reg, t):
        self._reg = True
        try:
            self.apply(reg, t)
        finally:
            self._reg = False

    @staticmethod
    def screen(base, add):
        return 255.0 - (255.0 - base) * (1.0 - np.clip(add, 0, 255) / 255.0)

    def composite(self, r, alpha, col):
        """Blend a layer of colour `col` with coverage `alpha` (h×w×1, 0..1) into region r.
        blend: screen (light things: sparks, glints, light) | multiply (ink/dark things on paper) | normal."""
        a = np.clip(alpha, 0, 1)
        mode = self.e.get("blend", "screen")
        if mode == "multiply":
            r *= 1.0 - a * (1.0 - col / 255.0)
        elif mode == "normal":
            r[...] = r * (1 - a) + col * a
        else:
            r[...] = 255.0 - (255.0 - r) * (1.0 - a * col / 255.0)

    def apply(self, f, t):
        raise NotImplementedError


@effect("flicker", "light")
class Flicker(Light):
    """Firelight, candles, torches, lightning bugs, a faulty bulb: brightness and warmth that dance."""

    def apply(self, f, t):
        a = float(self.e.get("amount", 0.18)) * self.env(t)
        sp = float(self.e.get("speed", 1.8))
        g = wave1d(t, self.seed, sp) * 0.7 + wave1d(t, self.seed + 3, sp * 2.9) * 0.3
        warm = self.color("color", [255, 170, 90]) / 255.0
        r = self.region(f)
        k = self.m * a * g
        r *= 1.0 + k * warm
        np.clip(r, 0, 255, out=r)


@effect("glow", "light")
class Glow(Light):
    """A soft coloured glow that breathes: a sore joint glowing red, a magic light, a lit window, embers' heart.
    period 0 = steady."""

    def apply(self, f, t):
        a = float(self.e.get("amount", 0.55)) * self.env(t)
        per = float(self.e.get("period", 1.8))
        pulse = 1.0 if per <= 0 else 0.6 + 0.4 * math.sin(2 * math.pi * t / per)
        col = self.color("color", [255, 80, 40])
        r = self.region(f)
        self.composite(r, self.m * a * pulse, col)


@effect("pulse", "light")
class Pulse(Light):
    """Brightness that rises and falls (attention on a detail, a heartbeat, a warning light). amount 0..1."""

    def apply(self, f, t):
        a = float(self.e.get("amount", 0.15)) * self.env(t)
        per = float(self.e.get("period", 1.2))
        s = math.sin(2 * math.pi * t / per)
        s = s ** 7 if self.e.get("beat") else s        # beat: short thump, long rest
        r = self.region(f)
        r *= 1.0 + self.m * a * s
        np.clip(r, 0, 255, out=r)


@effect("rays", "light")
class Rays(Light):
    """God rays: soft shafts of light through a window, trees or water, slowly shifting. angle = degrees from
    vertical (positive leans right)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        rng = np.random.default_rng(self.seed)
        n = 900
        prof = rng.uniform(0, 1, n).astype(np.float32)
        prof = cv2.GaussianBlur(prof[None, :], (0, 0), 6)[0]
        prof = (prof - prof.min()) / max(np.ptp(prof), 1e-6)
        self.prof = prof ** 2.2
        ang = math.radians(float(self.e.get("angle", 20)))
        ys, xs = np.mgrid[0:self.ch, 0:self.cw].astype(np.float32)
        self.u = (xs * math.cos(ang) - ys * math.sin(ang)) / max(self.cw, 1) * 220 + 300
        self.fade = (1.0 - ys / max(self.ch, 1) * 0.6)[..., None]

    def apply(self, f, t):
        a = float(self.e.get("amount", 0.28)) * self.env(t)
        shift = float(self.e.get("speed", 4.0)) * t
        idx = np.clip(self.u + shift, 0, len(self.prof) - 1)
        lit = np.interp(idx, np.arange(len(self.prof)), self.prof).astype(np.float32)[..., None]
        col = self.color("color", [255, 236, 190])
        r = self.region(f)
        self.composite(r, lit * self.fade * self.m * a, col)


@effect("sweep", "light")
class Sweep(Light):
    """One sheen that crosses the box once between from/to (a medal, a blade, wet rock, a reveal)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        ang = math.radians(float(self.e.get("angle", 20)))
        ys, xs = np.mgrid[0:self.ch, 0:self.cw].astype(np.float32)
        u = xs + ys * math.tan(ang)
        self.u = (u - u.min()) / max(np.ptp(u), 1)

    def apply(self, f, t):
        a0, b0 = float(self.e.get("from", 0)), float(self.e.get("to", min(self.total, 1.6)))
        if not (a0 <= t <= b0):
            return
        p = (t - a0) / max(b0 - a0, 1e-3)
        wdt = float(self.e.get("width", 0.12))
        band = np.exp(-((self.u - (-wdt + p * (1 + 2 * wdt))) / wdt) ** 2)[..., None]
        col = self.color("color", [255, 248, 225])
        r = self.region(f)
        self.composite(r, band * self.m * float(self.e.get("amount", 0.45)), col)


@effect("fog", "light")
class Fog(Light):
    """Mist, dust clouds, steam, spray, underwater haze: a soft veil whose density drifts."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        lh, lw = max(8, self.ch // 8), max(8, self.cw // 8)
        self.n = Looping(lh, lw, int(self.e.get("detail", 5)), self.seed, float(self.e.get("speed", 0.08)))

    def apply(self, f, t):
        a = float(self.e.get("amount", 0.22)) * self.env(t)
        n = cv2.resize(self.n.at(t), (self.cw, self.ch), interpolation=cv2.INTER_CUBIC)[..., None]
        dens = np.clip(0.55 + 0.45 * n, 0, 1) * self.m * a
        col = self.color("color", [236, 228, 214])
        r = self.region(f)
        r[...] = r * (1 - dens) + col * dens


# =================================================================== particles
class Particles(Light):
    family = "particle"
    defaults = dict(count=40, size=3.0, speed=20.0, opacity=0.6, color=[255, 240, 210])

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        for key, v in self.defaults.items():
            self.e.setdefault(key, v)
        rng = np.random.default_rng(self.seed)
        n = int(self.e["count"])
        self.n = n
        self.px = rng.uniform(0, 1, n)
        self.py = rng.uniform(0, 1, n)
        self.sz = float(self.e["size"]) * rng.uniform(0.6, 1.4, n)
        self.sp = float(self.e["speed"]) * rng.uniform(0.6, 1.4, n)
        self.ph = rng.uniform(0, 2 * math.pi, n)
        self.dirs = rng.uniform(0, 2 * math.pi, n)
        self.col = self.color("color", self.defaults["color"])
        self.sprites = {}

    def _blend_layer(self, f, layer: np.ndarray, env: float) -> None:
        ys, xs = np.nonzero(layer)
        if not len(ys):
            return
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        lay = layer[y0:y1, x0:x1].astype(np.float32)[..., None] / 255.0
        rgn = self.region(f)[y0:y1, x0:x1]
        self.composite(rgn, lay * self.m[y0:y1, x0:x1] * float(self.e["opacity"]) * env, self.col)

    def sprite(self, r: float) -> np.ndarray:
        key = round(r * 2) / 2
        if key not in self.sprites:
            s = int(math.ceil(key * 3)) * 2 + 1
            y, x = np.mgrid[0:s, 0:s].astype(np.float32) - s // 2
            self.sprites[key] = np.exp(-(x * x + y * y) / (2 * (key * 0.8) ** 2))
        return self.sprites[key]

    def positions(self, t):
        """→ x, y (pixels inside the region), alpha 0..1"""
        raise NotImplementedError

    def apply(self, f, t):
        """Sprites are blended patch by patch (cheap even when the region is the whole picture)."""
        env = self.env(t)
        if env <= 0:
            return
        x, y, al = self.positions(t)
        a = float(self.e["opacity"]) * env
        r = self.region(f)
        col = self.col
        mode = self.e.get("blend", "screen")
        for i in range(self.n):
            if al[i] <= 0.01:
                continue
            sp = self.sprite(self.sz[i])
            s = sp.shape[0]
            cx, cy = int(x[i]) - s // 2, int(y[i]) - s // 2
            x0, y0 = max(cx, 0), max(cy, 0)
            x1, y1 = min(cx + s, self.cw), min(cy + s, self.ch)
            if x0 >= x1 or y0 >= y1:
                continue
            alpha = (sp[y0 - cy:y1 - cy, x0 - cx:x1 - cx] * (al[i] * a))[..., None] * self.m[y0:y1, x0:x1]
            patch = r[y0:y1, x0:x1]
            if mode == "multiply":
                patch *= 1.0 - alpha * (1.0 - col / 255.0)
            else:
                patch[...] = 255.0 - (255.0 - patch) * (1.0 - alpha * col / 255.0)


@effect("dust", "particle")
class Dust(Particles):
    """Motes floating in a sunbeam or a dusty room; plankton underwater (blue-white colour)."""
    defaults = dict(count=50, size=2.6, speed=10.0, opacity=0.55, color=[255, 242, 214])

    def positions(self, t):
        x = (self.px * self.cw + np.cos(self.dirs) * self.sp * t + 6 * np.sin(0.7 * t + self.ph)) % self.cw
        y = (self.py * self.ch + np.sin(self.dirs) * self.sp * t * 0.6 + 6 * np.cos(0.5 * t + self.ph)) % self.ch
        al = 0.55 + 0.45 * np.sin(1.3 * t + self.ph)
        return x, y, al


@effect("embers", "particle")
class Embers(Particles):
    """Sparks rising from a fire or a forge, wobbling and fading as they climb."""
    defaults = dict(count=35, size=2.4, speed=70.0, opacity=0.9, color=[255, 150, 60])

    def positions(self, t):
        span = self.ch * 1.1
        prog = ((self.py * span + self.sp * t) % span) / span          # 0 at bottom → 1 at top
        y = self.ch * (1 - prog)
        x = (self.px * self.cw + 14 * np.sin(2.1 * t + self.ph) + 30 * prog * np.cos(self.ph)) % self.cw
        al = np.clip(1.2 - prog * 1.3, 0, 1) * (0.7 + 0.3 * np.sin(9 * t + self.ph))
        return x, y, al


@effect("snow", "particle")
class Snow(Particles):
    """Falling snow or ash."""
    defaults = dict(count=70, size=3.0, speed=45.0, opacity=0.85, color=[250, 250, 255])

    def positions(self, t):
        y = (self.py * self.ch + self.sp * t) % self.ch
        x = (self.px * self.cw + 18 * np.sin(0.9 * t + self.ph)) % self.cw
        return x, y, np.ones(self.n)


@effect("bubbles", "particle")
class Bubbles(Particles):
    """Air bubbles rising underwater (divers, a drink, a pot)."""
    defaults = dict(count=24, size=5.0, speed=55.0, opacity=0.7, color=[235, 248, 255])

    def apply(self, f, t):
        env = self.env(t)
        if env <= 0:
            return
        layer = np.zeros((self.ch, self.cw), np.uint8)
        y = (self.py * self.ch - self.sp * t) % self.ch
        x = (self.px * self.cw + 8 * np.sin(2.4 * t + self.ph)) % self.cw
        for i in range(self.n):
            r = max(2, int(self.sz[i]))
            cv2.circle(layer, (int(x[i] * 4), int(y[i] * 4)), r * 4, 255, 4 if r > 3 else 3, cv2.LINE_AA, shift=2)
            cv2.circle(layer, (int((x[i] - r * 0.35) * 4), int((y[i] - r * 0.35) * 4)), max(1, r // 3) * 4, 255, -1,
                       cv2.LINE_AA, shift=2)
        self._blend_layer(f, layer, env)


@effect("rain", "particle")
class Rain(Particles):
    """Rain streaks (angle in degrees from vertical). For drawn styles prefer a light opacity."""
    defaults = dict(count=140, size=1.0, speed=1100.0, opacity=0.35, color=[230, 235, 245])

    def apply(self, f, t):
        env = self.env(t)
        if env <= 0:
            return
        ang = math.radians(float(self.e.get("angle", 12)))
        ln = float(self.e.get("length", 38))
        layer = np.zeros((self.ch, self.cw), np.uint8)
        span = self.ch + ln
        y = (self.py * span + self.sp * t) % span - ln
        x = (self.px * self.cw - (y + ln) * math.tan(ang)) % self.cw
        dx, dy = ln * math.sin(ang), ln * math.cos(ang)
        for i in range(self.n):
            cv2.line(layer, (int(x[i]), int(y[i])), (int(x[i] + dx), int(y[i] + dy)), 255, 1, cv2.LINE_AA)
        self._blend_layer(f, layer, env)


@effect("sparkle", "particle")
class Sparkle(Particles):
    """Twinkling glints (wet stones, stars, jewels, a fresh idea). Each glint flashes now and then."""
    defaults = dict(count=14, size=5.0, speed=0.0, opacity=0.9, color=[255, 252, 235])

    def apply(self, f, t):
        env = self.env(t)
        if env <= 0:
            return
        layer = np.zeros((self.ch, self.cw), np.float32)
        for i in range(self.n):
            ph = (t * 0.45 + self.ph[i] / (2 * math.pi)) % 1.0
            a = max(0.0, math.sin(ph * math.pi * 3)) ** 3 if ph < 0.34 else 0.0
            if a < 0.02:
                continue
            cx, cy = int(self.px[i] * self.cw), int(self.py[i] * self.ch)
            r = int(self.sz[i] * 3 * a) + 2
            for (ux, uy) in ((1, 0), (0, 1)):
                cv2.line(layer, (cx - ux * r, cy - uy * r), (cx + ux * r, cy + uy * r), float(a), 2, cv2.LINE_AA)
            cv2.circle(layer, (cx, cy), max(1, r // 4), float(a), -1, cv2.LINE_AA)
        layer = cv2.GaussianBlur(layer, (0, 0), 1.2)
        self._blend_layer(f, (np.clip(layer, 0, 1) * 255).astype(np.uint8), env)
