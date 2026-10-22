"""YouTube scan (studio/ytscan.py) with fake yt-dlp calls: topics, new channels, panel API. No network."""
from datetime import date

import pytest

import studio.channel as channel_mod
import studio.config as config_mod
import studio.ytscan as ytscan


@pytest.fixture()
def demo(tmp_path, monkeypatch):
    for m in (config_mod, channel_mod, ytscan):
        monkeypatch.setattr(m, "CHANNELS", tmp_path)
    from studio.channel import Channel, create_channel
    create_channel("demo", "Demo", ["en"])
    ch = Channel("demo")
    ch.save_ideas({"ideas": [{"id": "g001", "title": "Can opener", "query": "how a can opener works", "priority": "A"},
                             {"id": "g002", "title": "Zipper", "priority": "B"}]})
    return ch


def _v(i, views, ch="c1", dur=600):
    return {"id": f"v{i}", "title": f"Video {i}", "channel": f"Chan {ch}", "channel_id": ch, "views": views,
            "duration": dur, "url": f"https://www.youtube.com/watch?v=v{i}", "upload_date": None}


def test_measure_topic_gap():
    today = date(2026, 10, 21)
    vids = [_v(1, 900_000), _v(2, 150_000), _v(3, 2_000)]
    old = {"v1": {"upload_date": "20160101"}, "v2": {"upload_date": "20190505"}}
    s, _ = ytscan.measure_topic("q", find=lambda q, n: [dict(v) for v in vids], more=lambda ids: old, today=today)
    assert s["strong"] == 2 and s["recent_strong_long"] == 0 and s["gap"] and s["median_views"] == 150_000
    new = {"v1": {"upload_date": "20260301"}}
    s, _ = ytscan.measure_topic("q", find=lambda q, n: [dict(v) for v in vids], more=lambda ids: new, today=today)
    assert s["recent_strong_long"] == 1 and not s["gap"]


def test_scan_topics_saves_idea_and_report(demo):
    seen = []
    def find(q, n):
        seen.append(q)
        return [_v(1, 300_000), _v(2, 5_000)]
    ytscan.scan_topics("demo", find=find, more=lambda ids: {"v1": {"upload_date": "20150101"}})
    assert seen == ["how a can opener works", "Zipper"]            # idea query first, else the title; A before B
    ideas = {i["id"]: i for i in channel_mod.Channel("demo").load_ideas()["ideas"]}
    assert ideas["g001"]["scan"]["gap"] is True
    got = ytscan.latest("demo")
    assert [r["id"] for r in got["topics"]["rows"]] == ["g001", "g002"] and "/" in got["topics"]["md"]


def test_new_channels_filters_age_and_size(demo):
    vids = [_v(1, 400_000, "young"), _v(2, 900_000, "old"), _v(3, 30_000, "tiny")]
    first = {"young": "20260101", "old": "20120101", "tiny": "20260601"}.get
    ytscan.scan_new_channels("demo", find=lambda q, n, by_date=False: vids, first=first,
                             more=lambda ids: {i: {"subs": 50_000 if i == "v1" else 100} for i in ids})
    rows = ytscan.latest("demo")["channels"]["rows"]
    assert [r["channel"] for r in rows] == ["Chan young"] and rows[0]["subs"] == 50_000


def test_new_channels_old_best_video_music_and_newest_upload_bug(demo):
    # 22 Oct 2026 report: every giant channel came out "0 months old" because first_upload returned the newest upload
    vids = [_v(1, 9_000_000, "giant"), _v(2, 500_000, "hymns"), _v(3, 400_000, "fresh"), _v(4, 300_000, "liar")]
    meta = {"v1": {"subs": 44_000_000, "upload_date": "20170301"},             # best video 9 years old: not new
            "v2": {"subs": 2_000_000, "upload_date": "20260901", "categories": ["Music"]},
            "v3": {"subs": 80_000, "upload_date": "20260501"},
            "v4": {"subs": 90_000, "upload_date": "20230101"}}
    asked = []
    def first(ch):
        asked.append(ch)
        return {"fresh": "20260101", "liar": "20261020"}.get(ch)              # "liar": a wrong, too-new date
    ytscan.scan_new_channels("demo", find=lambda q, n, by_date=False: vids, first=first,
                             more=lambda ids: {i: meta[i] for i in ids})
    rows = ytscan.latest("demo")["channels"]["rows"]
    assert [r["channel"] for r in rows] == ["Chan fresh"] and rows[0]["first_upload"] == "20260101"
    assert "giant" not in asked and "hymns" not in asked                  # filtered before the slow uploads read
    assert ytscan.months_between("20261020", date(2026, 10, 22)) == 0 and ytscan.months_between(None, date.today()) is None


def test_first_upload_takes_the_oldest(monkeypatch):
    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def extract_info(self, url, download=False):
            assert self.opts.get("extract_flat") and "playlistreverse" not in self.opts
            return {"entries": [{"id": "newestAAAAA"}, {"id": "middleBBBBB"}, {"id": "oldestCCCCC"}]}
    monkeypatch.setattr(ytscan, "_ydl", lambda flat=True, **kw: FakeYDL({"extract_flat": flat, **kw}))
    monkeypatch.setattr(ytscan, "details", lambda ids: {i: {"upload_date": "20190101"} for i in ids if i == "oldestCCCCC"})
    assert ytscan.first_upload("UCx") == "20190101"


def test_seed_queries_from_channel_yaml(demo):
    assert ytscan.seed_queries(demo) == ["how a can opener works", "Zipper"]   # no queries: tags + top ideas
    d = demo.data
    d["research"] = {"scan_queries": ["a", "b"]}
    demo.save(d)
    assert ytscan.seed_queries(demo) == ["a", "b"]


def test_scan_api(demo, monkeypatch):
    from fastapi.testclient import TestClient

    from studio.web import app as app_mod
    calls = []
    class J:
        id = "j1"
    monkeypatch.setattr(app_mod.manager, "submit", lambda args, label, ch, p: calls.append(args) or J())
    c = TestClient(app_mod.app)
    d = c.get("/api/channels/demo/scan").json()
    assert d["topics"] is None and "queries" in d and "ytdlp" in d
    assert c.post("/api/channels/demo/scan", json={"mode": "rm -rf"}).status_code == 400
    assert c.post("/api/channels/demo/scan", json={"mode": "konular", "ids": ["g001", "x;y"]}).json()["job"] == "j1"
    assert calls[-1] == ["scan", "konular", "--channel", "demo", "--only", "g001"]


def test_panel_scripts_are_cache_busted():
    from fastapi.testclient import TestClient

    from studio.web.app import app
    c = TestClient(app)
    html = c.get("/").text
    assert "/static/app.js?v=" in html and "/static/style.css?v=" in html
    assert c.get("/static/app2.js").headers["cache-control"] == "no-cache"
