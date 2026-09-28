"""Three-way merge of the owner's local edits with an update from GitHub.

base   = the file as it was in the version the owner last downloaded
ours   = the owner's edited copy (panel saves, new ideas, statuses, settings)
theirs = the file in the new version

Rule for every value: whoever changed it wins; if both changed it, the owner wins. Lists of records with an
`id` (ideas, sources, claims) are merged record by record, so a new field added upstream (e.g. signals) and a
status the owner set on the same idea both survive.
"""
from __future__ import annotations

import copy
import io
from typing import Any

import yaml

MISSING = object()


def _with_ids(items: list) -> list:
    """Idea lists written by older versions have no ids: ids were the 1-based position (i001, i002 ...)."""
    out = []
    for i, it in enumerate(items):
        if isinstance(it, dict) and "id" not in it:
            it = {"id": f"i{i + 1:03d}", **it}
        out.append(it)
    return out


def _keyed(items: list) -> bool:
    return bool(items) and all(isinstance(i, dict) and "id" in i for i in items)


def merge_value(base: Any, ours: Any, theirs: Any, key: str = "") -> Any:
    if ours == base:
        return theirs
    if theirs == base or ours == theirs:
        return ours
    if isinstance(ours, dict) and isinstance(theirs, dict):
        return merge_dict(base if isinstance(base, dict) else {}, ours, theirs)
    if isinstance(ours, list) and isinstance(theirs, list):
        return merge_list(base if isinstance(base, list) else [], ours, theirs, key)
    return ours if ours is not MISSING else theirs


def merge_dict(base: dict, ours: dict, theirs: dict) -> dict:
    out: dict = {}
    keys = list(theirs) + [k for k in ours if k not in theirs]
    for k in keys:
        b, o, t = base.get(k, MISSING), ours.get(k, MISSING), theirs.get(k, MISSING)
        v = merge_value(b, o, t, str(k))
        if v is not MISSING:
            out[k] = v
    return out


def merge_list(base: list, ours: list, theirs: list, key: str = "") -> list:
    if key == "ideas":
        base, ours, theirs = _with_ids(base), _with_ids(ours), _with_ids(theirs)
    if not (_keyed(ours) and (_keyed(theirs) or not theirs)):
        return ours
    bmap = {i["id"]: i for i in base if isinstance(i, dict) and "id" in i}
    omap = {i["id"]: i for i in ours}
    out = []
    for t in theirs:
        o = omap.get(t["id"], MISSING)
        b = bmap.get(t["id"], MISSING)
        if o is MISSING:
            if b is MISSING:          # new upstream record
                out.append(t)
            continue                  # the owner deleted it
        out.append(merge_value(b, o, t, key))
    tids = {t["id"] for t in theirs}
    for o in ours:                    # records the owner added
        if o["id"] not in tids and o["id"] not in bmap:
            out.append(o)
    return out


def merge_yaml_text(base: str | None, ours: str, theirs: str, ideas_file: bool = False) -> str:
    """Returns the merged file text. Raises ValueError when a side is not valid YAML."""
    try:
        b = yaml.safe_load(base) if base else {}
        o = yaml.safe_load(ours)
        t = yaml.safe_load(theirs)
    except yaml.YAMLError as e:
        raise ValueError(str(e)) from e
    merged = merge_value(b if b is not None else {}, o, t)
    if ideas_file and isinstance(merged, dict):
        from .channel import dump_ideas
        header = []
        for ln in theirs.splitlines():
            if not ln.startswith("#"):
                break
            header.append(ln)
        return dump_ideas(merged, header)
    return dump_preserving(theirs, merged)


def dump_preserving(theirs_text: str, merged: Any) -> str:
    """Writes `merged` keeping the comments and layout of the new file where values did not change."""
    try:
        from ruamel.yaml import YAML
    except ImportError:
        return yaml.safe_dump(merged, allow_unicode=True, sort_keys=False, width=110)
    ry = YAML()
    ry.preserve_quotes = True
    ry.width = 4096
    doc = ry.load(theirs_text)
    if not isinstance(doc, dict) or not isinstance(merged, dict):
        return yaml.safe_dump(merged, allow_unicode=True, sort_keys=False, width=110)
    _apply(doc, merged)
    buf = io.StringIO()
    ry.dump(doc, buf)
    return buf.getvalue()


def _apply(doc: Any, merged: dict) -> None:
    for k in list(doc.keys()):
        if k not in merged:
            del doc[k]
    for k, v in merged.items():
        if k in doc and isinstance(doc[k], dict) and isinstance(v, dict):
            _apply(doc[k], v)
        elif k not in doc or _plain(doc[k]) != v:
            doc[k] = copy.deepcopy(v)


def _plain(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_plain(x) for x in v]
    return v
