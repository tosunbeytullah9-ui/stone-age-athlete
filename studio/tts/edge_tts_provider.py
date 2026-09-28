"""Free online voice via Microsoft Edge's read-aloud service (pip install edge-tts).

Many languages including Turkish (tr-TR-AhmetNeural, tr-TR-EmelNeural). Returns word boundaries,
so image timing is exact. Note: this uses an unofficial client of a free consumer service; for
commercial channels at scale prefer ElevenLabs or an official Azure Speech key.
"""
from __future__ import annotations

import asyncio

from . import Speech
from .elevenlabs_tts import _decode_mp3

DEFAULT_VOICES = {"en": "en-US-GuyNeural", "tr": "tr-TR-AhmetNeural", "es": "es-ES-AlvaroNeural",
                  "pt": "pt-BR-AntonioNeural", "de": "de-DE-ConradNeural", "fr": "fr-FR-HenriNeural"}


class EdgeTTS:
    unit = "sentence"

    def __init__(self, cfg, lang: str):
        import importlib.util
        if importlib.util.find_spec("edge_tts") is None:
            raise SystemExit("edge-tts kurulu değil: pip install edge-tts")
        self.voice = (cfg.get_path("tts.edge.voice_by_lang") or {}).get(lang) or DEFAULT_VOICES.get(lang)
        if not self.voice:
            raise SystemExit(f"config → tts.edge.voice_by_lang.{lang} boş")
        self.rate = cfg.get_path("tts.edge.rate", "+0%")

    def cache_key(self) -> str:
        return f"edge|{self.voice}|{self.rate}"

    async def _run(self, text: str):
        import edge_tts
        com = edge_tts.Communicate(text, self.voice, rate=self.rate, boundary="WordBoundary")
        audio, words = bytearray(), []
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append((chunk["text"], chunk["offset"] / 1e7))
        return bytes(audio), words

    def synthesize(self, text: str) -> Speech:
        mp3, words = asyncio.run(self._run(text))
        samples = _decode_mp3(mp3, 24000)
        starts = [0.0] * len(text)
        pos, t = 0, 0.0
        for word, start in words:
            i = text.find(word, pos)
            if i < 0:
                continue
            for k in range(pos, i + len(word)):
                starts[k] = t if k < i else start
            t, pos = start, i + len(word)
        for k in range(pos, len(text)):
            starts[k] = t
        return Speech(samples, 24000, starts if words else None)
