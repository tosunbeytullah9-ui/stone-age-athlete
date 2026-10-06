"""AI images with Google Gemini ("Nano Banana") via the official REST API.

Reference images keep things consistent:
  visual.characters: [coach]  attaches channels/<c>/<characters.coach.ref> (the character sheet)
  visual.ref: s012            attaches that shot's finished image ("same place, a moment later")
"""
from __future__ import annotations

import base64
import io
import time
from pathlib import Path

import requests
from PIL import Image

from ..config import CHANNELS, secret
from .style_prompt import build_prompt

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
BILLING = ("Gemini kredisi bitti ya da faturalandırma kapalı (HTTP {code}). Google AI Studio → "
           "https://ai.studio/projects → projen → Billing'den kredi yükle, sonra aynı adımı tekrar çalıştır "
           "(hazır olanlar korunur, tekrar ödenmez).")


class OutOfCredits(SystemExit):
    """Retrying cannot help: stop the whole step instead of failing scene after scene."""


class GeminiEngine:
    def __init__(self, cfg):
        self.key = secret("GEMINI_API_KEY")
        self.model = cfg.get_path("images.gemini.model", "gemini-3.1-flash-image")
        self.aspect = cfg.get_path("images.gemini.aspect_ratio", "16:9")
        self.image_size = cfg.get_path("images.gemini.image_size", "") or ""
        self.retries = int(cfg.get_path("images.gemini.retries", 3))
        self.size = (int(cfg.get_path("video.width", 1920)), int(cfg.get_path("video.height", 1080)))
        self.style = cfg.get_path("channel.visual_style", "") or ""
        self.characters = cfg.get_path("channel.characters") or {}
        self.channel_dir = CHANNELS / str(cfg.get_path("channel.id", "") or "")

    def char_refs(self, names) -> list[Path]:
        out = []
        for n in names or []:
            ref = (self.characters.get(n) or {}).get("ref")
            if ref and (self.channel_dir / ref).exists():
                out.append(self.channel_dir / ref)
        return out

    def render(self, shot: dict, out: Path, shots_dir: Path | None = None) -> None:
        v = shot["visual"]
        refs = self.char_refs(v.get("characters") if isinstance(v, dict) else None)
        if isinstance(v, dict) and v.get("ref") and shots_dir is not None:
            prev = shots_dir / f"{v['ref']}.png"
            if prev.exists():
                refs.append(prev)
        prompt = build_prompt(v, self.style, self.characters)
        if isinstance(v, dict) and v.get("ref"):
            prompt += "\n\nThe last attached image is the previous scene: keep its place, light and people consistent."
        try:
            self.generate(prompt, out, refs)
        except RuntimeError as e:
            raise RuntimeError(f"{shot['id']}: {e}") from None

    def generate(self, prompt: str, out: Path, refs: list[Path] | None = None, aspect: str | None = None,
                 size: tuple[int, int] | None = None) -> None:
        parts: list[dict] = [{"text": prompt}]
        for ref in refs or []:
            parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(_png(ref)).decode()}})
        image_cfg = {"aspectRatio": aspect or self.aspect}
        if self.image_size:
            image_cfg["imageSize"] = self.image_size
        body = {"contents": [{"parts": parts}],
                "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": image_cfg}}
        last = ""
        for attempt in range(1, self.retries + 1):
            try:
                r = requests.post(API.format(model=self.model), json=body, timeout=240,
                                  headers={"x-goog-api-key": self.key, "Content-Type": "application/json"})
            except requests.RequestException as e:
                last = f"bağlantı hatası: {e}"
                time.sleep(5 * attempt)
                continue
            if r.status_code == 200:
                img = _first_image(r.json())
                if img is not None:
                    _cover(img, size or self.size).save(out)
                    return
                last = "yanıtta görsel yok (güvenlik filtresi olabilir; istemi yumuşat)"
            else:
                if r.status_code == 402 or (r.status_code == 429 and "prepay" in r.text.lower()):
                    raise OutOfCredits(BILLING.format(code=r.status_code))
                last = f"HTTP {r.status_code}: {r.text[:200]}"
                if r.status_code in (400, 401, 403):
                    break
            time.sleep(5 * attempt)
        raise RuntimeError(f"Gemini görsel üretemedi — {last}")


def _png(path: Path) -> bytes:
    if path.suffix.lower() == ".png":
        return path.read_bytes()
    buf = io.BytesIO()
    Image.open(path).convert("RGB").save(buf, "PNG")
    return buf.getvalue()


def _first_image(resp: dict):
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            data = part.get("inlineData") or part.get("inline_data")
            if data and data.get("data"):
                return Image.open(io.BytesIO(base64.b64decode(data["data"]))).convert("RGB")
    return None


def _cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale and centre-crop to exactly fill the frame."""
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - tw) // 2, (img.height - th) // 2
    return img.crop((left, top, left + tw, top + th))
