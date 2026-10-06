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
    id_map: dict[str, str] = {}
    for idx, b in enumerate(beats):
        prev = keep.get(idx, {})
        shot = {"id": f"s{idx + 1:03d}", "para": b["para"], "sent": b["sent"], "text": b["text"]}
        # everything planned for an unchanged sentence survives: visual, engine, camera, translations, overlay ...
        for key, val in prev.items():
            if key not in ("id", "para", "sent", "text", "tone") and val is not None:
                shot[key] = val
        if b.get("tone"):              # delivery tags always follow script.md ([curious] ...)
            shot["tone"] = b["tone"]
        shot.setdefault("visual", None)
        if prev.get("id"):
            id_map[prev["id"]] = shot["id"]
        shots.append(shot)

    from .images import drop_orphans
    drop_orphans(shots)
    data = {
        "title": title,
        "paragraphs": len(paragraphs(script)),
        "shots": shots,
    }
    project.save_storyboard(data)
    if any(k != v for k, v in id_map.items()):
        remap_shot_refs(project, id_map)
    return data


def remap_shot_refs(project: Project, id_map: dict[str, str]) -> None:
    """Shot ids are renumbered when the script changes; keep Shorts ranges and claim links pointing at the same
    sentences."""
    meta = project.meta
    changed = False
    for cut in meta.get("shorts") or []:
        for k in ("from", "to"):
            if cut.get(k) in id_map and id_map[cut[k]] != cut[k]:
                cut[k] = id_map[cut[k]]
                changed = True
    if changed:
        project.save_meta(meta)
    from .claims import load_claims, save_claims
    data = load_claims(project)
    if data.get("claims"):
        for c in data["claims"]:
            c["shots"] = [id_map.get(x, x) for x in c.get("shots") or []]
        save_claims(project, data)


def unplanned(shots: list[dict]) -> list[dict]:
    return [s for s in shots if not s.get("visual")]
