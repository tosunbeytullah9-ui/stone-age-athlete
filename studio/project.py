"""A project = one video. Folder layout:

projects/<slug>/
  script.md          narration (paragraphs separated by a blank line)
  storyboard.yaml    one entry per shot: text + visual spec (edited by hand or by the planner)
  build/             generated files (git-ignored)
    audio/           narration chunks + narration.wav
    shots/           one PNG per shot
    timing.json      start/end seconds per shot
    video.mp4        final render
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import PROJECTS


@dataclass
class Project:
    slug: str

    @property
    def dir(self) -> Path:
        return PROJECTS / self.slug

    @property
    def script_path(self) -> Path:
        return self.dir / "script.md"

    @property
    def storyboard_path(self) -> Path:
        return self.dir / "storyboard.yaml"

    @property
    def build(self) -> Path:
        p = self.dir / "build"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def audio_dir(self) -> Path:
        p = self.build / "audio"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def shots_dir(self) -> Path:
        p = self.build / "shots"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def timing_path(self) -> Path:
        return self.build / "timing.json"

    @property
    def audio_manifest_path(self) -> Path:
        return self.audio_dir / "manifest.json"

    # ---- storyboard -------------------------------------------------------
    def exists(self) -> bool:
        return self.dir.exists()

    def load_storyboard(self) -> dict[str, Any]:
        if not self.storyboard_path.exists():
            raise SystemExit(f"storyboard.yaml yok. Önce: python -m studio split {self.slug}")
        with open(self.storyboard_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def save_storyboard(self, data: dict[str, Any]) -> None:
        with open(self.storyboard_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=110)

    # ---- json helpers -----------------------------------------------------
    @staticmethod
    def read_json(path: Path) -> Any:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
