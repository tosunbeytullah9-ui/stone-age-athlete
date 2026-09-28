"""Audience retention → shots. Import the retention curve exported from YouTube Studio (Analytics → Engagement →
Audience retention → export, or copy two columns) and see exactly which sentence and drawing were on screen when
viewers left.

Accepted input: CSV/TSV/pasted text with a position column (percent of the video, seconds, or m:ss) and a
retention column (percent or 0..1). English and Turkish Studio headers work; decimal commas are fine.
Stored in <project>/analytics/retention_<lang>.json (raw text next to it).
"""
from __future__ import annotations

import csv
import io
import json
import re
from typing import Any

from .project import Project

POS_WORDS = ("position", "konum", "time", "zaman", "süre", "sure", "moment", "an ")
RET_WORDS = ("retention", "elde tutma", "izleyici", "audience", "kitle")


def _num(s: str) -> float | None:
    s = (s or "").strip().replace("%", "").replace(" ", "")
    if not s:
        return None
    if re.fullmatch(r"\d+:\d{1,2}(:\d{1,2})?", s):
        parts = [int(x) for x in s.split(":")]
        return float(parts[0] * 60 + parts[1]) if len(parts) == 2 else float(parts[0] * 3600 + parts[1] * 60 + parts[2])
    if s.count(",") == 1 and "." not in s:
        s = s.replace(",", ".")
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse(text: str) -> dict[str, Any]:
    text = text.strip().lstrip("﻿")
    if not text:
        raise ValueError("boş veri")
    sample = text[:2000]
    delim = "\t" if "\t" in sample else (";" if sample.count(";") > sample.count(",") else ",")
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim) if any(c.strip() for c in r)]
    header = None
    if rows and sum(_num(c) is None for c in rows[0]) >= 1:
        header = [c.strip().lower() for c in rows[0]]
        rows = rows[1:]
    ncols = max(len(r) for r in rows) if rows else 0
    numeric_cols = [i for i in range(ncols) if sum(_num(r[i]) is not None for r in rows if i < len(r)) >= len(rows) * 0.8]
    if len(numeric_cols) < 2:
        raise ValueError("en az iki sayısal sütun gerekli (konum ve izlenme oranı)")
    pos_col, ret_col = numeric_cols[0], numeric_cols[1]
    time_like = any(":" in (r[pos_col] if pos_col < len(r) else "") for r in rows[:5])
    if header:
        for i in numeric_cols:
            h = header[i] if i < len(header) else ""
            if any(w in h for w in POS_WORDS):
                pos_col = i
                break
        cands = [i for i in numeric_cols if i != pos_col]
        abs_first = [i for i in cands if i < len(header) and any(w in header[i] for w in RET_WORDS)
                     and ("abs" in header[i] or "mutlak" in header[i])]
        named = [i for i in cands if i < len(header) and any(w in header[i] for w in RET_WORDS)]
        ret_col = (abs_first or named or cands)[0]
    pts = []
    for r in rows:
        if max(pos_col, ret_col) >= len(r):
            continue
        p, v = _num(r[pos_col]), _num(r[ret_col])
        if p is not None and v is not None:
            pts.append((p, v))
    if len(pts) < 5:
        raise ValueError("çok az veri noktası")
    pts.sort()
    pmax = max(p for p, _ in pts)
    hpos = header[pos_col] if header and pos_col < len(header) else ""
    if time_like or "sn" in hpos or "sec" in hpos or pmax > 100:
        unit = "seconds"
    elif pmax <= 1.0:
        unit = "fraction"
    else:
        unit = "percent"
    vmax = max(v for _, v in pts)
    scale = 100.0 if vmax <= 1.5 else 1.0
    return {"unit": unit, "points": [{"pos": p, "ret": round(v * scale, 2)} for p, v in pts]}


def import_retention(project: Project, lang: str, text: str) -> dict[str, Any]:
    data = parse(text)
    d = project.dir / "analytics"
    d.mkdir(exist_ok=True)
    (d / f"retention_{lang}.txt").write_text(text, encoding="utf-8")
    (d / f"retention_{lang}.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    return analyze(project, lang)


def analyze(project: Project, lang: str) -> dict[str, Any] | None:
    path = project.dir / "analytics" / f"retention_{lang}.json"
    if not path.exists() or not project.timing_path(lang).exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    timing = project.read_json(project.timing_path(lang))
    duration = float((project.meta.get("publish") or {}).get("duration_sec") or timing[-1]["end"])
    pts = []
    for p in data["points"]:
        t = p["pos"] if data["unit"] == "seconds" else (p["pos"] / 100.0 if data["unit"] == "percent" else p["pos"]) * duration
        pts.append({"t": round(t, 2), "ret": p["ret"]})
    shots = {s["id"]: s for s in project.load_storyboard().get("shots", [])}

    def shot_at(t: float) -> dict:
        for tm in timing:
            if tm["start"] <= t < tm["end"]:
                return tm
        return timing[-1]

    # drops: retention lost per window, skipping the first 3 s (everyone who clicks by mistake leaves there)
    win = max(3.0, duration * 0.02)
    drops = []
    for i, a in enumerate(pts):
        if a["t"] < 3:
            continue
        b = next((q for q in pts[i + 1:] if q["t"] >= a["t"] + win), None)
        if not b:
            break
        drops.append({"from": a["t"], "to": b["t"], "lost": round(a["ret"] - b["ret"], 2)})
    drops.sort(key=lambda d: -d["lost"])
    picked: list[dict] = []
    for dr in drops:
        if dr["lost"] <= 0 or any(abs(dr["from"] - p["from"]) < win * 1.5 for p in picked):
            continue
        tm = shot_at(dr["from"] + (dr["to"] - dr["from"]) / 2)
        picked.append({**dr, "shot": tm["id"], "text": shots.get(tm["id"], {}).get("text", ""), "para": shots.get(tm["id"], {}).get("para")})
        if len(picked) == 5:
            break

    def at(t: float) -> float | None:
        prev = None
        for p in pts:
            if p["t"] >= t:
                if prev is None:
                    return p["ret"]
                k = (t - prev["t"]) / max(p["t"] - prev["t"], 1e-6)
                return round(prev["ret"] + k * (p["ret"] - prev["ret"]), 1)
            prev = p
        return None

    paras: dict[int, dict] = {}
    for tm in timing:
        para = shots.get(tm["id"], {}).get("para", 0)
        pr = paras.setdefault(para, {"para": para, "start": tm["start"], "end": tm["end"]})
        pr["end"] = tm["end"]
    for pr in paras.values():
        a, b = at(pr["start"]), at(pr["end"])
        pr["lost"] = round(a - b, 1) if a is not None and b is not None else None
        pr["per_min"] = round(pr["lost"] / max((pr["end"] - pr["start"]) / 60, 0.1), 1) if pr["lost"] is not None else None
    return {"lang": lang, "duration": round(duration, 2), "points": pts,
            "shots": [{"id": t["id"], "start": t["start"], "end": t["end"]} for t in timing],
            "drops": picked, "paragraphs": sorted(paras.values(), key=lambda p: p["para"]),
            "at30": at(30), "at60": at(60), "end": pts[-1]["ret"] if pts else None}
