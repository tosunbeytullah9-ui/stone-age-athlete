"""Word-level timing (studio/words.py) and code-drawn `mech` scenes (validation, word cues, numbers)."""
from studio import words
from studio.motion_rules import _mech_numbers
from studio.remotion import beat_timing, validate, word_cues

SHOTS = [{"id": "s1", "text": "The valve lifts. Then the valve hisses!"},
         {"id": "s2", "text": "Steam escapes through the valves."}]
TIMING = {"s1": {"start": 10.0, "end": 13.0}, "s2": {"start": 13.0, "end": 15.0}}


def test_cue_keys_and_offsets():
    v = {"items": [{"kind": "circle", "in": "@Valve#2+0.3", "keys": [{"at": "@pot - 0.2"}]}, {"kind": "text", "text": "@ not a cue"}]}
    assert words.cue_keys(v) == {"@valve#2", "@pot"}
    assert words.base_key("@spring*") == "@spring*"


def test_cue_table_counts_occurrences_across_shots():
    keys = {"@valve", "@valve#2", "@valve#3", "@steam", "@pot"}
    table, missing = words.cue_table(SHOTS, TIMING, 30, keys)
    assert table["@valve"] < table["@valve#2"] < table["@valve#3"]       # 'valves' counts as valve
    assert table["@steam"] == 90                                             # s2 starts 3 s after the scene
    assert missing == ["@pot"]


def test_stored_word_times_win():
    e = {"start": 0, "end": 3, "words": [["the", 0.0], ["valve", 2.5], ["lifts", 2.8], ["then", 2.9],
                                         ["the", 2.9], ["valve", 2.95], ["hisses", 2.99]]}
    assert words.shot_words(SHOTS[0], e)[1] == ("valve", 2.5)


def test_word_cues_for_a_scene():
    v = {"comp": "mech", "items": [{"kind": "gear", "spin": {"speed": 90, "from": "@hisses"}}]}
    cues = word_cues(SHOTS, TIMING, 30, v)
    assert 0 < cues["@hisses"] < 90
    assert word_cues(SHOTS, TIMING, 30, {"comp": "mech", "items": []}) is None
    bt = beat_timing(SHOTS, [0, 60], 30, 150)
    assert bt["s2"]["start"] == 2.0 and bt["s2"]["end"] == 5.0


def test_mech_validation():
    assert validate({"comp": "mech", "items": [{"kind": "gear"}, {"kind": "group", "items": [{"kind": "text", "text": "hi"}]}]}) is None
    assert "bilinmeyen" in validate({"comp": "mech", "items": [{"kind": "spaceship"}]})
    assert "def" in validate({"comp": "mech", "items": [{"kind": "use", "def": "nope"}]})
    assert "items" in validate({"comp": "mech"})


def test_mech_numbers_skip_examples():
    v = {"items": [{"kind": "text", "text": "1925 · feed wheel"}, {"kind": "text", "text": "×6", "example": True},
                   {"kind": "group", "items": [{"kind": "label", "text": "0.20 – 0.35 mm"}]},
                   {"kind": "gear", "r": 80}]}
    assert _mech_numbers(v) == {1925.0, 0.2, 0.35}


def test_split_refreshes_chapters(tmp_path, monkeypatch):
    import studio.channel as channel_mod
    import studio.config as config_mod
    monkeypatch.setattr(config_mod, "CHANNELS", tmp_path)
    monkeypatch.setattr(channel_mod, "CHANNELS", tmp_path)
    from studio.channel import create_channel
    from studio.project import create_project
    from studio.storyboard import build_storyboard
    ch = create_channel("demo", "Demo", ["en"])
    p = create_project(ch.id, "Chapters")
    p.script_path.write_text("# t\n<!-- chapter: One -->\nFirst paragraph is here.\n\nA new paragraph.\n\n"
                             "<!-- chapter: Two -->\nThird paragraph is here.\n", encoding="utf-8")
    m = p.meta
    m["chapters"] = {0: "One", 1: "Two"}
    p.save_meta(m)
    build_storyboard(p, config_mod.load_config(ch.id))
    assert p.meta["chapters"] == {0: "One", 2: "Two"}
