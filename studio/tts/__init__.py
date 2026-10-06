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


def get_provider(cfg, lang: str = "en"):
    """Provider for a language: tts.provider_by_lang.<lang> wins over tts.provider."""
    name = (cfg.get_path("tts.provider_by_lang") or {}).get(lang) or cfg.get_path("tts.provider", "kokoro")
    if name == "kokoro" and lang not in KOKORO_LANGS:
        raise SystemExit(f"Kokoro '{lang}' dilini desteklemiyor. config → tts.provider_by_lang.{lang}: "
                         f"edge (ücretsiz, çevrimiçi) ya da elevenlabs (ücretli) seç.")
    if name == "kokoro":
        from .kokoro_tts import KokoroTTS
        return KokoroTTS(cfg, lang)
    if name == "elevenlabs":
        from .elevenlabs_tts import ElevenLabsTTS
        return ElevenLabsTTS(cfg)
    if name == "gemini":
        from .gemini_tts import GeminiTTS
        return GeminiTTS(cfg, lang)
    if name == "estimate":
        from .estimate_tts import EstimateTTS
        return EstimateTTS(cfg)
    if name == "edge":
        from .edge_tts_provider import EdgeTTS
        return EdgeTTS(cfg, lang)
    raise SystemExit(f"Bilinmeyen tts.provider: {name} (kokoro | edge | elevenlabs | gemini | estimate)")


KOKORO_LANGS = {"en", "es", "fr", "it", "pt", "hi", "ja", "zh"}
