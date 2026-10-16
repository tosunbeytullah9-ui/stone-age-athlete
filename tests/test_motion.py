"""Living pictures: the stillmotion engine and its use in render."""
import json
import subprocess

import numpy as np
import pytest
from PIL import Image


def _picture(path, w=320, h=180):
    rng = np.random.default_rng(0)
    arr = (rng.uniform(0, 255, (h, w, 3))).astype(np.uint8)
    arr[h // 2:, :, 1] = 160                                    # a "grass" band
    Image.fromarray(arr).save(path)
    return path


def test_spec_parse_and_errors():
    from studio.stillmotion import parse
    s = parse({"camera": "left", "fx": [{"type": "sway", "box": [0, .5, 1, 1]}]})
    assert s.camera.move == "left" and s.fx[0]["type"] == "sway"
    with pytest.raises(ValueError):
        parse({"fx": [{"type": "lasers"}]})
    with pytest.raises(ValueError):
        parse({"camera": {"move": "spin"}})


def test_envelope_open_ended_and_ramps():
    from studio.stillmotion.spec import envelope
    assert envelope({}, 50.0, 7.0) == 1.0                         # keeps going past the clip (cross-fade tail)
    assert envelope({"from": 2, "to": 4, "ramp": 0.5}, 1.0, 7.0) == 0.0
    assert 0 < envelope({"from": 2, "ramp": 0.5}, 2.2, 7.0) < 1


def test_clip_is_deterministic_and_moves(tmp_path):
    from studio.stillmotion import Clip
    img = _picture(tmp_path / "p.png")
    spec = {"camera": {"move": "in", "amount": 0.1}, "fx": [{"type": "sway", "box": [0, .5, 1, 1], "amount": 4}]}
    a, b = Clip(img, spec, 1, 10, depth="off"), Clip(img, spec, 1, 10, depth="off")
    f0, f9 = a.frame(0), a.frame(9)
    assert f0.shape == (180, 320, 3)
    assert np.array_equal(f9, b.frame(9))                         # same input → same frames
    assert np.abs(f0.astype(int) - f9.astype(int)).mean() > 1     # the camera moved


def test_local_effects_stay_in_their_box(tmp_path):
    from studio.stillmotion import Clip
    img = _picture(tmp_path / "p.png")
    spec = {"camera": "none", "fx": [{"type": "flicker", "box": [0.6, 0.6, 0.9, 0.9], "amount": 0.5},
                                     {"type": "embers", "box": [0.6, 0.6, 0.9, 0.9], "count": 20}]}
    c = Clip(img, spec, 2, 10, depth="off")
    diff = np.abs(c.frame(3).astype(int) - c.frame(12).astype(int)).sum(2)
    assert diff[:90, :150].max() == 0                             # top-left quarter untouched
    assert diff[108:162, 192:288].max() > 0                       # inside the box something moved


def test_every_effect_runs(tmp_path):
    from studio.stillmotion import Clip
    from studio.stillmotion.effects import REGISTRY
    img = _picture(tmp_path / "p.png")
    fx = [{"type": name, "box": [0.1, 0.1, 0.9, 0.9]} for name in REGISTRY]
    c = Clip(img, {"camera": {"move": "drift"}, "fx": fx}, 1, 10, depth="heuristic")
    for i in (0, 5, 14):                                          # 14: past the end (tail frames)
        assert c.frame(i).shape == (180, 320, 3)


def test_scene_spec_merges_preset_plan_and_scene_camera():
    from studio.config import Config
    from studio.motion import scene_spec
    cfg = Config({"video": {"zoom": 0.08, "motion_preset": "ledger"}})
    head = {"id": "s004"}
    plain = scene_spec(head, 3, "right", cfg, {})
    assert plain["camera"]["move"] == "right" and plain["camera"]["amount"] == 0.08
    assert [e["type"] for e in plain["fx"]] == ["boil"]
    planned = scene_spec(head, 3, "right", cfg, {"s004": {"camera": {"move": "in"}, "fx": [{"type": "rain"}]}})
    assert planned["camera"]["move"] == "in" and [e["type"] for e in planned["fx"]] == ["boil", "rain"]
    alone = scene_spec(head, 3, "right", cfg, {"s004": {"inherit_fx": False, "fx": [{"type": "snow"}]}})
    assert [e["type"] for e in alone["fx"]] == ["snow"]


def test_motion_clip_with_overlay_and_crossfade(tmp_path):
    from studio.fx import overlay_layer
    from studio.render import _clip
    from studio.stillmotion import render
    img = _picture(tmp_path / "p.png")
    scene = render(img, tmp_path / "scene.mp4", 1.0, {"camera": "in"}, fps=10, depth="off")
    ov = overlay_layer({"kind": "stat", "text": "92%"}, "en", "en", tmp_path / "ov.png", (320, 180))
    out = tmp_path / "shot.mp4"
    _clip(out, 6, 10, 320, 180, 23, ("motion", scene, 2), prev=("motion", scene, 0), xfade=2, overlay=ov)
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries",
                        "stream=nb_read_frames,width,height", "-of", "json", str(out)], capture_output=True, text=True)
    st = json.loads(r.stdout)["streams"][0]
    assert (int(st["nb_read_frames"]), st["width"], st["height"]) == (6, 320, 180)
