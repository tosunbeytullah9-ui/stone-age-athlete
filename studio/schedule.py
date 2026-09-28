"""Publishing calendar: slots from channel.yaml → schedule, filled by projects' publish.planned_date."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .channel import Channel
from .project import Project
from .publish import get_publish

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAYS_TR = {"Mon": "Pzt", "Tue": "Sal", "Wed": "Çar", "Thu": "Per", "Fri": "Cum", "Sat": "Cmt", "Sun": "Paz"}


def settings(ch: Channel) -> dict[str, Any]:
    s = dict(ch.data.get("schedule") or {})
    s.setdefault("per_week", 1)
    s.setdefault("days", ["Mon", "Wed", "Fri", "Tue", "Thu", "Sat", "Sun"][: int(s["per_week"])])
    s.setdefault("slot_types", ["long"] * len(s["days"]))
    s.setdefault("hours_per_video", 6.5)
    s.setdefault("hours_per_short", 1.5)
    return s


def _stage(p: Project) -> tuple[str, int]:
    """Short production stage label + 0..100 progress, cheap to compute."""
    from .readiness import check
    langs = p.ch.languages
    if all(p.video_path(lg).exists() for lg in langs[:1]):
        return "video hazır", 100
    try:
        r = check(p)
    except SystemExit:
        return "senaryo", 10
    keys = {c["key"]: c for c in r["checks"]}
    if not keys.get("script", {}).get("ok"):
        return "senaryo", 10
    if "storyboard" in keys and not keys["storyboard"]["ok"]:
        return "bölünecek", 30
    if not keys.get("plan", {}).get("ok"):
        return "görsel planı", 45
    if not keys.get("images", {}).get("ok"):
        return "görseller", 65
    return "ses & video", 80


def calendar(cid: str, weeks: int = 8, start: date | None = None) -> dict[str, Any]:
    ch = Channel(cid)
    st = settings(ch)
    today = date.today()
    monday = (start or today) - timedelta(days=(start or today).weekday())
    projects = []
    for slug in ch.project_slugs():
        p = Project(cid, slug)
        pub = get_publish(p)
        projects.append({"slug": slug, "title": p.meta.get("title", slug), "planned": pub.get("planned_date") or "",
                         "published": pub.get("published_at") or "", "slot": pub.get("slot", "long"),
                         "series": pub.get("series", "")})
    by_date: dict[str, list[dict]] = {}
    for pr in projects:
        d = pr["published"] or pr["planned"]
        if d:
            by_date.setdefault(d, []).append(pr)
    series = ch.data.get("series") or {}
    out_weeks = []
    for w in range(weeks):
        wk_start = monday + timedelta(weeks=w)
        slots = []
        for day, typ in zip(st["days"], st["slot_types"] + ["long"] * 7):
            if day not in DAYS:
                continue
            d = wk_start + timedelta(days=DAYS.index(day))
            items = by_date.pop(d.isoformat(), [])
            slot = {"date": d.isoformat(), "day": DAYS_TR[day], "type": typ, "past": d < today, "items": []}
            for it in items:
                p = Project(cid, it["slug"])
                stage, pct = ("yayında", 100) if it["published"] else _stage(p)
                days_left = (d - today).days
                risk = not it["published"] and pct < 100 and days_left <= 3
                slot["items"].append({**it, "stage": stage, "progress": pct, "risk": risk,
                                      "series_name": (series.get(it["series"]) or {}).get("name", "")})
            slots.append(slot)
        # items on non-slot days of this week
        for k in list(by_date):
            if wk_start.isoformat() <= k < (wk_start + timedelta(days=7)).isoformat():
                for it in by_date.pop(k):
                    p = Project(cid, it["slug"])
                    stage, pct = ("yayında", 100) if it["published"] else _stage(p)
                    slots.append({"date": k, "day": DAYS_TR[DAYS[date.fromisoformat(k).weekday()]], "type": it["slot"],
                                  "past": date.fromisoformat(k) < today, "extra": True,
                                  "items": [{**it, "stage": stage, "progress": pct, "risk": False, "series_name": ""}]})
        slots.sort(key=lambda s: s["date"])
        out_weeks.append({"start": wk_start.isoformat(), "slots": slots})
    unscheduled = [p for p in projects if not p["planned"] and not p["published"]]
    longs = sum(1 for t in st["slot_types"][: len(st["days"])] if t == "long")
    shorts = len(st["days"]) - longs
    hours = longs * float(st["hours_per_video"]) + shorts * float(st["hours_per_short"])
    filled = sum(1 for w in out_weeks[:4] for s in w["slots"] if s["items"])
    needed = sum(1 for w in out_weeks[:4] for s in w["slots"] if not s.get("extra"))
    return {"settings": st, "weeks": out_weeks, "unscheduled": unscheduled, "hours_per_week": round(hours, 1),
            "filled_4w": filled, "slots_4w": needed}


def assign(cid: str, slug: str, day: str | None) -> None:
    from .publish import save_publish
    p = Project(cid, slug)
    save_publish(p, {"planned_date": day or ""})
