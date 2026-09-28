"""Builds and updates storyboard.yaml without losing visuals that were already planned."""
from __future__ import annotations

import difflib
from typing import Any

from .config import Config
from .project import Project
from .splitter import paragraphs, split_script


def build_storyboard(project: Project, cfg: Config) -> dict[str, Any]:
    script = project.script_path.read_text(encoding="utf-8")
    beats = split_script(script, cfg.get_path("split.min_chars", 20), cfg.get_path("split.max_chars", 65))

    old_shots: list[dict] = []
    title = project.slug
    if project.storyboard_path.exists():
        old = project.load_storyboard()
        old_shots = old.get("shots", []) or []
        title = old.get("title", title)

    # keep the visual of any shot whose text is unchanged
    old_texts = [s.get("text", "") for s in old_shots]
    new_texts = [b["text"] for b in beats]
    keep: dict[int, dict] = {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=old_texts, b=new_texts, autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                keep[j1 + k] = old_shots[i1 + k]

    shots = []
    for idx, b in enumerate(beats):
        prev = keep.get(idx, {})
        shot = {"id": f"s{idx + 1:03d}", "para": b["para"], "sent": b["sent"], "text": b["text"]}
        for key in ("engine", "visual", "camera"):
            if prev.get(key) is not None:
                shot[key] = prev[key]
        shot.setdefault("visual", None)
        shots.append(shot)

    data = {
        "title": title,
        "paragraphs": len(paragraphs(script)),
        "shots": shots,
    }
    project.save_storyboard(data)
    return data


def unplanned(shots: list[dict]) -> list[dict]:
    return [s for s in shots if not s.get("visual")]
