"""Factory-level tests: channels, projects, idea bank, quality gate, panel API. No network, no models."""
import pytest

import studio.channel as channel_mod
import studio.config as config_mod


@pytest.fixture()
def tmp_channels(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CHANNELS", tmp_path)
    monkeypatch.setattr(channel_mod, "CHANNELS", tmp_path)
    return tmp_path


def test_channel_project_and_readiness(tmp_channels):
    from studio.channel import create_channel, list_channels
    from studio.project import Project, create_project
    from studio.readiness import check
    from studio.storyboard import build_storyboard

    ch = create_channel("history-of-medicine", "History of Medicine", ["en", "tr"])
    assert [c.id for c in list_channels()] == ["history-of-medicine"]
    p = create_project(ch.id, "The First Surgeons")
    assert p.slug.startswith("001-") and p.exists()
    r = check(p)
    assert not r["ready"]  # template script, no sources, no storyboard

    p.script_path.write_text("# t\n\n" + " ".join(["Surgeons in ancient Egypt set broken bones."] * 30), encoding="utf-8")
    p.sources_path.write_text("- a https://a.org\n- b https://b.org\n- c https://c.org\n", encoding="utf-8")
    cfg = config_mod.load_config(ch.id)
    sb = build_storyboard(p, cfg)
    for s in sb["shots"]:
        s["visual"] = {"prompt": f"scene {s['id']}"} if int(s["id"][1:]) % 3 == 1 else {"same": True}
    p.save_storyboard(sb)
    r = check(Project(ch.id, p.slug))
    assert r["ready"], [c for c in r["checks"] if not c["ok"]]


def test_channel_overrides_merge(tmp_channels):
    from studio.channel import Channel, create_channel
    ch = create_channel("c1", "C1", ["en"])
    d = ch.data
    d["overrides"] = {"tts": {"kokoro": {"voice": "bm_george"}}, "images": {"default_engine": "gemini"}}
    Channel("c1").save(d)
    cfg = config_mod.load_config("c1")
    assert cfg.get_path("tts.kokoro.voice") == "bm_george"
    assert cfg.get_path("tts.kokoro.speed") == 1.0          # untouched global value survives
    assert cfg.get_path("images.default_engine") == "gemini"
    assert cfg.get_path("channel.name") == "C1"


def test_translation_units_use_i18n(tmp_channels):
    from studio.voice import build_units
    shots = [{"id": "s001", "para": 0, "sent": 0, "text": "Right now,", "i18n": {"tr": "Şu anda,"}},
             {"id": "s002", "para": 0, "sent": 0, "text": "somewhere.", "i18n": {"tr": "bir yerlerde."}}]
    u = build_units(shots, "sentence", "tr", "en")[0]
    assert u["text"] == "Şu anda, bir yerlerde." and u["spans"][1]["start"] == len("Şu anda, ")


def test_panel_api(tmp_channels):
    from fastapi.testclient import TestClient

    from studio.web.app import app
    c = TestClient(app)
    assert c.post("/api/channels", json={"id": "demo", "name": "Demo", "languages": ["en"]}).status_code == 200
    ov = c.get("/api/overview").json()
    assert ov["channels"][0]["id"] == "demo"
    idea = c.post("/api/channels/demo/ideas", json={"title": "Why do we sweat?", "pillar": "P5", "priority": "A"}).json()
    slug = c.post(f"/api/channels/demo/ideas/{idea['id']}/project").json()["slug"]
    proj = c.get(f"/api/projects/demo/{slug}").json()
    assert proj["meta"]["title"] == "Why do we sweat?" and proj["readiness"]["ready"] is False
    svg = c.post("/api/preview-svg", json={"visual": "bg: plain_warm\nprops: [{type: pie, value: 0.3}]"}).text
    assert svg.startswith("<svg")
    assert c.get("/files/../config.yaml").status_code == 404
    assert c.post(f"/api/projects/demo/{slug}/run", json={"step": "rm -rf"}).status_code == 400
