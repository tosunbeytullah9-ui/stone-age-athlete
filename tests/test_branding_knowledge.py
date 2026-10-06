"""Channel artwork (profile, banner, watermark) and the channel bible for chatbots."""
import pytest
from PIL import Image

import studio.channel as channel_mod
import studio.claims as claims_mod
import studio.config as config_mod


@pytest.fixture()
def ch(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CHANNELS", tmp_path / "channels")
    monkeypatch.setattr(channel_mod, "CHANNELS", tmp_path / "channels")
    monkeypatch.setattr(claims_mod, "LIBRARY", tmp_path / "library" / "sources.yaml")
    from studio.channel import create_channel
    from studio.project import create_project
    c = create_channel("demo", "Demo Channel", ["en", "tr"])
    d = c.data
    d.update({"tagline": "Your body has a long training log.", "mascot": {"pose": "point", "wear": ["headband"]},
              "series": {"limits": {"name": "Human Limits", "pillars": ["P3"], "promise": "Extreme bodies"}}})
    c.save(d)
    c.save_ideas({"pillars": {"P3": {"name": "Extreme", "promise": "p"}},
                  "ideas": [{"id": "i001", "title": "Bajau | divers", "pillar": "P3", "priority": "A",
                             "status": "idea", "signals": {"demand": 4, "competition": 2, "gap": 5}},
                            {"id": "i002", "title": "Dropped one", "pillar": "P3", "status": "dropped"}]})
    claims_mod.save_library({"sources": [{"id": "ilardo2018", "title": "Diving adaptations", "year": 2018,
                                          "type": "primary", "population": "59 Bajau adults"}]})
    p = create_project("demo", "Bajau")
    p.script_path.write_text("# Bajau\n<!-- note -->\n\n" + "They dive all day. " * 80, encoding="utf-8")
    meta = p.meta
    meta["status"] = "published"
    meta["publish"] = {"series": "limits", "hook_type": "question", "youtube_id": "abc",
                       "metrics": [{"date": "2026-10-01", "day": 7, "views": 1200, "ctr": 5.1}]}
    p.save_meta(meta)
    return c


def test_knowledge_bible(ch):
    from studio.knowledge import build_knowledge, write_knowledge
    cfg = config_mod.load_config("demo")
    md = build_knowledge("demo", cfg)
    for part in ("# Demo Channel: channel bible", "Human Limits", "[curious]", "| i001 | Bajau / divers | A | idea | 4/2/5",
                 "`ilardo2018` (primary)", "59 Bajau adults", "abc", "views 1200", "## 10. Reference script",
                 "They dive all day."):
        assert part in md, part
    assert "Dropped one" not in md and "<!-- note -->" not in md
    assert write_knowledge("demo", cfg).read_text(encoding="utf-8") == md


def test_banner_safe_area_is_centred():
    from studio.branding import BANNER, SAFE, safe_box
    x0, y0, x1, y1 = safe_box()
    assert (x1 - x0, y1 - y0) == SAFE and abs(x0 + x1 - BANNER[0]) <= 1 and abs(y0 + y1 - BANNER[1]) <= 1


def test_branding_renders(ch):
    pw = pytest.importorskip("playwright.sync_api")
    try:
        with pw.sync_playwright() as p:
            p.chromium.launch().close()
    except Exception:
        pytest.skip("no Chromium for Playwright")
    from studio.branding import render_branding
    made = {p.name: p for p in render_branding("demo", config_mod.load_config("demo"))}
    assert Image.open(made["profile.png"]).size == (800, 800)
    assert Image.open(made["banner.png"]).size == (2560, 1440)
    wm = Image.open(made["watermark.png"])
    assert wm.size == (150, 150) and wm.mode == "RGBA" and wm.getpixel((0, 0))[3] == 0
