"""Thumbnail kinds (studio/thumbkit.py) and the channel-aware packaging prompt."""
import numpy as np
from PIL import Image, ImageDraw

from studio import thumbkit as tk
from studio import thumbnails as th
from tests.test_features import proj  # noqa: F401  (fixture)


def _picture(dark=False):
    img = Image.new("RGB", (1920, 1080), (40, 50, 60) if dark else (240, 232, 214))
    d = ImageDraw.Draw(img)
    d.ellipse([1100, 400, 1500, 900], outline=(20, 20, 20), width=4, fill=(120, 90, 60))
    return img


def test_theme_defaults_and_slip():
    paper = tk.theme_of({"thumbnails": {"paper": True, "accent": "#112233"}})
    assert paper["accent"] == "#112233" and paper["fonts"]["hand"] == "PermanentMarker-Regular.ttf"
    assert paper["slip"] is False                      # the page itself is the paper
    painting = tk.theme_of({})
    assert painting["slip"] is True and painting["stamp"] == "WRONG"


def test_bundled_fonts_load():
    for name in tk.DEFAULT_THEME["fonts"].values():
        assert (tk.FONTS / name).exists()
        f = tk.font(name, 40)
        assert f.getlength("WRONG") > 40


def test_every_kind_renders_on_paper_and_painting():
    for theme in (tk.theme_of({"thumbnails": {"paper": True, "ink_boost": 1}}), tk.theme_of({})):
        dark = not theme["paper"]
        for v, texts in (({"kind": "correction"}, {"myth": "8 glasses", "note": "half a sentence?"}),
                         ({"kind": "stamp", "pos": "top-right"}, {}),
                         ({"kind": "scene", "pos": "top"}, {"text": "not a raisin"})):
            out = tk.compose_kind(_picture(dark), v, texts, theme, "#b23a2e")
            assert out.size == (1920, 1080)
            a = np.asarray(out).astype(int)
            accent = np.array(tk.rgb(theme["accent"]))
            ink = np.array(tk.rgb(theme["ink"]))
            near = lambda c: (np.abs(a - c).sum(axis=2) < 90).sum()       # noqa: E731
            assert near(accent) > 2000 or near(ink) > 2000, (v, theme["paper"])
            assert np.abs(a[1000:, 1700:] - np.asarray(tk.prepare(_picture(dark), theme, (1920, 1080)))[1000:, 1700:]
                          ).max() < 40      # the bottom-right corner (duration badge) stays untouched


def test_long_scene_text_wraps_instead_of_shrinking():
    theme = tk.theme_of({"thumbnails": {"paper": True}})
    out = tk.scene(_picture(), "this is far too many words for one line", theme, "top")
    assert out.size == (1920, 1080)


def test_lint_rules():
    assert tk.lint({"kind": "correction"}, {"myth": "eight full glasses daily", "note": "a b c d"}) == [
        "inanış en fazla 3 kelime olmalı", "not en fazla 3 kelime olmalı"]
    assert any("claim" in w for w in tk.lint({"kind": "scene"}, {"text": "CONSUL AT 42"}))
    assert tk.lint({"kind": "scene", "claim": "c07"}, {"text": "CONSUL AT 42"}) == []
    assert tk.lint({"kind": "stamp", "pos": "bottom-right"}, {})


def test_direction_leaves_room_for_the_words():
    d = th._direction({"kind": "stamp", "pos": "top-left"}, {})
    assert "upper left" in d and "rubber stamp" in d
    d = th._direction({"kind": "scene"}, {"thumbnails": {"direction": "Ink drawing, one subject."}})
    assert d.startswith("Ink drawing, one subject.") and "top third" in d
    assert "space on the right side" in th._direction({"text_pos": "right"}, {})     # classic entries unchanged


def test_package_prompt_uses_the_channel(proj):  # noqa: F811
    d = proj.ch.data
    d["package"] = {"positioning": "A deadpan clerk files what everyone got wrong.",
                    "thumbnail_rules": ["Never show the clerk's face."]}
    d["thumbnails"] = {"stamp": "MYTH"}
    proj.ch.save(d)
    from studio.project import Project
    p = Project(proj.channel, proj.slug)
    prompt = th.build_package_prompt(p)
    assert "A deadpan clerk files what everyone got wrong." in prompt
    assert "Never show the clerk's face." in prompt
    assert '"MYTH"' in prompt and "kind: correction" in prompt
    assert "strength & conditioning" not in prompt          # no other channel's positioning leaks in


def test_preview_and_apply_package(proj):  # noqa: F811
    n = th.apply_package(proj, {"thumbnails": [
        {"kind": "correction", "visual": {"prompt": "eight glasses"}, "myth": {"en": "8 GLASSES"}, "claim": "c01"},
        {"kind": "stamp", "visual": {"prompt": "a bottle"}},
        {"kind": "scene", "visual": {"prompt": "a grape"}, "text": {"en": "NOT A RAISIN"}}]})
    assert n["thumbnails"] == 3 and proj.meta["thumbnails"][0]["kind"] == "correction"
    d = proj.build / "thumbnails" / "en"
    d.mkdir(parents=True)
    for i in (1, 2, 3):
        _picture().save(d / f"thumb{i}.png")
    out = th.preview(proj, "en")
    assert out.exists() and Image.open(out).size == (40 + 3 * 470, 980)


def test_render_thumbnails_end_to_end(proj, monkeypatch):  # noqa: F811
    import studio.images.gemini_engine as ge
    prompts = []

    class FakeEngine:
        style, characters, model = "Ink drawing on a ledger page.", {}, "fake"

        def __init__(self, cfg):
            pass

        def char_refs(self, chars):
            return []

        def generate(self, prompt, out, refs):
            prompts.append(prompt)
            _picture().save(out)

    monkeypatch.setattr(ge, "GeminiEngine", FakeEngine)
    d = proj.ch.data
    d["thumbnails"] = {"paper": True, "ink_boost": 1}
    d["series"]["limits"]["color"] = "#b23a2e"
    proj.ch.save(d)
    from studio.config import load_config
    from studio.project import Project
    p = Project(proj.channel, proj.slug)
    th.apply_package(p, {"thumbnails": [
        {"kind": "correction", "visual": {"prompt": "eight glasses"}, "myth": {"en": "8 GLASSES"},
         "note": {"en": "half a sentence?"}, "claim": "c01"},
        {"kind": "stamp", "visual": {"prompt": "a bottle"}, "pos": "top-right"},
        {"visual": {"prompt": "classic"}, "text": {"en": "OLD STYLE"}}]})
    p = Project(proj.channel, proj.slug)
    made = th.render_thumbnails(p, load_config(proj.channel), "en")
    assert [m.name for m in made] == ["thumb1.png", "thumb2.png", "thumb3.png"]
    assert Image.open(made[0]).size == (1920, 1080) and Image.open(made[2]).size == (1280, 720)
    assert "upper left" in prompts[0] and "rubber stamp" in prompts[1] and "big title" in prompts[2]
    assert (p.build / "thumbnails" / "en" / "preview.png").exists()
    th.render_thumbnails(p, load_config(proj.channel), "en")       # words only changed → no new pictures
    assert len(prompts) == 3
