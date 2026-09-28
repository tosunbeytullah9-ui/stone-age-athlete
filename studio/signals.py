"""Demand and competition signals for ideas, from the official YouTube Data API v3 (free key, daily quota).

For each idea one search (100 quota units) + video and channel statistics (2 units): with the default quota of
10,000 units/day that is ~95 ideas per day. Ideas checked in the last 30 days are skipped.

Stored per idea in ideas.yaml → signals:
  query           what was searched (idea.query, else the title)
  results         videos looked at (top 25 by relevance)
  median_views    typical views of what the search shows = demand
  top_views       the biggest video
  recent_12m      how many of those were published in the last 12 months = how crowded the topic is now
  outlier         best views ÷ subscribers among channels under 250k subscribers: small channels winning here = gap
  big_channels    results from channels over 1M subscribers
  demand / competition / gap   1..5 bands of the numbers above (bands, not a weighted score — you decide)
  checked         date
"""
from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

import requests

from .channel import Channel
from .config import secret

API = "https://www.googleapis.com/youtube/v3"


def _get(path: str, params: dict, key: str) -> dict:
    r = requests.get(f"{API}/{path}", params={**params, "key": key}, timeout=30)
    if r.status_code == 403 and "quota" in r.text.lower():
        raise QuotaExceeded(r.text[:200])
    if r.status_code != 200:
        raise SystemExit(f"YouTube API hatası {r.status_code}: {r.text[:300]}")
    return r.json()


class QuotaExceeded(Exception):
    pass


def _band(v: float, edges: list[float]) -> int:
    return 1 + sum(v >= e for e in edges)


def measure(query: str, key: str, fetch: Callable = _get, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    s = fetch("search", {"part": "snippet", "q": query, "type": "video", "maxResults": 25,
                         "order": "relevance", "relevanceLanguage": "en", "safeSearch": "none"}, key)
    ids = [it["id"]["videoId"] for it in s.get("items", []) if it.get("id", {}).get("videoId")]
    if not ids:
        return {"query": query, "results": 0, "median_views": 0, "top_views": 0, "recent_12m": 0, "outlier": 0,
                "big_channels": 0, "demand": 1, "competition": 1, "gap": 3, "checked": today.isoformat()}
    v = fetch("videos", {"part": "statistics,snippet", "id": ",".join(ids)}, key)
    vids = []
    for it in v.get("items", []):
        vids.append({"views": int(it.get("statistics", {}).get("viewCount", 0) or 0),
                     "channel": it["snippet"]["channelId"], "published": it["snippet"]["publishedAt"][:10]})
    chan_ids = sorted({x["channel"] for x in vids})
    c = fetch("channels", {"part": "statistics", "id": ",".join(chan_ids[:50])}, key)
    subs = {it["id"]: int(it.get("statistics", {}).get("subscriberCount", 0) or 0) for it in c.get("items", [])}
    views = [x["views"] for x in vids]
    cutoff = (today - timedelta(days=365)).isoformat()
    recent = sum(1 for x in vids if x["published"] >= cutoff)
    ratios = [x["views"] / max(subs.get(x["channel"], 0), 1000) for x in vids if subs.get(x["channel"], 0) < 250_000]
    outlier = round(max(ratios), 1) if ratios else 0.0
    big = sum(1 for x in vids if subs.get(x["channel"], 0) >= 1_000_000)
    med = int(statistics.median(views)) if views else 0
    demand = _band(med, [10_000, 50_000, 200_000, 1_000_000])
    competition = _band(recent + 2 * big, [4, 8, 13, 19])
    gap = _band(outlier, [1, 3, 10, 30])
    return {"query": query, "results": len(vids), "median_views": med, "top_views": max(views) if views else 0,
            "recent_12m": recent, "outlier": outlier, "big_channels": big, "demand": demand,
            "competition": competition, "gap": gap, "checked": today.isoformat()}


def update_signals(cid: str, limit: int | None = None, ids: list[str] | None = None, force: bool = False,
                   fetch: Callable = _get, key: str | None = None) -> list[str]:
    key = key or secret("YOUTUBE_API_KEY")
    ch = Channel(cid)
    data = ch.load_ideas()
    rank = {"A": 0, "B": 1, "C": 2}
    todo = [i for i in data["ideas"] if i.get("status", "idea") not in ("published", "dropped")]
    if ids:
        todo = [i for i in todo if i["id"] in ids]
    fresh = (date.today() - timedelta(days=30)).isoformat()
    if not force:
        todo = [i for i in todo if (i.get("signals") or {}).get("checked", "") < fresh]
    todo.sort(key=lambda i: (rank.get(i.get("priority"), 1), i["id"]))
    if limit:
        todo = todo[:limit]
    done: list[str] = []
    print(f"  {len(todo)} fikir kontrol edilecek (~{len(todo) * 102} kota birimi / günlük 10.000)")
    for n, idea in enumerate(todo, 1):
        q = idea.get("query") or idea["title"]
        try:
            idea["signals"] = measure(q, key, fetch)
        except QuotaExceeded:
            print("  Günlük YouTube kotası doldu. Kalanlar yarın (kaldığı yerden devam eder).")
            break
        sg = idea["signals"]
        print(f"  {n}/{len(todo)} {idea['id']} talep {sg['demand']} · rekabet {sg['competition']} · "
              f"boşluk {sg['gap']} · medyan {sg['median_views']:,} izlenme — {idea['title'][:50]}")
        done.append(idea["id"])
        ch.save_ideas(data)                     # save after each idea: an interrupted run keeps its work
    return done


def now_utc() -> datetime:  # pragma: no cover
    return datetime.now(timezone.utc)
