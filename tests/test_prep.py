"""Preparation packages (studio/prep.py) and the YouTube-policy guard (studio/policy.py)."""
import pytest
import yaml

import studio.channel as channel_mod
import studio.claims as claims_mod
import studio.config as config_mod


@pytest.fixture()
def demo(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CHANNELS", tmp_path / "channels")
    monkeypatch.setattr(channel_mod, "CHANNELS", tmp_path / "channels")
    monkeypatch.setattr(claims_mod, "LIBRARY", tmp_path / "library" / "sources.yaml")
    from studio.channel import create_channel
    create_channel("demo", "Demo", ["en"])
    path = tmp_path / "channels" / "demo" / "channel.yaml"
    ch = yaml.safe_load(path.read_text(encoding="utf-8"))
    ch["youtube"] = {"made_for_kids": False, "synthetic_media": False}
    path.write_text(yaml.safe_dump(ch, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _set_policy(path, **pol):
    ch = yaml.safe_load(path.read_text(encoding="utf-8"))
    ch["policy"] = pol
    path.write_text(yaml.safe_dump(ch, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _cfg():
    return config_mod.load_config("demo")


def _example(**over):
    """The panel's format example plus two test-only sources (the gate wants three different sources)."""
    from studio.prep import example
    d = example()
    d["sources"] += [{"id": "testa2020", "title": "Test source A", "url": "https://example.org/a", "type": "review"},
                     {"id": "testb2021", "title": "Test source B", "url": "https://example.org/b", "type": "primary"}]
    d["claims"] += [{"id": "c04", "text": "Chimpanzees are far stronger than humans", "source": "testa2020",
                     "says": "Chimpanzees are far stronger than we are"},
                    {"id": "c05", "text": "Muscles alone could not move the arm that fast", "source": "testb2021",
                     "says": "Muscles alone could never move the arm that fast"}]
    d.update(over)
    return d


def test_locate_and_chapters():
    from studio.prep import chapters_from_script, locate
    shots = [{"text": "In two thousand thirteen, a team at Harvard"}, {"text": "filmed twenty baseball players"},
             {"text": "with motion capture."}]
    assert locate(shots, "filmed twenty baseball players with motion capture") == (1, 2)
    assert locate(shots, "Harvard filmed") == (0, 1)
    assert locate(shots, "nothing like this") is None
    script = "# T\n<!-- chapter: One -->\nFirst para.\n\nSecond para.\n\n<!-- chapter: Two -->\nThird para.\n"
    assert chapters_from_script(script) == {0: "One", 2: "Two"}


def test_example_passes(demo):
    from studio.prep import check
    rep = check("demo", _example(), _cfg())
    assert rep["importable"], rep["errors"]
    assert rep["ok"], [c["message"] for c in rep["checks"] if c["level"] == "block" and not c["ok"]]
    s = rep["summary"]
    assert s["claims"] == 5 and s["shorts"] == 1 and s["chapters"] == 3


def test_errors_stop_the_import(demo):
    from studio.prep import check, import_bundle
    bad = _example(claims=[{"id": "c01", "text": "x", "source": "nobody2020", "says": "a twelve-year-old"}])
    rep = check("demo", bad, _cfg())
    assert not rep["importable"] and "nobody2020" in rep["errors"][0]
    with pytest.raises(ValueError):
        import_bundle("demo", bad, _cfg())


def test_import_links_everything(demo):
    from studio.claims import load_claims
    from studio.channel import Channel
    from studio.prep import import_bundle
    from studio.publish import get_publish
    data = _example(new_idea={"title": "Your Shoulder Is a Catapult", "pillar": "P1", "angle": "elastic energy"})
    p = import_bundle("demo", data, _cfg())
    claims = load_claims(p)["claims"]
    assert all(c.get("shots") for c in claims)                       # `says` found in the shots
    meta = p.meta
    assert meta["chapters"][0] == "The throw" and len(meta["chapters"]) == 3
    assert meta["shorts"][0]["from"].startswith("s") and meta["shorts"][0]["to"] >= meta["shorts"][0]["from"]
    assert len(meta["thumbnails"]) == 3 and meta["description"]
    pub = get_publish(p)
    assert pub["title_used"] == "Your Shoulder Is a Catapult" and pub["title_variants"][0] == pub["title_used"]
    idea = next(i for i in Channel("demo").load_ideas()["ideas"] if i.get("project") == p.slug)
    assert idea["status"] == "scripting" and idea["title"] == "Your Shoulder Is a Catapult"
    assert (p.dir / "storyboard.yaml").exists()
    assert "roach2013" in {s["id"] for s in claims_mod.load_library()["sources"]}


def test_repeat_is_blocked(demo):
    from studio.prep import check, import_bundle
    import_bundle("demo", _example(), _cfg())
    rep = check("demo", _example(), _cfg())                          # the same script again
    orig = next(c for c in rep["checks"] if c["key"] == "policy_original")
    assert not orig["ok"] and orig["level"] == "block" and not rep["ok"]


def test_ai_persona_on_health(demo):
    from studio.prep import check, import_bundle
    _set_policy(demo, sensitive=["health"], narrator="fictional",
                transparency="The narrator is a fictional character with a synthetic voice.")
    rep = check("demo", _example(), _cfg())
    assert rep["ok"], [c["message"] for c in rep["checks"] if c["level"] == "block" and not c["ok"]]
    d = _example()
    d["script"] = d["script"].replace("So the next time you throw", "As a doctor, I recommend this. So the next time you throw")
    rep = check("demo", d, _cfg())
    per = next(c for c in rep["checks"] if c["key"] == "policy_persona")
    assert not per["ok"] and per["level"] == "block"
    with pytest.raises(ValueError):
        import_bundle("demo", d, _cfg())
    assert import_bundle("demo", d, _cfg(), force=True)              # the owner can decide knowingly


def test_transparency_required_on_sensitive_channels(demo):
    from studio.prep import check
    _set_policy(demo, sensitive=["health"])
    rep = check("demo", _example(), _cfg())
    tr = next(c for c in rep["checks"] if c["key"] == "policy_transparency")
    assert not tr["ok"] and tr["level"] == "block"


def test_metadata_rules():
    from studio.policy import metadata_checks
    out = {c["key"]: c for c in metadata_checks(["This Is Shit"], ["GORE"], "nothing")}
    assert not out["policy_meta_language"]["ok"] and out["policy_meta_language"]["level"] == "warn"
    assert not out["policy_meta_shock"]["ok"]
    out = {c["key"]: c for c in metadata_checks(["Why 7,000 Greeks Stayed"], ["7.000 MEN"], "about 7000 Greeks")}
    assert out["policy_meta_claims"]["ok"]
    out = {c["key"]: c for c in metadata_checks(["Why 9,000 Greeks Stayed"], [], "about seven thousand Greeks")}
    assert not out["policy_meta_claims"]["ok"]


def test_ai_label(demo):
    from studio.policy import ai_label
    assert ai_label(_cfg())[0] is False
    _set_policy(demo, realistic_visuals=True)
    assert ai_label(_cfg())[0] is True


def test_upload_needs_the_owner_review(demo):
    from studio.policy import REVIEW_STEPS, save_review, upload_blocks
    from studio.prep import import_bundle
    p = import_bundle("demo", _example(), _cfg())
    assert any("Sahip onayı" in b for b in upload_blocks(p, _cfg()))
    save_review(p, {k: True for k in REVIEW_STEPS})
    assert not any("Sahip onayı" in b for b in upload_blocks(p, _cfg()))


def test_prompt_carries_the_rules(demo):
    from studio.prep import build_prompt
    _set_policy(demo, sensitive=["health"], transparency="Fictional narrator.")
    t = build_prompt("demo", topic="Why kids out-throw chimps", cfg=_cfg())
    assert "AI personas on sensitive topics" in t and "Fictional narrator." in t
    assert "new_idea:" in t and "says:" in t and "shorts:" in t


def test_inbox_roundtrip(demo):
    from studio.prep import dump, list_inbox, read_inbox, save_inbox
    name = save_inbox("demo", dump(_example()))
    assert list_inbox("demo")[0]["name"] == name
    assert "Catapult" in read_inbox("demo", name)
