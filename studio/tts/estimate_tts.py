"""Silent dry-run voice: produces silence of realistic length (~155 words/min).
Useful to preview pacing and images before spending anything on a real voice."""
from __future__ import annotations

import numpy as np

from . import Speech

SR = 24000
CHARS_PER_SEC = 14.5


class EstimateTTS:
    unit = "sentence"

    def __init__(self, cfg):
        pass

    def cache_key(self) -> str:
        return "estimate"

    def synthesize(self, text: str) -> Speech:
        dur = max(0.6, len(text) / CHARS_PER_SEC)
        n = int(dur * SR)
        starts = [i / CHARS_PER_SEC for i in range(len(text))]
        return Speech(np.zeros(n, dtype="float32"), SR, starts)
