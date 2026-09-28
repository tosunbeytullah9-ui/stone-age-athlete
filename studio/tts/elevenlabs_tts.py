"""Paid voice: ElevenLabs. Uses the with-timestamps endpoint, so image timing is exact."""
from __future__ import annotations

import base64
import io
import subprocess

import numpy as np
import requests

from ..config import secret
from . import Speech

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps"


class ElevenLabsTTS:
    unit = "paragraph"   # longer text = more natural delivery

    def __init__(self, cfg):
        self.key = secret("ELEVENLABS_API_KEY")
        self.voice = cfg.get_path("tts.elevenlabs.voice_id", "")
        if not self.voice:
            raise SystemExit("config.yaml → tts.elevenlabs.voice_id boş.")
        self.model = cfg.get_path("tts.elevenlabs.model", "eleven_multilingual_v2")

    def cache_key(self) -> str:
        return f"elevenlabs|{self.voice}|{self.model}"

    def synthesize(self, text: str) -> Speech:
        r = requests.post(
            API.format(voice=self.voice),
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": self.key, "Content-Type": "application/json"},
            json={"text": text, "model_id": self.model},
            timeout=180,
        )
        if r.status_code != 200:
            raise SystemExit(f"ElevenLabs hatası {r.status_code}: {r.text[:300]}")
        data = r.json()
        mp3 = base64.b64decode(data["audio_base64"])
        samples = _decode_mp3(mp3, 44100)
        align = data.get("alignment") or {}
        starts = align.get("character_start_times_seconds")
        if starts and len(starts) != len(text):
            starts = None  # mismatch → fall back to proportional/whisper alignment
        return Speech(samples, 44100, starts)


def _decode_mp3(data: bytes, sr: int) -> np.ndarray:
    out = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(sr), "pipe:1"],
        input=data, capture_output=True, check=True,
    ).stdout
    return np.frombuffer(io.BytesIO(out).getbuffer(), dtype="<f4").copy()
