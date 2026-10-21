"""YouTube taraması (yt-dlp): rakip videolar, yeni ve hızlı büyüyen kanallar, rakip kapakları. Her kanal için çalışır;
API kotası harcamaz (YouTube Data API ile ölçülen talep bantları ayrıca `signals`).

  python -m studio scan konular --channel C [--only g001,g002] [--limit N]
  python -m studio scan yeni-kanallar --channel C
  python -m studio scan kapaklar --channel C [--only ...]
Panel: Kanal → YouTube taraması (üç düğme ve son sonuçlar).

konular        Her fikir için YouTube aramasının ilk 20 videosu: izlenme, yükleme yılı, kanal, süre. Sonuç fikrin
               `scan` alanına yazılır (ideas.yaml; panelde Fikir havuzu → Sinyal sütunu) ve bir rapora:
               güçlü video sayısı (≥100 bin), en büyük video, en iyi 5 başlık ve BOŞLUK = konu izleniyor ama son iki
               yılda 8 dakikadan uzun güçlü bir video yok.
yeni-kanallar  Kanalın arama ifadelerinden (channel.yaml → research.scan_queries; yoksa etiketler ve fikirler) son
               videolar toplanır; ilk videosu son 24 ay içinde olup 10 bin aboneye ya da 100 bin izlenmeli bir videoya
               ulaşan kanallar aylık abone hızına göre listelenir.
kapaklar       En çok izlenen rakip videoların kapakları indirilir (yalnızca incelemek için) ve tek bir kontak sayfası
               (research/kapaklar/kontak.jpg) yapılır.

Çıktılar: channels/<kanal>/research/ (Markdown + CSV + JSON). Gerekenler: yt-dlp (requirements.txt), internet.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from datetime import date
from pathlib import Path
from typing import Callable

from .channel import Channel
from .config import CHANNELS

STRONG = 100_000
LONG = 480                       # saniye: 8 dakikadan uzun = ara reklam alabilen, ayrıntılı video
MODES = ("konular", "yeni-kanallar", "kapaklar")


def research_dir(cid: str) -> Path:
    d = CHANNELS / cid / "research"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ------------------------------------------------------------------ yt-dlp
def _ydl(flat: bool = True, **extra):
    try:
        import yt_dlp
    except ImportError:
        raise SystemExit("yt-dlp kurulu değil. Kur: .venv\\Scripts\\pip install yt-dlp  (ya da guncelle.bat)")
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "ignoreerrors": True, **extra}
    if flat:
        opts["extract_flat"] = "in_playlist"
    return yt_dlp.YoutubeDL(opts)


def search(query: str, n: int = 20, by_date: bool = False) -> list[dict]:
    with _ydl(flat=True) as y:
        info = y.extract_info(f"ytsearch{'date' if by_date else ''}{n}:{query}", download=False) or {}
    vids = []
    for e in info.get("entries") or []:
        if not e or not e.get("id") or len(str(e["id"])) != 11:
            continue
        vids.append({"id": e["id"], "title": e.get("title") or "", "channel": e.get("channel") or e.get("uploader") or "",
                     "channel_id": e.get("channel_id") or "", "views": int(e.get("view_count") or 0),
                     "duration": int(e.get("duration") or 0), "url": f"https://www.youtube.com/watch?v={e['id']}",
                     "upload_date": e.get("upload_date")})
    return vids


def details(video_ids: list[str]) -> dict[str, dict]:
    """Full metadata (upload date, subscriber count) for a few videos."""
    out = {}
    with _ydl(flat=False) as y:
        for vid in video_ids:
            info = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            if info:
                out[vid] = {"upload_date": info.get("upload_date"), "subs": int(info.get("channel_follower_count") or 0),
                            "views": int(info.get("view_count") or 0), "duration": int(info.get("duration") or 0),
                            "channel_id": info.get("channel_id")}
            time.sleep(0.4)
    return out


def first_upload(channel_id: str) -> str | None:
    """Date of a channel's oldest video (its uploads reversed, first item)."""
    with _ydl(flat=False, playlistreverse=True, playlist_items="1") as y:
        info = y.extract_info(f"https://www.youtube.com/channel/{channel_id}/videos", download=False) or {}
    entries = [e for e in (info.get("entries") or []) if e]
    return entries[0].get("upload_date") if entries else None


