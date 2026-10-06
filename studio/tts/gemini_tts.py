"""Paid (cheap) voice: Google Gemini TTS via the official Gemini API, same GEMINI_API_KEY as the images.

Delivery is directed in plain English (tts.gemini.style): the style text is NOT spoken, it steers the read
(e.g. rising curiosity on questions, a pause before a reveal). No per-character timestamps, so image timing
comes from the align step (whisper when installed, otherwise proportional).

Tries the current Interactions API model first (tts.gemini.model) and falls back to the classic
generateContent speech format (tts.gemini.fallback_model) if the first call is rejected.

Quick voice audition (writes WAVs you can play):
    python -m studio.tts.gemini_tts Leda Zephyr Laomedeia
"""
from __future__ import annotations

import base64
import io
import re
import sys
import time
import wave

import numpy as np
import requests

from ..config import secret
from . import Speech

BASE = "https://generativelanguage.googleapis.com/v1beta"
SR = 24000
DEFAULT_STYLE = ("An energetic young woman presenting a popular science YouTube channel. Warm, curious and "
                 "confident. Let questions rise with genuine curiosity, lean into surprising numbers, and take a "
                 "short pause before each reveal. Natural conversational pace, never shouting, never robotic.")


class GeminiTTS:
    unit = "paragraph"   # one call per paragraph keeps the tone consistent inside a thought

    def __init__(self, cfg, lang: str = "en"):
        self.key = secret("GEMINI_API_KEY")
        g = cfg.get_path("tts.gemini", {}) or {}
        self.model = g.get("model", "gemini-3.8-flash-tts")
        self.fallback = g.get("fallback_model", "gemini-3.1-flash-tts-preview")
        self.voice = (g.get("voice_by_lang") or {}).get(lang) or g.get("voice", "Leda")
        self.style = (g.get("style") or DEFAULT_STYLE).strip()
        self.retries = int(g.get("retries", 4))
        self._use_fallback = False

    def cache_key(self) -> str:
        return f"gemini|{self.model}|{self.voice}|{self.style}"

    # --- the two request formats -------------------------------------------------------------------
    def _interactions(self, text: str) -> requests.Response:
        body = {
            "model": self.model,
            "input": [{"type": "user_input", "content": [{
                "type": "text", "text": text,
                "annotations": [{"type": "speech_metadata", "style": self.style}]}]}],
            "response_format": {"type": "audio", "mime_type": "audio/wav", "sample_rate": SR},
            "generation_config": {"speech_config": [{"voice": self.voice}]},
        }
        return requests.post(f"{BASE}/interactions", json=body, timeout=300, headers=self._headers())

    def _generate_content(self, text: str) -> requests.Response:
        body = {
            "contents": [{"parts": [{"text": f"{self.style}\n\nRead this aloud:\n{text}"}]}],
            "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": self.voice}}}},
        }
        return requests.post(f"{BASE}/models/{self.fallback}:generateContent", json=body, timeout=300,
                             headers=self._headers())

    def _headers(self) -> dict:
        return {"x-goog-api-key": self.key, "Content-Type": "application/json"}

    def synthesize(self, text: str) -> Speech:
        last = ""
        for attempt in range(1, self.retries + 1):
            call = self._generate_content if self._use_fallback else self._interactions
            r = call(text)
            if r.status_code == 200:
                audio = _find_audio(r.json())
                if audio is not None:
                    return Speech(audio, SR, None)
                last = "yanıtta ses yok"
            else:
                if r.status_code == 402 or (r.status_code == 429 and "prepay" in r.text.lower()):
                    from ..images.gemini_engine import BILLING
                    raise SystemExit(BILLING.format(code=r.status_code))
                last = f"HTTP {r.status_code}: {r.text[:300]}"
                if not self._use_fallback and r.status_code in (400, 404):
                    print(f"  gemini-tts: {self.model} reddedildi ({r.status_code}), {self.fallback} deneniyor")
                    self._use_fallback = True
                    continue
                if r.status_code in (401, 403):
                    break
            time.sleep(min(60, 5 * attempt * attempt))   # 429 / preview rate limits
        raise SystemExit(f"Gemini TTS hatası: {last}")


def _find_audio(obj) -> np.ndarray | None:
    """Walk the response and decode the first base64 audio blob (WAV or raw 16-bit PCM)."""
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            inline = o.get("inlineData") or o.get("inline_data")
            if isinstance(inline, dict) and inline.get("data"):
                return _decode(inline["data"], inline.get("mimeType") or inline.get("mime_type") or "")
            mime = str(o.get("mime_type") or o.get("mimeType") or "")
            if isinstance(o.get("data"), str) and (mime.startswith("audio") or o.get("type") == "audio"):
                return _decode(o["data"], mime)
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(reversed(o))
    return None


def _decode(b64: str, mime: str) -> np.ndarray:
    raw = base64.b64decode(b64)
    if raw[:4] == b"RIFF":
        with wave.open(io.BytesIO(raw)) as w:
            if w.getframerate() != SR or w.getsampwidth() != 2:
                raise SystemExit(f"Beklenmeyen WAV biçimi: {w.getframerate()} Hz, {w.getsampwidth() * 8} bit")
            pcm = w.readframes(w.getnframes())
            ch = w.getnchannels()
    else:
        m = re.search(r"rate=(\d+)", mime)
        if m and int(m.group(1)) != SR:
            raise SystemExit(f"Beklenmeyen örnekleme hızı: {mime}")
        pcm, ch = raw, 1
    a = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    return a.reshape(-1, ch).mean(axis=1) if ch > 1 else a


HOOK = ("Pick up a ball and throw it as hard as you can. That simple move is something no other animal on Earth "
        "can really copy. An adult male chimpanzee, trained to throw, manages about twenty miles an hour. "
        "A professional pitcher throws more than ninety. So where does the speed come from?")


def _audition(voices: list[str]) -> None:
    from pathlib import Path
    from ..config import ROOT, default_channel, load_config
    cfg = load_config(default_channel())
    out = ROOT / "build" / "voice_test"
    out.mkdir(parents=True, exist_ok=True)
    for v in voices:
        cfg.setdefault("tts", {}).setdefault("gemini", {})["voice"] = v
        t = GeminiTTS(cfg)
        sp = t.synthesize(HOOK)
        path = out / f"gemini_{v}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
            w.writeframes((np.clip(sp.samples, -1, 1) * 32767).astype("<i2").tobytes())
        model = t.fallback if t._use_fallback else t.model
        print(f"  {v}: {path}  ({len(sp.samples) / SR:.1f} sn, model {model})")
    print(f"\nDinle: {out}")


if __name__ == "__main__":
    _audition(sys.argv[1:] or ["Leda", "Zephyr", "Laomedeia"])
