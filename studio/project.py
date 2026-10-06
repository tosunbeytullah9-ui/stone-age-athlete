"""A project = one video inside a channel. Folder layout:

channels/<channel>/projects/<slug>/
  project.yaml       title, idea id, status, notes
  script.md          narration in the channel's primary language
  sources.md         every factual claim's source (required before production)
  storyboard.yaml    one entry per shot: text (+ translations in i18n) + visual recipe
  build/
    shots/           one PNG per shot (shared by all languages — images contain no text)
    <lang>/audio/    narration units + narration.wav + manifest.json
    <lang>/timing.json
    <lang>/video.mp4, <lang>/shorts/*.mp4, <lang>/description.txt
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .channel import Channel


@dataclass
class Project:
    channel: str
    slug: str

    @property
    def ch(self) -> Channel:
        return Channel(self.channel)

    @property
    def dir(self) -> Path:
        return self.ch.projects_dir / self.slug

    @property
    def meta_path(self) -> Path:
        return self.dir / "project.yaml"

    @property
    def script_path(self) -> Path:
        return self.dir / "script.md"

    @property
    def sources_path(self) -> Path:
        return self.dir / "sources.md"

    @property
    def storyboard_path(self) -> Path:
        return self.dir / "storyboard.yaml"

    @property
    def build(self) -> Path:
        p = self.dir / "build"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def shots_dir(self) -> Path:
        p = self.build / "shots"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def primary_lang(self) -> str:
        try:
            return self.ch.languages[0]
        except Exception:
            return "en"

    def lang_dir(self, lang: str | None = None) -> Path:
        p = self.build / (lang or self.primary_lang())
        p.mkdir(parents=True, exist_ok=True)
        return p

    def audio_dir(self, lang: str | None = None) -> Path:
        p = self.lang_dir(lang) / "audio"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def audio_manifest_path(self, lang: str | None = None) -> Path:
        return self.audio_dir(lang) / "manifest.json"

    def timing_path(self, lang: str | None = None) -> Path:
        return self.lang_dir(lang) / "timing.json"

    def video_path(self, lang: str | None = None) -> Path:
        return self.lang_dir(lang) / "video.mp4"

    # ---- meta --------------------------------------------------------------
    def exists(self) -> bool:
        return self.script_path.exists()

    @property
    def meta(self) -> dict[str, Any]:
        if not self.meta_path.exists():
            return {"title": self.slug, "status": "scripting"}
        with open(self.meta_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def save_meta(self, data: dict[str, Any]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=None, width=110)

    # ---- storyboard --------------------------------------------------------
    def load_storyboard(self) -> dict[str, Any]:
        if not self.storyboard_path.exists():
            raise SystemExit(f"storyboard.yaml yok. Önce 'split' adımını çalıştır ({self.channel}/{self.slug}).")
        with open(self.storyboard_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def save_storyboard(self, data: dict[str, Any]) -> None:
        with open(self.storyboard_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=110)

    # ---- json helpers ------------------------------------------------------
    @staticmethod
    def read_json(path: Path) -> Any:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def shot_text(shot: dict, lang: str, primary: str) -> str:
    """Text of a shot in a language (primary = shot['text'], others from shot['i18n'][lang])."""
    if lang == primary:
        return shot["text"]
    t = (shot.get("i18n") or {}).get(lang)
    if not t:
        raise SystemExit(f"{shot['id']}: '{lang}' çevirisi yok (storyboard → i18n.{lang}). Önce çeviri adımını çalıştır.")
    return t


SCRIPT_TEMPLATE = """# {title}
<!-- Narration in English. Paragraphs are separated by a blank line; lines starting with # are ignored.
     Structure that holds viewers (~1,300-1,600 words ≈ 9-11 min):
     1. HOOK (0-8 s): the most surprising SOURCED fact or stake, second person ("Take a deep breath...").
     2. SETUP: who / where / why it matters, short sentences.
     3. EVIDENCE: one study at a time: who was measured, what was found (group, not "all humans").
     4. TURN: "But here is where the story gets complicated..." what the evidence cannot tell us.
     5. COACH'S LESSON (60-90 s): what the viewer can safely use today.
     Every number and "scientists found" needs a claim (İddialar).
     Delivery (ElevenLabs eleven_v3 only, ignored otherwise): a tag before the words, sparingly, e.g.
     "[curious] So why can't a chimp throw?", "[excited]", "[whispers]", "[pause]". Never in captions. -->

Write the first paragraph of narration here.

Write the second paragraph here.
"""

SOURCES_TEMPLATE = """# Sources — {title}
<!-- One line per source: what it supports + link. Production is blocked until at least 3 sources are listed. -->

"""


def create_project(channel: str, title: str, idea_id: str | None = None, slug: str | None = None) -> Project:
    ch = Channel(channel)
    p = Project(channel, slug or ch.next_project_slug(title))
    if p.exists():
        raise ValueError(f"project exists: {p.slug}")
    p.dir.mkdir(parents=True, exist_ok=True)
    p.script_path.write_text(SCRIPT_TEMPLATE.format(title=title), encoding="utf-8")
    p.sources_path.write_text(SOURCES_TEMPLATE.format(title=title), encoding="utf-8")
    p.save_meta({"title": title, "idea": idea_id, "status": "scripting"})
    return p
