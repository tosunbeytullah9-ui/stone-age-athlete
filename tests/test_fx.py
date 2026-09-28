"""Finishing layer: overlays, chart animation, sound effects, camera runs, vertical crop."""
from PIL import Image


def test_overlay_text_and_draw():
    from studio.fx import draw_overlay, overlay_text, short_cite
    ov = {"kind": "stat", "text": "+11–16%", "i18n": {"tr": "%11–16"}}
    assert overlay_text(ov, "tr", "en") == "%11–16" and overlay_text(ov, "de", "en") == "+11–16%"
    base = Image.new("RGB", (1920, 1080), "#f0dfb8")
    for kind in ("stat", "label", "cite"):
        img = draw_overlay(base, {"kind": kind}, "Macintosh et al. · 2017")
        assert img.size == base.size and img.tobytes() != base.tobytes()
    assert short_cite({"authors": "Ilardo MA et al.", "year": 2018, "venue": "Cell"}) == "Ilardo et al. · 2018 · Cell"


def test_animated_visuals_grow():
    from studio.fx import ANIM_FRAMES, animated_visuals
    v = {"bg": "classroom", "props": [{"type": "bar_chart", "values": [1.0, 0.5]}, {"type": "gauge", "value": 0.8}]}
    frames = animated_visuals(v)
    assert len(frames) == ANIM_FRAMES
    assert frames[0]["props"][0]["values"][0] < frames[-1]["props"][0]["values"][0] < 1.0
    assert v["props"][0]["values"] == [1.0, 0.5]                     # original untouched
    assert animated_visuals({"bg": "gym"}) == [] and animated_visuals({**v, "animate": False}) == []


def test_sfx_events_and_track(tmp_path):
    from studio.fx import build_sfx_track, sfx_events
    shots = [{"visual": {"bg": "gym", "props": []}}, {"visual": {"bg": "gym", "props": [{"type": "clock"}]}},
             {"visual": {"bg": "savanna"}}]
    timing = [{"start": 0, "end": 2}, {"start": 2, "end": 4}, {"start": 4, "end": 6}]
    ev = sfx_events(shots, timing)
    assert [n for _, n in ev] == ["pop", "whoosh"]
    out = build_sfx_track(ev, 6.0, tmp_path, tmp_path / "fx.wav")
    assert out.exists() and out.stat().st_size > 1000


def test_camera_runs_and_vertical_crop():
    from studio.config import load_global
    from studio.render import _camera_modes
    from studio.svgkit import crop_vertical, render_svg
    shots = [{"visual": {"bg": "gym"}}, {"visual": {"bg": "gym"}}, {"visual": {"bg": "sea"}},
             {"visual": {"bg": "sea"}, "camera": "none"}, {"visual": {"bg": "classroom", "props": [{"type": "pie", "value": 0.4}]}}]
    assert _camera_modes(shots, load_global()) == ["in", "in", "out", "none", "none"]
    svg = crop_vertical(render_svg({"bg": "gym", "figures": [{"pose": "run", "x": 1800}]}), 1800)
    assert 'width="1080" height="1920"' in svg and 'viewBox="1312.5 0 607.5 1080.0"' in svg
