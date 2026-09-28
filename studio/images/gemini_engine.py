"""Paid engine: Google Gemini image models ("Nano Banana") via the official REST API.

Optional character consistency: visual.characters: [coach] attaches assets/refs/<name>.png
as a reference image when it exists (create it once with: python -m studio refs).
"""
from __future__ import annotations

import base64
import io
import time
from pathlib import Path

import requests
from PIL import Image

from ..config import ASSETS, secret
from .style_prompt import build_prompt

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiEngine:
    def __init__(self, cfg):
        self.key = secret("GEMINI_API_KEY")
        self.model = cfg.get_path("images.gemini.model", "gemini-3.1-flash-image")
        self.aspect = cfg.get_path("images.gemini.aspect_ratio", "16:9")
        self.retries = int(cfg.get_path("images.gemini.retries", 3))
        self.size = (int(cfg.get_path("video.width", 1920)), int(cfg.get_path("video.height", 1080)))

    def _parts(self, visual) -> list[dict]:
        parts: list[dict] = [{"text": build_prompt(visual)}]
        chars = visual.get("characters", []) if isinstance(visual, dict) else []
        for name in chars or []:
            ref = ASSETS / "refs" / f"{name}.png"
            if ref.exists():
                parts.append({"inline_data": {"mime_type": "image/png",
                                              "data": base64.b64encode(ref.read_bytes()).decode()}})
        return parts

    def render(self, shot: dict, out: Path) -> None:
        body = {
            "contents": [{"parts": self._parts(shot["visual"])}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": self.aspect}},
        }
        last = ""
        for attempt in range(1, self.retries + 1):
            r = requests.post(API.format(model=self.model), json=body, timeout=180,
                              headers={"x-goog-api-key": self.key, "Content-Type": "application/json"})
            if r.status_code == 200:
                img = _first_image(r.json())
                if img is not None:
                    _cover(img, self.size).save(out)
                    return
                last = "yanıtta görsel yok (güvenlik filtresi olabilir)"
            else:
                last = f"HTTP {r.status_code}: {r.text[:200]}"
                if r.status_code in (400, 401, 403):
                    break
            time.sleep(5 * attempt)
        raise RuntimeError(f"{shot['id']}: Gemini görsel üretemedi — {last}")


def _first_image(resp: dict):
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            data = part.get("inlineData") or part.get("inline_data")
            if data and data.get("data"):
                return Image.open(io.BytesIO(base64.b64decode(data["data"]))).convert("RGB")
    return None


def _cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale and centre-crop to exactly fill the video frame."""
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - tw) // 2, (img.height - th) // 2
    return img.crop((left, top, left + tw, top + th))
