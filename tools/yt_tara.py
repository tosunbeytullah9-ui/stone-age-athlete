"""Rakip ve fırsat taraması (yt-dlp, API kotası harcamaz). Sahibin bilgisayarında çalışır.

Kullanım (proje klasöründe):
  .venv\\Scripts\\python tools\\yt_tara.py konular --channel ordinary-genius          # fikir havuzundaki her konu
  .venv\\Scripts\\python tools\\yt_tara.py konular --channel ordinary-genius --only g001,g004
  .venv\\Scripts\\python tools\\yt_tara.py yeni-kanallar --channel ordinary-genius    # yeni açılıp hızlı büyüyen kanallar
  .venv\\Scripts\\python tools\\yt_tara.py kapaklar --channel ordinary-genius         # öne çıkan videoların kapakları

Çıktılar `channels/<kanal>/research/` klasörüne yazılır (Markdown + CSV; kapaklar için resimler ve bir kontak sayfası).
Bu dosyalar Claude'a verilir: konuların sırası, açısı ve kapak dili bunlara göre seçilir.

konular        Her fikir için YouTube aramasındaki ilk N video: izlenme, yükleme yılı, kanal, süre. Sonuç:
               güçlü video sayısı (≥100 bin), en büyük video, son 2 yılda güçlü video var mı, en iyi 5 başlık.
               "Boşluk" = konu aranıyor ama son iki yılda güçlü, ayrıntılı (8 dk+) bir video yok.
yeni-kanallar  Konu aramalarından son 12 ayın videoları toplanır; kanalların ilk videosunun tarihi ve abonesi
               bulunur. 24 aydan genç olup 10 bin abone ya da 100 bin izlenmeli videoya ulaşanlar listelenir.
kapaklar       konular taramasındaki en çok izlenen videoların kapak resimlerini indirir (sadece incelemek için;
               yeniden kullanılmaz) ve tek bir kontak sayfası yapar.

Gerekenler: pip install yt-dlp (requirements.txt içinde). İnternet bağlantısı.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
from datetime import date, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STRONG = 100_000


def _ydl(flat: bool = True):
    try:
        import yt_dlp
    except ImportError:
        sys.exit("yt-dlp kurulu değil: .venv\\Scripts\\pip install yt-dlp")
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "ignoreerrors": True}
    if flat:
        opts["extract_flat"] = "in_playlist"
    return yt_dlp.YoutubeDL(opts)


def _ideas(cid: str, only: set[str] | None) -> list[dict]:
    data = yaml.safe_load((ROOT / "channels" / cid / "ideas.yaml").read_text(encoding="utf-8")) or {}
    out = []
    for it in data.get("ideas") or []:
        if only and it.get("id") not in only:
            continue
        if it.get("status") in ("dropped",):
            continue
        out.append(it)
    return out


def _year(d: str | None) -> int | None:
    return int(d[:4]) if d and len(d) >= 4 and d[:4].isdigit() else None


def search(query: str, n: int = 20, by_date: bool = False) -> list[dict]:
    with _ydl(flat=True) as y:
        info = y.extract_info(f"ytsearch{'date' if by_date else ''}{n}:{query}", download=False) or {}
    vids = []
    for e in info.get("entries") or []:
        if not e or e.get("ie_key", "Youtube") not in ("Youtube", None) or not e.get("id"):
            continue
        vids.append({"id": e["id"], "title": e.get("title") or "", "channel": e.get("channel") or e.get("uploader") or "",
                     "channel_id": e.get("channel_id") or "", "views": int(e.get("view_count") or 0),
                     "duration": int(e.get("duration") or 0), "url": f"https://www.youtube.com/watch?v={e['id']}",
                     "upload_date": e.get("upload_date")})
    return vids


def details(video_ids: list[str]) -> dict[str, dict]:
    """Full metadata (upload date, subscriber count, thumbnail) for a few videos."""
    out = {}
    with _ydl(flat=False) as y:
        for vid in video_ids:
            info = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            if info:
                out[vid] = {"upload_date": info.get("upload_date"), "subs": int(info.get("channel_follower_count") or 0),
                            "thumbnail": info.get("thumbnail"), "views": int(info.get("view_count") or 0),
                            "channel_id": info.get("channel_id")}
            time.sleep(0.5)
    return out


# ------------------------------------------------------------------ konular
def scan_topics(cid: str, only: set[str] | None, n: int) -> Path:
    rows, md = [], [f"# Rakip taraması: {cid} ({date.today().isoformat()})", "",
                    f"Her konu için YouTube aramasının ilk {n} videosu. Güçlü = en az {STRONG:,} izlenme. "
                    "Boşluk: arama talebi var ama son iki yılda 8 dakikadan uzun güçlü bir video yok.", ""]
    this_year = date.today().year
    for idea in _ideas(cid, only):
        q = idea.get("query") or idea.get("title")
        vids = search(q, n)
        top = sorted(vids, key=lambda v: -v["views"])[:8]
        det = details([v["id"] for v in top])
        for v in top:
            v.update({k: x for k, x in det.get(v["id"], {}).items() if x})
        strong = [v for v in vids if v["views"] >= STRONG]
        recent_strong_long = [v for v in top if v["views"] >= STRONG and (_year(v.get("upload_date")) or 0) >= this_year - 1
                              and v["duration"] >= 480]
        med = int(statistics.median([v["views"] for v in vids])) if vids else 0
        gap = bool(strong) and not recent_strong_long
        row = {"id": idea.get("id"), "title": idea.get("title"), "query": q, "results": len(vids), "median_views": med,
               "top_views": top[0]["views"] if top else 0, "strong": len(strong),
               "recent_strong_long": len(recent_strong_long), "gap": "EVET" if gap else "",
               "top_channel": top[0]["channel"] if top else "", "top_year": _year(top[0].get("upload_date")) if top else ""}
        rows.append(row)
        md += [f"## {idea.get('id')} · {idea.get('title')}", f"Arama: `{q}` · medyan {med:,} · en büyük "
               f"{row['top_views']:,} · güçlü {len(strong)} · son 2 yılda güçlü+uzun {len(recent_strong_long)}"
               + (" · **BOŞLUK**" if gap else ""), ""]
        for v in top[:5]:
            md.append(f"- [{v['title']}]({v['url']}) — {v['channel']} · {v['views']:,} izlenme · "
                      f"{_year(v.get('upload_date')) or '?'} · {v['duration'] // 60} dk")
        md.append("")
        print(f"  {idea.get('id')}: güçlü {len(strong)}, boşluk {'evet' if gap else 'hayır'}")
    out_dir = ROOT / "channels" / cid / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    with (out_dir / f"rakip-{stamp}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["id"])
        w.writeheader()
        w.writerows(rows)
    path = out_dir / f"rakip-{stamp}.md"
    path.write_text("\n".join(md), encoding="utf-8")
    return path


# ------------------------------------------------------------------ yeni kanallar
SEED_QUERIES = ["how does it work everyday objects", "how everyday things work", "physics of everyday things",
                "why is it designed this way", "how a kitchen tool works", "engineering of everyday objects",
                "how things work animation", "the genius design of", "you never noticed this design",
                "how does a household appliance work"]


def first_upload(channel_id: str) -> str | None:
    """Date of the channel's oldest video: its uploads list reversed, first item, fully extracted."""
    import yt_dlp
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "ignoreerrors": True,
            "playlistreverse": True, "playlist_items": "1"}
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(f"https://www.youtube.com/channel/{channel_id}/videos", download=False) or {}
    entries = [e for e in (info.get("entries") or []) if e]
    return entries[0].get("upload_date") if entries else None


