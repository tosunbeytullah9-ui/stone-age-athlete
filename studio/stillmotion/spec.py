"""Motion spec: what moves in a still picture.

    camera:                       # one continuous move over the whole clip
      move: in                    # in | out | left | right | up | down | drift | orbit | none
      amount: 0.07                # zoom/pan size (0.07 = 7 %)
      parallax: 0.6               # 0..1 — depth-based 2.5D strength (0 = flat move)
      focus: [0.5, 0.45]          # point the zoom heads to (normalized image coords)
      ease: smooth                # smooth | linear | out
    fx:                           # local effects, all optional and combinable
      - {type: sway, box: [0, 0.62, 1, 1], amount: 5, anchor: bottom}
      - {type: embers, box: [0.42, 0.55, 0.62, 0.85], count: 40}
    seed: 7

Every effect accepts: box [x0, y0, x1, y1] (0..1 of the picture; default whole picture), shape ellipse|rect,
feather (0..0.5), depth [near_lo, near_hi] (keep only pixels in that depth band, 1 = near), from/to (seconds),
ramp (fade in/out seconds).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

MOVES = ("in", "out", "left", "right", "up", "down", "drift", "orbit", "none")


@dataclass
class Camera:
    move: str = "in"
    amount: float = 0.07
    parallax: float = 0.0
    focus: tuple[float, float] = (0.5, 0.5)
    ease: str = "smooth"


@dataclass
class Spec:
    camera: Camera = field(default_factory=Camera)
    fx: list[dict] = field(default_factory=list)
    seed: int = 1


def parse(d: dict | None, defaults: dict | None = None) -> Spec:
    """dict (from YAML/JSON) → Spec. `defaults` fills a missing camera (e.g. from a style preset)."""
    d = dict(d or {})
    base = dict((defaults or {}).get("camera") or {})
    cam = d.get("camera")
    if isinstance(cam, str):
        cam = {"move": cam}
    base.update(cam or {})
    move = str(base.get("move", "in"))
    if move not in MOVES:
        raise ValueError(f"camera.move '{move}' bilinmiyor; seçenekler: {', '.join(MOVES)}")
    camera = Camera(move=move, amount=float(base.get("amount", 0.07)), parallax=float(base.get("parallax", 0.0)),
                    focus=tuple(base.get("focus", (0.5, 0.5))), ease=str(base.get("ease", "smooth")))
    fx = list(d.get("fx") or [])
    if defaults and d.get("inherit_fx", True):
        fx = list(defaults.get("fx") or []) + fx
    from .effects import REGISTRY
    for e in fx:
        if not isinstance(e, dict) or e.get("type") not in REGISTRY:
            raise ValueError(f"bilinmeyen efekt: {e!r}; seçenekler: {', '.join(sorted(REGISTRY))}")
    return Spec(camera=camera, fx=fx, seed=int(d.get("seed", (defaults or {}).get("seed", 1))))


# ---------------------------------------------------------------- time
def ease(p: float, kind: str = "smooth") -> float:
    p = min(1.0, max(0.0, p))
    if kind == "linear":
        return p
    if kind == "out":
        return 1 - (1 - p) ** 2
    return p * p * (3 - 2 * p)


def envelope(e: dict, t: float, total: float) -> float:
    """0..1 strength of an effect at time t (fades in at `from`, out at `to`)."""
    a = float(e.get("from", 0.0))
    b = float(e["to"]) if e.get("to") is not None else math.inf    # open-ended: keeps going past the clip end
    r = float(e.get("ramp", 0.5))
    if t < a or t > b:
        return 0.0
    k = 1.0
    if r > 0:
        if a > 0:
            k = min(k, (t - a) / r)
        if b < math.inf:
            k = min(k, (b - t) / r)
    return max(0.0, min(1.0, k))


# ---------------------------------------------------------------- masks
def box_of(e: dict) -> tuple[float, float, float, float]:
    b = e.get("box") or (0, 0, 1, 1)
    x0, y0, x1, y1 = (float(v) for v in b)
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def mask(e: dict, h: int, w: int, depth: np.ndarray | None = None) -> np.ndarray:
    """Soft mask float32 h×w in [0,1] for an effect, in picture space."""
    x0, y0, x1, y1 = box_of(e)
    shape = e.get("shape") or ("rect" if (x1 - x0 > 0.95 or y1 - y0 > 0.95) else "ellipse")
    feather = float(e.get("feather", 0.25))
    ys = (np.arange(h, dtype=np.float32) + 0.5) / h
    xs = (np.arange(w, dtype=np.float32) + 0.5) / w
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = max((x1 - x0) / 2, 1e-4), max((y1 - y0) / 2, 1e-4)
    if shape == "rect":
        # distance inside the rectangle, per axis; picture edges never fade (a box touching the edge stays full)
        def axis(v, lo, hi, r):
            f = max(feather * 2 * r, 1e-4)
            m = np.ones_like(v)
            if lo > 0.001:
                m = np.minimum(m, np.clip((v - lo) / f, 0, 1))
            if hi < 0.999:
                m = np.minimum(m, np.clip((hi - v) / f, 0, 1))
            return m
        m = axis(ys, y0, y1, ry)[:, None] * axis(xs, x0, x1, rx)[None, :]
    else:
        dx = (xs[None, :] - cx) / rx
        dy = (ys[:, None] - cy) / ry
        r = np.sqrt(dx * dx + dy * dy)
        f = max(feather, 1e-3)
        m = np.clip((1.0 - r) / f, 0, 1)
    m = m * m * (3 - 2 * m)
    band = e.get("depth")
    if band is not None and depth is not None:
        lo, hi = float(band[0]), float(band[1])
        d = cv2.resize(depth, (w, h), interpolation=cv2.INTER_LINEAR) if depth.shape != (h, w) else depth
        soft = 0.06
        m = m * np.clip((d - lo) / soft + 1, 0, 1) * np.clip((hi - d) / soft + 1, 0, 1)
    return m.astype(np.float32)


def bbox_px(e: dict, h: int, w: int, pad: float = 0.0) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box_of(e)
    return (max(0, int(math.floor((x0 - pad) * w))), max(0, int(math.floor((y0 - pad) * h))),
            min(w, int(math.ceil((x1 + pad) * w))), min(h, int(math.ceil((y1 + pad) * h))))
