"""Global config (config.yaml) + per-channel overrides (channels/<id>/channel.yaml) + secrets (.env).

Effective settings for a channel = deep_merge(config.yaml, channel.yaml["overrides"]).
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CHANNELS = ROOT / "channels"
ASSETS = ROOT / "assets"
ENV_PATH = ROOT / ".env"
SECRET_NAMES = ["GEMINI_API_KEY", "ELEVENLABS_API_KEY", "ANTHROPIC_API_KEY", "YOUTUBE_API_KEY"]


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ENV_PATH, override=True)


class Config(dict):
    """dict with dotted access: cfg.get_path("tts.kokoro.voice")."""

    def get_path(self, dotted: str, default: Any = None) -> Any:
        node: Any = self
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_global() -> Config:
    _load_env()
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return Config(yaml.safe_load(f) or {})


def load_config(channel: str | None = None) -> Config:
    """Effective config for a channel (or the global one when channel is None)."""
    cfg = load_global()
    if channel:
        from .channel import Channel, resolve_channel_id
        ch = Channel(resolve_channel_id(channel))
        if ch.exists():
            merged = deep_merge(cfg, ch.data.get("overrides") or {})
            merged["channel"] = {**(cfg.get("channel") or {}), **{k: v for k, v in ch.data.items() if k != "overrides"}}
            return Config(merged)
    return cfg


def default_channel() -> str:
    from .channel import resolve_channel_id
    return resolve_channel_id(load_global().get_path("factory.default_channel", "homo-athleticus"))


def secret(name: str) -> str:
    """Read an API key from the environment; fail with a clear Turkish message."""
    _load_env()
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"\n[eksik anahtar] {name} bulunamadı.\n"
            f"  Panelde Ayarlar → API anahtarları bölümünden ekle (ya da .env dosyasına {name}= yaz).\n"
        )
    return value


def secrets_status() -> dict[str, bool]:
    _load_env()
    return {n: bool(os.environ.get(n, "").strip()) for n in SECRET_NAMES}


def set_secret(name: str, value: str) -> None:
    """Write/replace one key in the local .env file (never committed)."""
    if name not in SECRET_NAMES:
        raise ValueError(f"unknown secret {name}")
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    lines = [ln for ln in lines if not ln.startswith(f"{name}=")]
    if value.strip():
        lines.append(f"{name}={value.strip()}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ.pop(name, None)
    _load_env()
