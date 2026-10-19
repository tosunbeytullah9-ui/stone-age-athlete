"""Channel motion rules (studio/motion_rules.py): the signature beats come from the script's fixed structure, data
scenes are only accepted when their numbers and quotes come from the claims linked to their shots."""
import pytest
import yaml

import studio.channel as channel_mod
import studio.claims as claims_mod
import studio.config as config_mod

SCRIPT = """# Water

You think you need eight glasses of water a day.
Everyone says so.

Case file zero zero seven.
Subject: you.
Belief: you need eight glasses of water a day, or you dry out.

A 2016 study measured 5604 people in 26 countries.
Most of them drank far less.

Verdict: wrong. Drink when you are thirsty.
"""


@pytest.fixture()
def proj(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CHANNELS", tmp_path / "channels")
    monkeypatch.setattr(channel_mod, "CHANNELS", tmp_path / "channels")
    monkeypatch.setattr(claims_mod, "LIBRARY", tmp_path / "library" / "sources.yaml")
    import studio.remotion as rm
    monkeypatch.setattr(rm, "CHANNELS", tmp_path / "channels")
    from studio.channel import create_channel
    from studio.project import create_project
    from studio.storyboard import build_storyboard
    create_channel("demo", "Demo", ["en"])
    path = tmp_path / "channels" / "demo" / "channel.yaml"
    ch = yaml.safe_load(path.read_text(encoding="utf-8"))
    ch["remotion"] = {"theme": "ledger", "scenes": {"cold_open": True, "case_file": {"org": "BUREAU"},
                                                    "verdict": {"note": True}, "data": {"min": 1, "max": 3}}}
    path.write_text(yaml.safe_dump(ch, allow_unicode=True, sort_keys=False), encoding="utf-8")
    p = create_project("demo", "Water")
    p.script_path.write_text(SCRIPT, encoding="utf-8")
    build_storyboard(p, config_mod.load_config("demo"))
    return p


def _cfg():
    return config_mod.load_config("demo")


def _ids(p, pattern):
    import re
    return [s["id"] for s in p.load_storyboard()["shots"] if re.search(pattern, s["text"], re.I)]


def _claims(p, claims):
    (p.dir / "claims.yaml").write_text(yaml.safe_dump({"claims": claims}, sort_keys=False), encoding="utf-8")


def test_rules_off_without_channel_setting(proj):
    from studio.motion_rules import rules_for, signature_plan
    cfg = _cfg()
    cfg["channel"]["remotion"].pop("scenes")
    assert rules_for(cfg, proj) is None
    shots, report = signature_plan(proj, cfg)
    assert report == [] and shots == proj.load_storyboard()["shots"]


def test_theme_ignores_motion_rules(proj):
    """The paper's ruled lines (`theme.rules`) must never be overwritten by the channel's motion rules."""
    from studio.remotion import theme
    th = theme(_cfg(), copy_assets=False)
    assert "rules" not in th or "step" in th["rules"]


def test_signature_beats(proj):
    from studio.motion_rules import signature_plan
    from studio.remotion import comp_of
    shots, report = signature_plan(proj, _cfg())
    by = {s["id"]: s for s in shots}
    first = shots[0]
    assert first["visual"]["comp"] == "verdict" and first["visual"]["label"] == "BELIEF"
    assert "eight glasses" in first["visual"]["belief"].lower()
    assert first["visual"]["hit_beat"] >= 1
    case = by[_ids(proj, r"^case file")[0]]
    assert case["visual"]["comp"] == "case-file" and case["visual"]["number"] == "007"
    assert case["visual"]["org"] == "BUREAU" and case["visual"]["fields"][0]["label"] == "SUBJECT"
    subj = by[_ids(proj, r"^subject")[0]]
    assert subj["visual"] == {"same": True}                     # "Subject: you." is typed onto the card
    verdict = by[_ids(proj, r"^verdict")[0]]
    assert comp_of(verdict["visual"]) == "verdict" and verdict["visual"]["word"] == "WRONG"
    assert any(r.startswith("açılış") for r in report) and any(r.startswith("hüküm") for r in report)
    # idempotent: planning twice gives the same storyboard
    again, _ = signature_plan(proj, _cfg(), shots)
    assert again == shots


def test_project_switches(proj):
    from studio.motion_rules import signature_plan
    proj.save_meta({**proj.meta, "motion": {"cold_open": False, "case_file": False}})
    shots, report = signature_plan(proj, _cfg())
    assert "comp" not in (shots[0].get("visual") or {})
    assert not any(r.startswith("dosya") for r in report)
    assert any(r.startswith("hüküm") for r in report)


def test_cold_open_needs_the_belief(proj):
    """An opening that does not restate the belief keeps its picture."""
    from studio.motion_rules import signature_plan
    from studio.storyboard import build_storyboard
    proj.script_path.write_text(SCRIPT.replace("You think you need eight glasses of water a day.",
                                               "In 1945 a committee wrote one sentence."), encoding="utf-8")
    build_storyboard(proj, _cfg())
    shots, report = signature_plan(proj, _cfg())
    assert "comp" not in (shots[0].get("visual") or {})
    assert any("resim kalıyor" in r for r in report)


def test_validate_data(proj):
    from studio.motion_rules import validate_data
    sid = _ids(proj, r"5604")[0]
    other = _ids(proj, r"^verdict")[0]
    _claims(proj, [{"id": "c1", "text": "A 2016 study measured 5604 people in 26 countries.", "shots": [sid],
                    "quote": "most of this quantity is contained in prepared foods"}])
    ok = {sid: {"visual": {"comp": "counter", "value": 5604, "label": "people in 26 countries"}}}
    assert validate_data(proj, ok) == {}
    bad_number = {sid: {"visual": {"comp": "counter", "value": 5600}}}           # rounded: rejected
    assert "5600" in validate_data(proj, bad_number)[sid]
    unlinked = {other: {"visual": {"comp": "counter", "value": 5604}}}           # claim is on another shot
    assert "iddia" in validate_data(proj, unlinked)[other]
    quote_ok = {sid: {"visual": {"comp": "quote", "text": "Most of this quantity is contained in prepared foods."}}}
    assert validate_data(proj, quote_ok) == {}
    quote_bad = {sid: {"visual": {"comp": "quote", "text": "Water is mostly in food, says the board."}}}
    assert "alıntı" in validate_data(proj, quote_bad)[sid]
    unknown = {sid: {"visual": {"comp": "fireworks"}}}
    assert validate_data(proj, unknown)[sid]


def test_apply_plan_skips_invalid_data_scenes(proj):
    from studio.planner import apply_plan
    sid = _ids(proj, r"5604")[0]
    nxt = _ids(proj, r"drank far less")[0]
    _claims(proj, [{"id": "c1", "text": "A 2016 study measured 5604 people in 26 countries.", "shots": [sid]}])
    before = {s["id"]: s.get("visual") for s in proj.load_storyboard()["shots"]}
    apply_plan(proj, {sid: {"visual": {"comp": "counter", "value": 9999}}, nxt: {"visual": {"same": True}}})
    after = {s["id"]: s.get("visual") for s in proj.load_storyboard()["shots"]}
    assert after[sid] == before[sid] and after[nxt] == before[nxt]               # nothing invented reaches the video
    apply_plan(proj, {sid: {"visual": {"comp": "counter", "value": 5604}}, nxt: {"visual": {"same": True}}})
    after = {s["id"]: s.get("visual") for s in proj.load_storyboard()["shots"]}
    assert after[sid]["comp"] == "counter" and after[nxt] == {"same": True}


def test_data_prompt_lists_claims_and_shots(proj):
    from studio.motion_rules import build_data_prompt
    sid = _ids(proj, r"5604")[0]
    _claims(proj, [{"id": "c1", "text": "5604 people in 26 countries.", "shots": [sid]}])
    txt = build_data_prompt(proj, _cfg())
    assert "c1 shots " + sid in txt and f"[{sid}]" in txt and "1–3 scenes" in txt