def _year(d: str | None) -> int | None:
    return int(d[:4]) if d and len(d) >= 4 and d[:4].isdigit() else None


def _todo(ch: Channel, ids: list[str] | None, limit: int | None) -> tuple[dict, list[dict]]:
    data = ch.load_ideas()
    rank = {"A": 0, "B": 1, "C": 2}
    todo = [i for i in data.get("ideas") or [] if i.get("status", "idea") not in ("dropped",)]
    if ids:
        todo = [i for i in todo if i["id"] in ids]
    todo.sort(key=lambda i: (rank.get(i.get("priority"), 1), i["id"]))
    return data, todo[:limit] if limit else todo


# ------------------------------------------------------------------ konular
def measure_topic(query: str, n: int = 20, today: date | None = None, find: Callable = search,
                  more: Callable = details) -> tuple[dict, list[dict]]:
    """→ (summary stored on the idea, the top videos for the report)."""
    today = today or date.today()
    vids = find(query, n)
    top = sorted(vids, key=lambda v: -v["views"])[:8]
    det = more([v["id"] for v in top]) if top else {}
    for v in top:
        v.update({k: x for k, x in det.get(v["id"], {}).items() if x})
    strong = [v for v in vids if v["views"] >= STRONG]
    recent_long = [v for v in top if v["views"] >= STRONG and (_year(v.get("upload_date")) or 0) >= today.year - 1
                   and v.get("duration", 0) >= LONG]
    med = int(statistics.median([v["views"] for v in vids])) if vids else 0
    summary = {"query": query, "results": len(vids), "median_views": med, "top_views": top[0]["views"] if top else 0,
               "strong": len(strong), "recent_strong_long": len(recent_long),
               "gap": bool(strong) and not recent_long,
               "top": [{"title": v["title"][:90], "channel": v["channel"], "views": v["views"],
                        "year": _year(v.get("upload_date")), "minutes": v.get("duration", 0) // 60, "url": v["url"]}
                       for v in top[:5]],
               "checked": today.isoformat()}
    return summary, top


def scan_topics(cid: str, ids: list[str] | None = None, limit: int | None = None, n: int = 20,
                find: Callable = search, more: Callable = details) -> Path:
    ch = Channel(cid)
    data, todo = _todo(ch, ids, limit)
    print(f"  {len(todo)} konu taranacak (konu başına ~20–40 sn)")
    rows: list[dict] = []
    for k, idea in enumerate(todo, 1):
        q = idea.get("query") or idea["title"]
        try:
            s, _ = measure_topic(q, n, find=find, more=more)
        except SystemExit:
            raise
        except Exception as e:                      # YouTube can refuse one request: go on with the next idea
            print(f"  {k}/{len(todo)} {idea['id']}: atlandı ({str(e)[:120]})")
            continue
        idea["scan"] = s
        ch.save_ideas(data)                         # save after each idea: an interrupted run keeps its work
        rows.append({"id": idea["id"], "title": idea["title"], **{x: s[x] for x in
                     ("query", "results", "median_views", "top_views", "strong", "recent_strong_long", "gap")}})
        print(f"  {k}/{len(todo)} {idea['id']}: güçlü {s['strong']}, son 2 yılda güçlü+uzun {s['recent_strong_long']}"
              f"{' · BOŞLUK' if s['gap'] else ''} — {idea['title'][:50]}")
    return _report_topics(cid, data, rows)


def _report_topics(cid: str, data: dict, rows: list[dict]) -> Path:
    out = research_dir(cid)
    stamp = date.today().isoformat()
    by_id = {i["id"]: i for i in data.get("ideas") or []}
    md = [f"# Rakip taraması · {cid} · {stamp}", "",
          f"Her konu için YouTube aramasının ilk videoları. Güçlü = en az {STRONG:,} izlenme. **BOŞLUK** = konu "
          "izleniyor ama son iki yılda 8 dakikadan uzun güçlü bir video yok.", ""]
    for r in sorted(rows, key=lambda r: (not r["gap"], -r["median_views"])):
        s = by_id[r["id"]]["scan"]
        md += [f"## {r['id']} · {r['title']}", f"Arama: `{s['query']}` · medyan {s['median_views']:,} · en büyük "
               f"{s['top_views']:,} · güçlü {s['strong']} · son 2 yılda güçlü+uzun {s['recent_strong_long']}"
               + (" · **BOŞLUK**" if s["gap"] else ""), ""]
        md += [f"- [{v['title']}]({v['url']}) — {v['channel']} · {v['views']:,} izlenme · {v['year'] or '?'} · "
               f"{v['minutes']} dk" for v in s["top"]] + [""]
    if rows:
        with (out / f"rakip-{stamp}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    (out / f"rakip-{stamp}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    path = out / f"rakip-{stamp}.md"
    path.write_text("\n".join(md), encoding="utf-8")
    print(f"  rapor: {path}")
    return path


# ------------------------------------------------------------------ yeni kanallar
def seed_queries(ch: Channel) -> list[str]:
    """channel.yaml → research.scan_queries; otherwise the channel's tags and its top ideas' searches."""
    d = ch.data or {}
    qs = list(((d.get("research") or {}).get("scan_queries")) or [])
    if qs:
        return qs
    tags = [t for t in ((d.get("youtube") or {}).get("tags") or []) if isinstance(t, str)][:6]
    _, todo = _todo(ch, None, 6)
    return tags + [i.get("query") or i["title"] for i in todo]


def scan_new_channels(cid: str, extra: list[str] | None = None, per_query: int = 40, max_age: int = 24,
                      find: Callable = search, more: Callable = details, first: Callable = first_upload) -> Path:
    ch = Channel(cid)
    queries = seed_queries(ch) + list(extra or [])
    seen: dict[str, dict] = {}
    for q in queries:
        try:
            vids = find(q, per_query, by_date=True)
        except Exception as e:
            print(f"  arama atlandı: {q} ({str(e)[:80]})")
            continue
        for v in vids:
            if not v["channel_id"]:
                continue
            c = seen.setdefault(v["channel_id"], {"channel": v["channel"], "best": -1})
            if v["views"] > c["best"]:
                c.update(best=v["views"], best_title=v["title"], best_url=v["url"], best_id=v["id"])
        print(f"  arama: {q} → {len(seen)} kanal")
    today = date.today()
    rows = []
    for ch_id, c in sorted(seen.items(), key=lambda kv: -kv[1]["best"])[:120]:
        if c["best"] < 20_000:
            continue
        try:
            fu = first(ch_id)
            det = more([c["best_id"]]).get(c["best_id"], {})
        except Exception:
            continue
        if not fu:
            continue
        age = (today.year - int(fu[:4])) * 12 + today.month - int(fu[4:6])
        subs = det.get("subs", 0)
        if age > max_age or (subs < 10_000 and c["best"] < STRONG):
            continue
        rows.append({"channel": c["channel"], "url": f"https://www.youtube.com/channel/{ch_id}", "first_upload": fu,
                     "age_months": age, "subs": subs, "subs_per_month": round(subs / max(1, age)),
                     "best_views": c["best"], "best_title": c["best_title"], "best_url": c["best_url"]})
        print(f"  yeni kanal: {c['channel']} · {age} ay · {subs:,} abone")
    rows.sort(key=lambda r: -r["subs_per_month"])
    out = research_dir(cid)
    stamp = today.isoformat()
    md = [f"# Yeni ve hızlı büyüyen kanallar · {cid} · {stamp}", "",
          f"İlk videosu son {max_age} ay içinde olan, 10 bin aboneye ya da 100 bin izlenmeli bir videoya ulaşmış "
          f"kanallar. Aramalar: {', '.join(queries)}", "",
          "| Kanal | İlk video | Ay | Abone | Abone/ay | En iyi video |", "| --- | --- | --- | --- | --- | --- |"]
    md += [f"| [{r['channel']}]({r['url']}) | {r['first_upload']} | {r['age_months']} | {r['subs']:,} | "
           f"{r['subs_per_month']:,} | [{r['best_title'][:60]}]({r['best_url']}) ({r['best_views']:,}) |" for r in rows]
    if not rows:
        md.append("| (bulunamadı) | | | | | |")
    (out / f"yeni-kanallar-{stamp}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    if rows:
        with (out / f"yeni-kanallar-{stamp}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    path = out / f"yeni-kanallar-{stamp}.md"
    path.write_text("\n".join(md), encoding="utf-8")
    print(f"  rapor: {path}")
    return path


# ------------------------------------------------------------------ kapaklar
def grab_thumbnails(cid: str, ids: list[str] | None = None, per_topic: int = 3, limit: int | None = 24,
                    find: Callable = search) -> Path:
    import requests
    from PIL import Image, ImageDraw
    ch = Channel(cid)
    data, todo = _todo(ch, ids, limit)
    out = research_dir(cid) / "kapaklar"
    out.mkdir(parents=True, exist_ok=True)
    tiles = []
    for idea in todo:
        scan = idea.get("scan") or {}
        if scan.get("top"):                      # reuse the topic scan when it exists
            vids = [{"id": v["url"].rsplit("=", 1)[-1], "views": v["views"], "channel": v["channel"]}
                    for v in scan["top"][:per_topic]]
        else:
            vids = sorted(find(idea.get("query") or idea["title"], 15), key=lambda v: -v["views"])[:per_topic]
        for v in vids:
            p = out / f"{idea['id']}_{v['id']}.jpg"
            if not p.exists():
                r = requests.get(f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg", timeout=20)
                if r.status_code == 200:
                    p.write_bytes(r.content)
            if p.exists():
                tiles.append((p, f"{idea['id']} · {v['views'] // 1000:,}k · {v['channel'][:20]}"))
        print(f"  {idea['id']}: {len(vids)} kapak")
    if not tiles:
        raise SystemExit("kapak bulunamadı")
    cols, tw, th = 6, 320, 180
    sheet = Image.new("RGB", (cols * tw, ((len(tiles) + cols - 1) // cols) * (th + 24)), "white")
    d = ImageDraw.Draw(sheet)
    for i, (p, lab) in enumerate(tiles):
        im = Image.open(p).convert("RGB")
        w, h = im.size                            # hqdefault has black bars: crop to 16:9
        im = im.crop((0, (h - w * 9 // 16) // 2, w, (h + w * 9 // 16) // 2)).resize((tw, th))
        x, y = (i % cols) * tw, (i // cols) * (th + 24)
        sheet.paste(im, (x, y))
        d.text((x + 4, y + th + 5), lab, fill="black")
    path = out / "kontak.jpg"
    sheet.save(path, quality=88)
    print(f"  kontak sayfası: {path}")
    return path


# ------------------------------------------------------------------ panel
def latest(cid: str) -> dict:
    """What the panel shows: the newest report of each kind."""
    d = CHANNELS / cid / "research"
    res: dict = {"topics": None, "channels": None, "thumbs": None}
    if not d.exists():
        return res
    for key, prefix in (("topics", "rakip-"), ("channels", "yeni-kanallar-")):
        files = sorted(d.glob(f"{prefix}*.json"))
        if files:
            f = files[-1]
            res[key] = {"date": f.stem[len(prefix):], "rows": json.loads(f.read_text(encoding="utf-8")),
                        "md": f.with_suffix(".md").relative_to(CHANNELS.parent).as_posix()}
    k = d / "kapaklar" / "kontak.jpg"
    if k.exists():
        res["thumbs"] = {"path": k.relative_to(CHANNELS.parent).as_posix(), "mtime": int(k.stat().st_mtime)}
    return res


def run(mode: str, cid: str, ids: list[str] | None = None, limit: int | None = None,
        extra: list[str] | None = None) -> Path:
    if mode not in MODES:
        raise SystemExit(f"tarama türü: {', '.join(MODES)}")
    if mode == "konular":
        return scan_topics(cid, ids, limit)
    if mode == "yeni-kanallar":
        return scan_new_channels(cid, extra)
    return grab_thumbnails(cid, ids, limit=limit or 24)


if __name__ == "__main__":  # pragma: no cover
    run(sys.argv[1], sys.argv[2])
