"""A channel = one YouTube channel: identity, style, voice, languages, idea bank, projects.

channels/<id>/
  channel.yaml   identity + overrides of config.yaml (voice, palette, engines ...)
  ideas.yaml     idea bank (pillars + ideas with status)
  projects/      one folder per video
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import CHANNELS

IDEA_STATUSES = ["idea", "researching", "scripting", "production", "published", "dropped"]

TEMPLATE = {
    "name": "New Channel",
    "tagline": "",
    "category": "Education",
    "languages": ["en"],          # first = primary language; others are dubbed versions
    "description": "",
    "mascot": {"pose": "point", "wear": ["headband", "whistle"], "hold": "pointer", "face": "smile"},
    "style": {"palette": {}},     # palette overrides, e.g. {sky_warm: "#f3e3c3"}
    "prompt_style": "",           # extra style sentence appended to every AI image prompt
    "overrides": {},              # any config.yaml key, e.g. {tts: {kokoro: {voice: bm_george}}}
}


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "untitled"


@dataclass
class Channel:
    id: str

    @property
    def dir(self) -> Path:
        return CHANNELS / self.id

    @property
    def path(self) -> Path:
        return self.dir / "channel.yaml"

    @property
    def ideas_path(self) -> Path:
        return self.dir / "ideas.yaml"

    @property
    def projects_dir(self) -> Path:
        return self.dir / "projects"

    def exists(self) -> bool:
        return self.path.exists()

    @property
    def data(self) -> dict[str, Any]:
        with open(self.path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def save(self, data: dict[str, Any]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=110)

    @property
    def languages(self) -> list[str]:
        return list(self.data.get("languages") or ["en"])

    # ---- ideas -----------------------------------------------------------
    def load_ideas(self) -> dict[str, Any]:
        if not self.ideas_path.exists():
            return {"pillars": {}, "ideas": []}
        with open(self.ideas_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        ideas = data.get("ideas") or []
        for i, idea in enumerate(ideas):
            idea.setdefault("id", f"i{i + 1:03d}")
            idea.setdefault("status", "idea")
        data["ideas"] = ideas
        data.setdefault("pillars", {})
        return data

    def save_ideas(self, data: dict[str, Any]) -> None:
        with open(self.ideas_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=140)

    # ---- projects --------------------------------------------------------
    def project_slugs(self) -> list[str]:
        if not self.projects_dir.exists():
            return []
        return sorted(p.name for p in self.projects_dir.iterdir() if (p / "script.md").exists())

    def next_project_slug(self, title: str) -> str:
        nums = [int(s.split("-")[0]) for s in self.project_slugs() if s.split("-")[0].isdigit()]
        n = (max(nums) + 1) if nums else 1
        return f"{n:03d}-{slugify(title)[:40].rstrip('-')}"


def list_channels() -> list[Channel]:
    if not CHANNELS.exists():
        return []
    return [Channel(p.name) for p in sorted(CHANNELS.iterdir()) if (p / "channel.yaml").exists()]


def create_channel(channel_id: str, name: str, languages: list[str] | None = None, **extra) -> Channel:
    ch = Channel(slugify(channel_id))
    if ch.exists():
        raise ValueError(f"channel already exists: {ch.id}")
    data = {**TEMPLATE, "name": name, "languages": languages or ["en"], **extra}
    ch.save(data)
    ch.save_ideas({"pillars": {}, "ideas": []})
    ch.projects_dir.mkdir(parents=True, exist_ok=True)
    return ch
