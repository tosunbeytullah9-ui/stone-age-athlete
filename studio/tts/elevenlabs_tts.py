"""Paid voice: ElevenLabs. Uses the with-timestamps endpoint, so image timing is exact.

With model `eleven_v3` the narration can carry delivery tags ("[curious]", "[excited]", "[whispers]", "[pause]").
They are written in script.md, kept on the shot as `tone`, inserted here just before the words, and the returned
timing is mapped back onto the clean text (captions and image timing never see the tags).
"""
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
        # Delivery: lower stability + some style = livelier, more emphatic reading (questions, reveals).
        s = cfg.get_path("tts.elevenlabs.settings", {}) or {}
        self.settings = {k: s[k] for k in ("stability", "similarity_boost", "style", "use_speaker_boost", "speed")
                         if k in s}
        self.supports_tags = self.model.startswith("eleven_v3") and bool(cfg.get_path("tts.elevenlabs.tags", True))
        if self.model.startswith("eleven_v3") and "stability" in self.settings:
            # v3 only accepts 0.0 (Creative), 0.5 (Natural), 1.0 (Robust)
            self.settings["stability"] = min((0.0, 0.5, 1.0), key=lambda v: abs(v - float(self.settings["stability"])))

    def cache_key(self) -> str:
        extra = ",".join(f"{k}={v}" for k, v in sorted(self.settings.items()))
        return f"elevenlabs|{self.voice}|{self.model}" + (f"|{extra}" if extra else "")

    def synthesize(self, text: str, cues: list | None = None) -> Speech:
        sent, keep = tag_text(text, cues) if cues and self.supports_tags else (text, None)
        r = requests.post(
            API.format(voice=self.voice),
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": self.key, "Content-Type": "application/json"},
            json={"text": sent, "model_id": self.model, **({"voice_settings": self.settings} if self.settings else {})},
            timeout=180,
        )
        if r.status_code != 200:
            raise SystemExit(f"ElevenLabs hatası {r.status_code}: {r.text[:300]}")
        data = r.json()
        mp3 = base64.b64decode(data["audio_base64"])
        samples = _decode_mp3(mp3, 44100)
        align = data.get("alignment") or {}
        starts = align.get("character_start_times_seconds")
        if starts and keep is not None and len(starts) == len(sent):
            starts = [starts[i] for i in keep]      # drop the tag characters → timing of the clean text
        if starts and len(starts) != len(text):
            starts = None  # mismatch → fall back to proportional/whisper alignment
        return Speech(samples, 44100, starts)


def tag_text(text: str, cues: list) -> tuple[str, list[int]]:
    """Insert '[tag] ' at each cue offset. Returns (tagged text, index in tagged text of every clean character)."""
    at: dict[int, list[str]] = {}
    for pos, tag in cues:
        at.setdefault(max(0, min(int(pos), len(text))), []).append(str(tag))
    out, keep = "", []
    for i in range(len(text) + 1):
        for tag in at.get(i, []):
            out += f"[{tag}] "
        if i < len(text):
            keep.append(len(out))
            out += text[i]
    return out, keep


def _decode_mp3(data: bytes, sr: int) -> np.ndarray:
    out = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(sr), "pipe:1"],
        input=data, capture_output=True, check=True,
    ).stdout
    return np.frombuffer(io.BytesIO(out).getbuffer(), dtype="<f4").copy()
