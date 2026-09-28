"""One-time data moves after an update. Safe to run on every start: it only acts when there is work to do.

Renamed channels: a channel.yaml lists its old ids under `aliases`. If a folder with an old id is still there
(projects the owner created before the rename, which Git does not move), its projects are moved into the new
channel folder, idea statuses are carried over by id, and the rest of the old folder goes to backups/.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

import yaml

from .channel import Channel, list_channels
from .config import CHANNELS, ROOT


def _backup_dir() -> Path:
    p = ROOT / "backups" / time.strftime("%Y%m%d-%H%M%S")
    p.mkdir(parents=True, exist_ok=True)
    return p


def migrate_renamed_channels(verbose: bool = True) -> list[str]:
    notes: list[str] = []
    for ch in list_channels():
        for old in ch.aliases:
            src = CHANNELS / old
            if old == ch.id or not src.is_dir():
                continue
            moved = 0
            for proj in sorted((src / "projects").glob("*")) if (src / "projects").is_dir() else []:
                if not proj.is_dir():
                    continue
                dst = ch.projects_dir / proj.name
                ch.projects_dir.mkdir(parents=True, exist_ok=True)
                if not dst.exists():
                    shutil.move(str(proj), str(dst))
                else:
                    _merge_move(proj, dst)     # e.g. scripts restored by the updater + build/ left here
                moved += 1
            if (src / "compilations").is_dir():
                dst = ch.dir / "compilations"
                dst.mkdir(exist_ok=True)
                for f in (src / "compilations").iterdir():
                    if not (dst / f.name).exists():
                        shutil.move(str(f), str(dst / f.name))
            old_ideas = src / "ideas.yaml"
            if old_ideas.exists():
                n = carry_idea_state(old_ideas, ch)
                if n:
                    notes.append(f"{n} fikrin durumu '{old}' klasöründen taşındı")
            rest = [p for p in src.rglob("*") if p.is_file()]
            if rest:
                bdir = _backup_dir() / "channels"
                bdir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(bdir / old))
            else:
                shutil.rmtree(src, ignore_errors=True)
            if moved:
                notes.append(f"{moved} proje '{old}' → '{ch.id}' klasörüne taşındı")
    if verbose:
        for n in notes:
            print(f"  [taşıma] {n}")
    return notes


def _merge_move(src: Path, dst: Path) -> None:
    """Moves every file of src into dst that dst does not have yet; files present in both stay in src."""
    for f in sorted(src.rglob("*")):
        if f.is_file():
            t = dst / f.relative_to(src)
            if not t.exists():
                t.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(t))


STATE_KEYS = ("status", "project", "notes", "gut")


def carry_idea_state(old_path: Path, ch: Channel) -> int:
    """Copies owner-set fields (status, project, notes, gut) from an old idea file into the channel's ideas by id.
    Old files without ids used the position as id (i001 = first idea)."""
    try:
        old = yaml.safe_load(old_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return 0
    old_ideas = old.get("ideas") or []
    by_id = {}
    for i, idea in enumerate(old_ideas):
        if isinstance(idea, dict):
            by_id[idea.get("id") or f"i{i + 1:03d}"] = idea
    data = ch.load_ideas()
    ids = {i["id"] for i in data["ideas"]}
    n = 0
    for idea in data["ideas"]:
        o = by_id.get(idea["id"])
        if not o or o.get("title") != idea.get("title"):
            continue
        changed = False
        for k in STATE_KEYS:
            if o.get(k) not in (None, "", "idea") and idea.get(k) in (None, "", "idea"):
                idea[k] = o[k]
                changed = True
        n += changed
    for iid, o in by_id.items():       # ideas the owner added himself
        if iid not in ids and o.get("title") and not any(x.get("title") == o["title"] for x in data["ideas"]):
            data["ideas"].append({**o, "id": iid})
            n += 1
    if n:
        ch.save_ideas(data)
    return n
