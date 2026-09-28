"""Publish record: everything about a video's release, kept in project.yaml under `publish:` so analytics can be
joined to production decisions later (which hook, which title, what we predicted).

publish:
  series: human-limits            # channel.yaml → series (playlist)
  slot: long                      # long | short
  hook_type: cold_open_stat       # see HOOK_TYPES
  planned_date: 2026-10-06        # calendar slot (Kanal → Takvim)
  youtube_id: ""                  # after upload
  published_at: ""                # YYYY-MM-DD
  title_used: ""
  title_variants: []              # candidates (Kapak & başlık)
  thumbnail_used: 1               # which variant went live (A/B test: list the ones tested)
  thumbnails_tested: []
  prediction: {views_28d_low: 0, views_28d_high: 0, gut: 3}
  metrics: []                     # snapshots: {date, day, views, impressions, ctr, avd_sec, avg_pct, subs, likes, comments}
  notes: ""
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .project import Project

HOOK_TYPES = {
    "cold_open_stat": "Şaşırtıcı sayı/sonuçla açılış",
    "question": "Soru",
    "contradiction": "Çelişki (herkes X sanıyor ama)",
    "story": "Hikâye / sahne",
    "mystery": "Bilimsel gizem",
    "you": "İzleyiciye doğrudan (sen...)",
}
SLOT_TYPES = ["long", "short"]
METRIC_KEYS = ["views", "impressions", "ctr", "avd_sec", "avg_pct", "subs", "likes", "comments"]


def defaults(project: Project) -> dict[str, Any]:
    return {"series": guess_series(project), "slot": "long", "hook_type": "", "planned_date": "",
            "youtube_id": "", "published_at": "", "title_used": "", "title_variants": [],
            "thumbnail_used": 1, "thumbnails_tested": [],
            "prediction": {"views_28d_low": None, "views_28d_high": None, "gut": None},
            "metrics": [], "notes": ""}


def get_publish(project: Project) -> dict[str, Any]:
    d = defaults(project)
    cur = project.meta.get("publish") or {}
    d.update({k: v for k, v in cur.items() if v is not None})
    if isinstance(cur.get("prediction"), dict):
        d["prediction"] = {**defaults(project)["prediction"], **cur["prediction"]}
    return d


def save_publish(project: Project, data: dict[str, Any]) -> dict[str, Any]:
    meta = project.meta
    pub = {**(meta.get("publish") or {}), **data}
    clean = {k: v for k, v in pub.items() if v not in (None, "", [], {})}
    if isinstance(clean.get("prediction"), dict):
        clean["prediction"] = {k: v for k, v in clean["prediction"].items() if v not in (None, "")}
        if not clean["prediction"]:
            clean.pop("prediction")
    meta["publish"] = clean
    if data.get("title_used"):
        meta["title"] = data["title_used"]         # the chosen title is the video's title everywhere
    if clean.get("youtube_id") or clean.get("published_at"):
        meta["status"] = "published"
    project.save_meta(meta)
    _sync_idea_status(project, meta)
    return get_publish(project)


def add_metrics(project: Project, snap: dict[str, Any]) -> dict[str, Any]:
    pub = get_publish(project)
    snap = {k: v for k, v in snap.items() if v not in (None, "")}
    snap.setdefault("date", date.today().isoformat())
    if pub.get("published_at") and "day" not in snap:
        try:
            snap["day"] = (date.fromisoformat(snap["date"]) - date.fromisoformat(pub["published_at"])).days
        except ValueError:
            pass
    metrics = [m for m in pub.get("metrics") or [] if m.get("date") != snap["date"]] + [snap]
    metrics.sort(key=lambda m: m.get("date", ""))
    return save_publish(project, {"metrics": metrics})


def guess_series(project: Project) -> str:
    """Series from the idea's pillar (channel.yaml → series.<id>.pillars)."""
    try:
        ch = project.ch
        idea_id = project.meta.get("idea")
        pillar = next((i.get("pillar") for i in ch.load_ideas()["ideas"] if i["id"] == idea_id), None)
        for sid, s in (ch.data.get("series") or {}).items():
            if pillar and pillar in (s.get("pillars") or []):
                return sid
    except Exception:
        pass
    return ""


def _sync_idea_status(project: Project, meta: dict) -> None:
    idea_id = meta.get("idea")
    if not idea_id or meta.get("status") != "published":
        return
    ch = project.ch
    data = ch.load_ideas()
    for i in data["ideas"]:
        if i["id"] == idea_id and i.get("status") != "published":
            i["status"] = "published"
            ch.save_ideas(data)
            return