def scan_new_channels(cid: str, extra_queries: list[str], per_query: int = 40) -> Path:
    seen: dict[str, dict] = {}
    for q in SEED_QUERIES + extra_queries:
        for v in search(q, per_query, by_date=True):
            if v["channel_id"]:
                c = seen.setdefault(v["channel_id"], {"channel": v["channel"], "best": 0, "best_title": "", "best_url": ""})
                if v["views"] > c["best"]:
                    c.update(best=v["views"], best_title=v["title"], best_url=v["url"], best_id=v["id"])
        print(f"  arama: {q} → {len(seen)} kanal")
    today = date.today()
    rows = []
    for ch_id, c in sorted(seen.items(), key=lambda kv: -kv[1]["best"])[:120]:
        if c["best"] < 20_000:
            continue
        det = details([c["best_id"]]).get(c["best_id"], {})
        first = first_upload(ch_id)
        if not first:
            continue
        age_m = (today.year - int(first[:4])) * 12 + today.month - int(first[4:6])
        if age_m > 24:
            continue
        subs = det.get("subs", 0)
        if subs < 10_000 and c["best"] < STRONG:
            continue
        rows.append({"channel": c["channel"], "url": f"https://www.youtube.com/channel/{ch_id}", "first_upload": first,
                     "age_months": age_m, "subs": subs, "best_views": c["best"], "best_title": c["best_title"],
                     "best_url": c["best_url"], "subs_per_month": round(subs / max(1, age_m))})
        time.sleep(0.5)
    rows.sort(key=lambda r: -r["subs_per_month"])
    out_dir = ROOT / "channels" / cid / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    md = [f"# Yeni ve hızlı büyüyen kanallar ({stamp})", "",
          "İlk videosu son 24 ay içinde olan, 10 bin aboneye ya da 100 bin izlenmeli bir videoya ulaşmış kanallar.", "",
          "| Kanal | İlk video | Ay | Abone | Abone/ay | En iyi video |", "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        md.append(f"| [{r['channel']}]({r['url']}) | {r['first_upload']} | {r['age_months']} | {r['subs']:,} | "
                  f"{r['subs_per_month']:,} | [{r['best_title'][:60]}]({r['best_url']}) ({r['best_views']:,}) |")
    if rows:
        with (out_dir / f"yeni-kanallar-{stamp}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    path = out_dir / f"yeni-kanallar-{stamp}.md"
    path.write_text("\n".join(md), encoding="utf-8")
    return path


# ------------------------------------------------------------------ kapaklar
def grab_thumbnails(cid: str, only: set[str] | None, per_topic: int = 3) -> Path:
    import requests
    from PIL import Image, ImageDraw
    out_dir = ROOT / "channels" / cid / "research" / "kapaklar"
    out_dir.mkdir(parents=True, exist_ok=True)
    tiles = []
    for idea in _ideas(cid, only):
        vids = sorted(search(idea.get("query") or idea.get("title"), 15), key=lambda v: -v["views"])[:per_topic]
        for v in vids:
            url = f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg"
            p = out_dir / f"{idea.get('id')}_{v['id']}.jpg"
            if not p.exists():
                r = requests.get(url, timeout=20)
                if r.status_code == 200:
                    p.write_bytes(r.content)
            if p.exists():
                tiles.append((p, f"{v['views'] // 1000}k · {v['channel'][:22]}"))
    if not tiles:
        sys.exit("kapak bulunamadı")
    cols, tw, th = 6, 320, 180
    sheet = Image.new("RGB", (cols * tw, ((len(tiles) + cols - 1) // cols) * (th + 22)), "white")
    d = ImageDraw.Draw(sheet)
    for i, (p, label) in enumerate(tiles):
        im = Image.open(p).convert("RGB").resize((tw, th))
        x, y = (i % cols) * tw, (i // cols) * (th + 22)
        sheet.paste(im, (x, y))
        d.text((x + 4, y + th + 4), label, fill="black")
    path = out_dir / "kontak.jpg"
    sheet.save(path, quality=88)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["konular", "yeni-kanallar", "kapaklar"])
    ap.add_argument("--channel", required=True)
    ap.add_argument("--only", default="", help="virgülle fikir id'leri (g001,g004)")
    ap.add_argument("-n", type=int, default=20, help="konu başına incelenen arama sonucu")
    ap.add_argument("--query", action="append", default=[], help="yeni-kanallar: ek arama ifadesi")
    a = ap.parse_args()
    only = {x.strip() for x in a.only.split(",") if x.strip()} or None
    if a.mode == "konular":
        print("Rapor:", scan_topics(a.channel, only, a.n))
    elif a.mode == "yeni-kanallar":
        print("Rapor:", scan_new_channels(a.channel, a.query))
    else:
        print("Kontak sayfası:", grab_thumbnails(a.channel, only))


if __name__ == "__main__":
    main()
