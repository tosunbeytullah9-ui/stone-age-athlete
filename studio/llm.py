"""Minimal text-model clients for planning and translation: Gemini (same key as the images) or Anthropic."""
from __future__ import annotations

import requests

from .config import secret

ANTHROPIC = "https://api.anthropic.com/v1/messages"
GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def complete(prompt: str, model: str, max_tokens: int = 16000, provider: str = "anthropic") -> str:
    if provider == "gemini":
        return _gemini(prompt, model, max_tokens)
    r = requests.post(ANTHROPIC, timeout=600, headers={
        "x-api-key": secret("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01",
        "content-type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]})
    if r.status_code != 200:
        raise SystemExit(f"Anthropic API hatası {r.status_code}: {r.text[:300]}")
    return "".join(b.get("text", "") for b in r.json().get("content", []))


def _gemini(prompt: str, model: str, max_tokens: int) -> str:
    r = requests.post(GEMINI.format(model=model), timeout=600,
                      headers={"x-goog-api-key": secret("GEMINI_API_KEY"), "Content-Type": "application/json"},
                      json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7}})
    if r.status_code == 402 or (r.status_code == 429 and "prepay" in r.text.lower()):
        from .images.gemini_engine import BILLING
        raise SystemExit(BILLING.format(code=r.status_code))
    if r.status_code != 200:
        raise SystemExit(f"Gemini API hatası {r.status_code}: {r.text[:300]}")
    parts = [p for c in r.json().get("candidates", []) for p in c.get("content", {}).get("parts", [])]
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    if not text.strip():
        raise SystemExit("Gemini boş yanıt verdi (güvenlik filtresi ya da token sınırı). Tekrar dene.")
    return text
