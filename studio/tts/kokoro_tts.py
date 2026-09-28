"""Free local voice: Kokoro-82M (ONNX build, no PyTorch needed).

Model files (~350 MB) are downloaded once into models/ on first use.
"""
from __future__ import annotations

from pathlib import Path

import requests

from ..config import ROOT
from . import Speech

MODEL_DIR = ROOT / "models"
FILES = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
LANGS = {"a": "en-us", "b": "en-gb"}
OTHER = {"es": "es", "fr": "fr-fr", "it": "it", "pt": "pt-br", "hi": "hi", "ja": "ja", "zh": "cmn"}


def ensure_models() -> tuple[Path, Path]:
    MODEL_DIR.mkdir(exist_ok=True)
    for name, url in FILES.items():
        path = MODEL_DIR / name
        if path.exists() and path.stat().st_size > 1_000_000:
            continue
        print(f"  Kokoro modeli indiriliyor: {name} (tek seferlik)...")
        tmp = path.with_suffix(".part")
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        tmp.rename(path)
    return MODEL_DIR / "kokoro-v1.0.onnx", MODEL_DIR / "voices-v1.0.bin"


class KokoroTTS:
    unit = "sentence"

    def __init__(self, cfg, lang: str = "en"):
        try:
            from kokoro_onnx import Kokoro
        except ImportError as e:
            raise SystemExit("kokoro-onnx kurulu değil: pip install -r requirements-voice.txt") from e
        model, voices = ensure_models()
        self.engine = Kokoro(str(model), str(voices))
        self.speed = float(cfg.get_path("tts.kokoro.speed", 1.0))
        if lang == "en":
            self.voice = cfg.get_path("tts.kokoro.voice", "am_michael")
            self.lang = LANGS.get(cfg.get_path("tts.kokoro.lang_code", "a"), "en-us")
        else:
            self.voice = (cfg.get_path("tts.kokoro.voice_by_lang") or {}).get(lang)
            if not self.voice:
                raise SystemExit(f"config → tts.kokoro.voice_by_lang.{lang} boş (örn. es: em_alex)")
            self.lang = OTHER[lang]

    def cache_key(self) -> str:
        return f"kokoro|{self.voice}|{self.speed}|{self.lang}"

    def synthesize(self, text: str) -> Speech:
        samples, sr = self.engine.create(text, voice=self.voice, speed=self.speed, lang=self.lang)
        return Speech(samples.astype("float32"), sr, None)
