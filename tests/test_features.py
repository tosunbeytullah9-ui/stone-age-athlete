"""Claims + library, publish record, calendar, retention import, signals, thumbnails text, re-split safety, captions."""
import json
from datetime import date

import pytest
from PIL import Image

import studio.channel as channel_mod
import studio.claims as claims_mod
import studio.config as config_mod


@pytest.fixture()
def proj(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CHANNELS", tmp_path / "channels")
    monkeypatch.setattr(channel_mod, "CHANNELS", tmp_path / "channels")
    monkeypatch.setattr(claims_mod, "LIBRARY", tmp_path / "library" / "sources.yaml")
    from studio.channel import create_channel
    from studio.project import create_project
    from studio.storyboard import build_storyboard
    ch = create_channel("demo", "Demo", ["en", "tr"])
    d = ch.data
    d["series"] = {"limits": {"name": "Human Limits", "pillars": ["P3"]}}
    d["schedule"] = {"per_week": 2, "days": ["Mon", "Thu"], "slot_types": ["long", "short"]}
    ch.save(d)
    ch.save_ideas({"pillars": {"P3": {"name": "Extreme"}}, "ideas": [{"id": "i001", "title": "Bajau", "pillar": "P3"}]})
    p = create_project("demo", "Bajau", idea_id="i001")
    p.script_path.write_text("# Bajau\n<!-- multi\nline comment -->\n\nTheir spleens are 50 percent larger. They dive all day.\n\n"
                             "Children learn by watching. The sea shaped them.\n", encoding="utf-8")
    build_storyboard(p, config_mod.load_config("demo"))
    return p


def test_claims_apply_and_gate(proj):
    from studio.claims import apply_reply, claim_checks, cited_sources, library_index
    r = apply_reply(proj, {
        "sources": [{"id": "ilardo2018", "title": "Adaptations", "year": 2018, "type": "primary", "url": "https://x.org"},
                    {"id": "news1", "title": "News", "type": "news", "url": "https://n.org"}],
        "claims": [{"text": "Spleens 50% larger", "source": "ilardo2018", "shots": ["s001"]},
                   {"text": "Unknown", "source": "nope"}]})
    assert r == {"sources_added": 2, "claims": 2}
    assert set(library_index()) == {"ilardo2018", "news1"}
    checks = {c["key"]: c for c in claim_checks(proj)}
    assert not checks["claims_sources"]["ok"] and "nope" in checks["claims_sources"]["message"]
    assert not checks["claims_count"]["ok"]
    assert [s["id"] for s in cited_sources(proj)] == ["ilardo2018"]
    # applying again never overwrites a library entry and keeps verified flags
    from studio.claims import load_claims, save_claims
    d = load_claims(proj)
    d["claims"][0]["verified"] = True
    save_claims(proj, d)
    apply_reply(proj, {"sources": [{"id": "ilardo2018", "title": "CHANGED"}],
                       "claims": [{"text": "Spleens 50% larger", "source": "ilardo2018"}]})
    assert library_index()["ilardo2018"]["title"] == "Adaptations"
    assert load_claims(proj)["claims"][0]["verified"] is True


def test_resplit_keeps_translations_and_remaps(proj):
    from studio.claims import load_claims, save_claims
    from studio.storyboard import build_storyboard
    sb = proj.load_storyboard()
    assert all("multi" not in s["text"] and "comment" not in s["text"] for s in sb["shots"])
    for s in sb["shots"]:
        s["i18n"] = {"tr": "çeviri " + s["id"]}
        s["visual"] = {"prompt": "the sea"}
    proj.save_storyboard(sb)
    last = sb["shots"][-1]["id"]
    meta = proj.meta
    meta["shorts"] = [{"title": "x", "from": "s001", "to": last}]
    proj.save_meta(meta)
    save_claims(proj, {"claims": [{"id": "c01", "text": "t", "source": "a", "shots": [last]}]})
    proj.script_path.write_text("# Bajau\n\nA brand new first sentence here.\n\n" +
                                proj.script_path.read_text(encoding="utf-8").split("\n\n", 1)[1], encoding="utf-8")
    sb2 = build_storyboard(proj, config_mod.load_config("demo"))
    kept = [s for s in sb2["shots"] if s.get("i18n")]
    assert len(kept) == len(sb["shots"])
    new_last = sb2["shots"][-1]["id"]
    assert new_last != last
    assert proj.meta["shorts"][0]["to"] == new_last
    assert load_claims(proj)["claims"][0]["shots"] == [new_last]


def test_publish_and_calendar(proj):
    from studio.publish import add_metrics, get_publish, save_publish
    from studio.schedule import calendar
    assert get_publish(proj)["series"] == "limits"
    today = date.today().isoformat()
    save_publish(proj, {"planned_date": today, "title_used": "Better Title"})
    assert proj.meta["title"] == "Better Title"
    cal = calendar("demo", weeks=2)
    assert cal["settings"]["per_week"] == 2 and len(cal["weeks"]) == 2
    items = [it for w in cal["weeks"] for s in w["slots"] for it in s["items"]]
    assert items and items[0]["slug"] == proj.slug
    save_publish(proj, {"youtube_id": "abcdefghijk", "published_at": today})
    assert proj.meta["status"] == "published"
    assert channel_mod.Channel("demo").load_ideas()["ideas"][0]["status"] == "published"
    add_metrics(proj, {"views": 100, "ctr": 5.2})
    assert get_publish(proj)["metrics"][0]["day"] == 0


def test_retention_parse_variants(proj):
    from studio.retention import analyze, import_retention, parse
    tr = "Video konumu (%);Mutlak kitleyi elde tutma (%)\n" + "\n".join(f"{i};{100 - i * 0.6:.1f}".replace(".", ",") for i in range(101))
    d = parse(tr)
    assert d["unit"] == "percent" and d["points"][0]["ret"] == 100.0
    en = "Video position,Audience retention\n" + "\n".join(f"0:{i:02d},{1 - i / 100:.2f}" for i in range(0, 60))
    d2 = parse(en)
    assert d2["unit"] == "seconds" and d2["points"][-1]["ret"] == pytest.approx(41.0)
    # needs timing to map onto shots
    timing = [{"id": s["id"], "start": i * 2.0, "end": i * 2.0 + 2.0} for i, s in enumerate(proj.load_storyboard()["shots"])]
    proj.write_json(proj.timing_path("en"), timing)
    r = import_retention(proj, "en", tr)
    assert r["shots"][0]["id"] == "s001" and r["points"][-1]["t"] == pytest.approx(timing[-1]["end"])
    assert analyze(proj, "tr") is None


def test_signals_measure_bands():
    from studio.signals import measure

    def fake(path, params, key):
        if path == "search":
            return {"items": [{"id": {"videoId": f"v{i}"}} for i in range(10)]}
        if path == "videos":
            return {"items": [{"statistics": {"viewCount": str(v)}, "snippet": {"channelId": f"c{i % 2}", "publishedAt": "2026-06-01T00:00:00Z"}}
                              for i, v in enumerate([300_000] * 10)]}
        return {"items": [{"id": "c0", "statistics": {"subscriberCount": "5000"}}, {"id": "c1", "statistics": {"subscriberCount": "2000000"}}]}
    s = measure("bajau", "k", fake, today=date(2026, 9, 1))
    assert s["median_views"] == 300_000 and s["demand"] == 4
    assert s["recent_12m"] == 10 and s["big_channels"] == 5 and s["competition"] == 5
    assert s["outlier"] == 60.0 and s["gap"] == 5


def test_thumbnail_compose_text_fits():
    from studio.thumbnails import TH, TW, compose
    img = compose(Image.new("RGB", (1920, 1080), "#f0dfb8"), "Bigger spleens than any diver", "left",
                  highlight={"x": 900, "y": 500, "r": 100}, frame={"x": 900, "y": 500, "zoom": 2})
    assert img.size == (TW, TH)
    px = img.load()
    assert any(px[x, TH // 2] != (240, 223, 184) for x in range(0, TW // 2, 7))   # text drawn on the left half


def test_srt_from_timing(proj):
    from studio.render import write_srt
    shots = proj.load_storyboard()["shots"]
    proj.write_json(proj.timing_path("en"), [{"id": s["id"], "start": i * 1.5, "end": i * 1.5 + 1.5}
                                              for i, s in enumerate(shots)])
    srt = write_srt(proj, "en").read_text(encoding="utf-8")
    assert srt.startswith("1\n00:00:00,000 --> ") and "percent" in srt
    assert json.dumps(srt)  # plain text


def test_one_click_package(proj, monkeypatch):
    """Package prompt → Gemini (faked) → titles, thumbnail concepts, hooks applied → thumbnails painted (faked)."""
    import studio.llm as llm
    from studio.images import gemini_engine
    from studio.thumbnails import make_package
    reply = """```yaml
titles: ["Why the Bajau Have Bigger Spleens", "Built to Dive"]
thumbnails:
  - visual: {prompt: "close-up of a Bajau diver gliding over a reef"}
    text: {en: BIGGER SPLEENS, tr: DEV DALAK}
    text_pos: left
hooks:
  - {type: question, text: "How long can you hold your breath?"}
description: "Sea nomads and their spleens."
shorts_ideas:
  - {hook: "Hold your breath", shows: "a diver", loop: "back to the start"}
```"""
    asked = []
    monkeypatch.setattr(llm, "complete", lambda prompt, model, max_tokens=16000, provider="anthropic":
                        asked.append((model, provider)) or reply)
    painted = []

    def fake_generate(self, prompt, out, refs=None, aspect=None, size=None):
        painted.append(prompt)
        Image.new("RGB", (1920, 1080), "teal").save(out)

    monkeypatch.setattr(gemini_engine, "secret", lambda name: "k")
    monkeypatch.setattr(gemini_engine.GeminiEngine, "generate", fake_generate)
    cfg = config_mod.load_config("demo")
    cfg["planner"]["provider"] = "gemini"
    n = make_package(proj, cfg)
    assert n == {"titles": 2, "thumbnails": 1} and asked == [("gemini-3.8-flash", "gemini")]
    meta = proj.meta
    assert meta["publish"]["title_variants"][0] == "Why the Bajau Have Bigger Spleens"
    assert meta["publish"]["hook_options"][0]["type"] == "question" and meta["description"] == "Sea nomads and their spleens."
    assert len(painted) == 1 and "close-up of a Bajau diver" in painted[0] and "empty space on the left" in painted[0]
    for lg in ("en", "tr"):
        assert Image.open(proj.build / "thumbnails" / lg / "thumb1.png").size == (1280, 720)
