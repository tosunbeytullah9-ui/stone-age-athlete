"""Loads config.yaml and .env. Every provider reads its settings from here."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
ASSETS = ROOT / "assets"


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # dotenv is optional at import time
        return
    load_dotenv(ROOT / ".env")


class Config(dict):
    """dict with dotted access: cfg.get_path("tts.kokoro.voice")."""

    def get_path(self, dotted: str, default: Any = None) -> Any:
        node: Any = self
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node


def load_config(path: Path | None = None) -> Config:
    _load_env()
    path = path or ROOT / "config.yaml"
    with open(path, encoding="utf-8") as f:
        return Config(yaml.safe_load(f) or {})


def secret(name: str) -> str:
    """Read an API key from the environment; fail with a clear Turkish message."""
    _load_env()
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"\n[eksik anahtar] {name} bulunamadı.\n"
            f"  .env.example dosyasını .env olarak kopyala ve {name}= satırını doldur.\n"
        )
    return value
