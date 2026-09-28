"""The code-drawn kit: every background, pose, prop, wear and hold item renders (no browser needed)."""
import re

import pytest

from studio.svgkit import backgrounds, catalog, render_svg
from studio.svgkit.figure import HOLDS, POSES, WEAR, draw_figure
from studio.svgkit.props import FLOATING, PROPS

DIGITS_IN_TEXT = re.compile(r"<text\b")


def _ok(svg: str):
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert "nan" not in svg.lower()
    assert not DIGITS_IN_TEXT.search(svg), "drawings must not contain text"


@pytest.mark.parametrize("name", sorted(backgrounds.BACKGROUNDS))
def test_background(name):
    fill, body, ground = backgrounds.get(name)
    assert 500 < ground < 1080
    _ok(render_svg({"bg": name}))


@pytest.mark.parametrize("opts", [
    ("sea", {"boat": True, "stilts": True, "island": True, "sun": "high"}),
    ("mountain", {"flag": True, "camp": True, "snow": False}),
    ("arctic", {"igloo": True, "sun": False}), ("desert", {"pyramids": True, "sun": None}),
    ("shore", {"reeds": False, "boat": True}), ("steppe", {"yurt": True}), ("village", {"stilts": True}),
    ("dojo", {"ring": True}), ("underwater", {"surface": False, "rays": False, "plants": False}),
])
def test_background_options(opts):
    name, o = opts
    _ok(render_svg({"bg": name, "bg_opts": o}))


@pytest.mark.parametrize("pose", sorted(POSES))
@pytest.mark.parametrize("flip", [False, True])
def test_pose(pose, flip):
    for scale in (1.0, 0.6):
        svg = draw_figure({"pose": pose, "flip": flip, "scale": scale, "x": 900}, 850)
        assert "polyline" in svg and "nan" not in svg


def test_pose_limb_lengths_are_consistent():
    """New poses keep the shared limb lengths (upper arm 85, forearm 80, thigh 95, shin 92) within 15%.
    (The original hand-made poses predate the builder and are left as they were.)"""
    import math
    new = ["swim", "dive", "float", "tread", "jump", "leap", "push_up", "plank", "lunge", "sprint_start", "stretch",
           "crawl", "push", "pull", "hang", "ride", "row", "wrestle", "march", "shiko", "club_swing", "guard"]
    for name in new:
        p = POSES[name]
        for a, b, L in (("sh", "le", 85), ("le", "lh", 80), ("sh", "re", 85), ("re", "rh", 80),
                        (None, "lk", 95), ("lk", "lf", 92), (None, "rk", 95), ("rk", "rf", 92)):
            d = math.dist(p[a] if a else (0, 0), p[b])
            assert abs(d - L) < 0.15 * L, (name, a, b, d)


@pytest.mark.parametrize("name", sorted(PROPS))
def test_prop(name):
    extra = {"to": (100, 100)} if name == "arrow" else {}
    _ok(render_svg({"bg": "plain_cool", "props": [{"type": name, "x": 900, "y": 500, **extra}]}))
    assert isinstance(PROPS[name](900, 500, 0.5, **extra), str)


def test_value_props_accept_extremes():
    for name in ("pie", "gauge", "meter", "battery", "stopwatch", "thermometer", "pedometer"):
        for v in (0, 0.5, 1):
            _ok(render_svg({"bg": "plain_cool", "props": [{"type": name, "x": 900, "y": 500, "value": v}]}))
    for name, key in (("lungs", "fill"), ("muscle_fiber", "fast"), ("eye", "pupil"), ("foot_arch", "arch"),
                      ("knee_joint", "cartilage"), ("balance", "tilt")):
        for v in (0, 1):
            _ok(render_svg({"bg": "plain_cool", "props": [{"type": name, "x": 900, "y": 700, key: v}]}))


@pytest.mark.parametrize("item", WEAR)
def test_wear(item):
    for pose in ("stand", "swim", "ride"):
        _ok(render_svg({"bg": "plain_warm", "figures": [{"pose": pose, "wear": [item]}]}))


@pytest.mark.parametrize("item", HOLDS)
def test_hold(item):
    for pose in ("stand", "carry_head", "draw_bow", "club_swing", "row"):
        _ok(render_svg({"bg": "plain_warm", "figures": [{"pose": pose, "hold": item, "flip": True}]}))


def test_floating_set_is_known():
    assert FLOATING <= set(PROPS)
    assert {"fish", "heart_organ", "bubbles", "pie"} <= FLOATING
    assert "horse" not in FLOATING


def test_lift_and_rotate_move_the_figure():
    base = draw_figure({"pose": "swim", "x": 900}, 900)
    lifted = draw_figure({"pose": "swim", "x": 900, "lift": 300}, 900)
    rotated = draw_figure({"pose": "stand", "x": 900, "rotate": 30}, 900)
    assert base != lifted and "polyline" in rotated


def test_mixed_recipe():
    visual = {
        "bg": "sea", "bg_opts": {"boat": True}, "order": "figures_first",
        "figures": [
            {"pose": "row", "x": 960, "ground": 735, "hold": "paddle", "wear": ["headscarf"]},
            {"pose": "tread", "x": 500, "ground": 880, "wear": ["goggles"], "face": "smile"},
            {"pose": "guard", "x": 1400, "hold": ["sword", "shield"], "wear": ["roman_helmet", "armor", "sandals"],
             "flip": True, "scale": 0.6},
        ],
        "props": [{"type": "water_surface", "x": 500, "y": 760, "w": 400},
                  {"type": "fish", "x": 300, "y": 950, "flip": True},
                  {"type": "pie", "x": 1600, "y": 250, "value": 0.3},
                  {"type": "line_chart", "x": 300, "y": 400, "values": [0.1, 0.5, 0.9], "scale": 0.5}],
    }
    _ok(render_svg(visual))
    cat = catalog()
    assert {"underwater", "sea", "mountain", "arena", "track", "lab"} <= set(cat["backgrounds"])
    assert {"swim", "ride", "wrestle", "draw_bow"} <= set(cat["poses"])


def test_catalog_sheets_build_without_browser():
    from studio.catalog import poses_pages, props_pages
    pages = props_pages()
    assert len(pages) >= 3 and all(p.startswith("<svg") for p in pages)
    assert len(poses_pages()) >= 3
