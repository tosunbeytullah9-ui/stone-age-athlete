"""Text-to-speech providers. All return float32 mono samples at their own sample rate.

A provider has:
  unit:  "sentence" or "paragraph"  — how much text it receives per call
  synthesize(text) -> Speech(samples, sample_rate, char_starts|None)
char_starts (optional): start time in seconds of every character of `text`,
which gives exact image timing without a separate alignment step.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Speech:
    samples: np.ndarray
    sample_rate: int
    char_starts: list[float] | None = None


def get_provider(cfg):
    name = cfg.get_path("tts.provider", "kokoro")
    if name == "kokoro":
        from .kokoro_tts import KokoroTTS
        return KokoroTTS(cfg)
    if name == "elevenlabs":
        from .elevenlabs_tts import ElevenLabsTTS
        return ElevenLabsTTS(cfg)
    if name == "estimate":
        from .estimate_tts import EstimateTTS
        return EstimateTTS(cfg)
    raise SystemExit(f"Bilinmeyen tts.provider: {name} (kokoro | elevenlabs | estimate)")
