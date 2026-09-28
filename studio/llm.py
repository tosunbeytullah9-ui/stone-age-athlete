"""Minimal Anthropic Messages API client (paid automation for planning and translation)."""
from __future__ import annotations

import requests

from .config import secret

API = "https://api.anthropic.com/v1/messages"


def complete(prompt: str, model: str, max_tokens: int = 16000) -> str:
    r = requests.post(API, timeout=600, headers={
        "x-api-key": secret("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01",
        "content-type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]})
    if r.status_code != 200:
        raise SystemExit(f"Anthropic API hatası {r.status_code}: {r.text[:300]}")
    return "".join(b.get("text", "") for b in r.json().get("content", []))
