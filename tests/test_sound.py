"""Sound design: synthesis, catalog, automatic plan, stems."""
import numpy as np


def test_every_builtin_sound_renders():
    from studio.sound import synth
    for name in ("archive", "rain", "street_old", "lab"):
        x = synth.generate(name)
        assert x.ndim == 2 and x.shape[1] == 2 and len(x) > synth.SR * 10 and np.isfinite(x).all()
    for name in synth.EFFECTS:
        x = synth.generate(name)
        assert x.shape[1] == 2 and 0.01 < np.abs(x).max() <= 1.0, name


def test_catalog_falls_back_without_files():
    from studio.sound import catalog
    cat = catalog.load_catalog()
    assert cat["vinyl_hiss"]["license"] == "CC0"
    assert catalog.kind("vinyl_hiss", cat) == "amb" and catalog.kind("gulp", cat) == "sfx"
    x = catalog.get("door", cat=cat)                      # file missing in tests → synthesized fallback (knock)
    assert x.shape[1] == 2
    assert not catalog.license_ok({"license": "CC-BY-NC"}) and catalog.license_ok({"license": "CC0"})


def test_plan_picks_beds_and_effects():
    from studio.sound.designer import plan, summary
    shots = [
        {"id": "s001", "para": 0, "text": "Case file zero zero one.",
         "visual": {"prompt": "the clerk's hands opening a folder", "characters": ["clerk"]}},
        {"id": "s002", "para": 1, "text": "He drinks it all.", "visual": {"prompt": "a man drinking a glass of water"}},
        {"id": "s003", "para": 1, "text": "In the market,", "visual": {"prompt": "a crowded Roman market square"}},
        {"id": "s004", "para": 1, "text": "people paid in coins.", "visual": {"same": True}},
        {"id": "s005", "para": 2, "text": "Verdict: wrong.", "visual": {"prompt": "stamp", "characters": ["clerk"]},
         "sound": {"amb": "none"}},
    ]
    groups = [[shots[0]], [shots[1]], [shots[2], shots[3]], [shots[4]]]
    timing = [{"id": s["id"], "start": 25.0 * i, "end": 25.0 * i + 24} for i, s in enumerate(shots)]
    p = plan(groups, timing)
    assert [a["id"] for a in p["amb"]] == ["archive", "room", "street_old", "none"]
    ids = [e["id"] for e in p["sfx"]]
    assert "paper" in ids and "gulp" in ids and "coins" in ids and ids[-1] == "stamp"
    s = summary(p, len(groups))
    assert 0.6 < s["amb_coverage"] < 1 and s["sfx_count"] == len(p["sfx"])


def test_storyboard_overrides_win():
    from studio.sound.designer import plan
    shot = {"id": "s001", "para": 0, "text": "He drinks slowly.", "visual": {"prompt": "a man drinking water"},
            "sound": {"amb": "rain", "sfx": [{"id": "bell", "at": "slowly"}]}}
    p = plan([[shot]], [{"id": "s001", "start": 0.0, "end": 4.0}])
    assert p["amb"][0]["id"] == "rain" and [e["id"] for e in p["sfx"]] == ["bell"]
    assert 2.0 < p["sfx"][0]["t"] < 3.5                    # lands on the word "slowly"


def test_stems_are_levelled_against_the_voice(tmp_path):
    from studio.sound import catalog
    from studio.sound.mixdown import _rms, render_ambience, render_effects
    sr = catalog.SR
    t = np.arange(sr * 6) / sr
    voice = (0.3 * np.sin(2 * np.pi * 180 * t) * (t % 2 < 1.4)).astype("float32")
    amb = render_ambience([{"t0": 0, "t1": 6, "id": "room"}], 6.0, voice, -26, 6)
    fx = render_effects([{"t": 1.0, "id": "stamp", "db": 0, "variant": 0}], 6.0, voice, -12)
    ratio_db = 20 * np.log10(_rms(amb) / _rms(voice))
    assert -36 < ratio_db < -24
    assert np.abs(fx).max() > 0 and np.abs(fx[: sr // 2]).max() == 0
    catalog.write_wav(tmp_path / "a.wav", amb)
    assert (tmp_path / "a.wav").stat().st_size > 10000
