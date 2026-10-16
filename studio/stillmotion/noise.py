"""Small deterministic noise helpers (seeded, no global state)."""
from __future__ import annotations

import math

import cv2
import numpy as np


def field(h: int, w: int, cells: int, seed: int) -> np.ndarray:
    """Smooth value noise in [-1, 1] at h×w: random grid of `cells` across the width, cubic upscaled."""
    rng = np.random.default_rng(seed)
    gw = max(2, cells)
    gh = max(2, int(round(cells * h / max(w, 1))))
    g = rng.uniform(-1, 1, (gh + 2, gw + 2)).astype(np.float32)
    up = cv2.resize(g, (w + 2 * w // gw, h + 2 * h // gh), interpolation=cv2.INTER_CUBIC)
    oy, ox = h // gh, w // gw
    return np.clip(up[oy:oy + h, ox:ox + w], -1.5, 1.5) / 1.5


class Looping:
    """Animated noise without per-frame generation: n(t) = A·cos(ωt) + B·sin(ωt) (+ a slower second octave)."""

    def __init__(self, h: int, w: int, cells: int, seed: int, speed: float = 0.3):
        self.a = field(h, w, cells, seed)
        self.b = field(h, w, cells, seed + 1)
        self.c = field(h, w, max(2, cells // 2), seed + 2)
        self.d = field(h, w, max(2, cells // 2), seed + 3)
        self.speed = speed

    def at(self, t: float) -> np.ndarray:
        w1 = 2 * math.pi * self.speed * t
        w2 = 2 * math.pi * self.speed * 0.43 * t + 1.3
        return (0.7 * (self.a * math.cos(w1) + self.b * math.sin(w1))
                + 0.3 * (self.c * math.cos(w2) + self.d * math.sin(w2)))


def wave1d(t: float, seed: int, speed: float = 1.0) -> float:
    """Smooth 1-D noise in about [-1, 1] (sum of incommensurate sines with seeded phases)."""
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 2 * math.pi, 4)
    fr = np.array([1.0, 2.17, 3.71, 5.93]) * speed
    am = np.array([0.5, 0.25, 0.15, 0.1])
    return float(np.sum(am * np.sin(2 * math.pi * fr * t + ph)) / 0.75)
