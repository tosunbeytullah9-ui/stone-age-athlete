"""Motion scenes (Remotion): storyboard routing, per-language props, the channel look, the quality gate and the
render wiring. The real Node render runs only when Node.js and the packages are installed."""
import shutil

import pytest

import studio.channel as channel_mod
import studio.claims as claims_mod
import studio.config as config_mod


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
    create_channel("demo", "Demo", ["en", "tr"])
    p = create_project("demo", "Water")
    p.script_path.write_text("# Water\n\nCase file zero zero one. Subject: you.\n\nVerdict: wrong. Drink when thirsty.\n",
                             encoding="utf-8")
    build_storyboard(p, config_mod.load_config("demo"))
    return p


def test_engine_routing():
    from studio.images import engine_name
    from studio.remotion import comp_of, is_motion_shot
    assert engine_name({"visual": {"comp": "verdict"}}, {}) == "remotion"
    assert engine_name({"visual": {"prompt": "a desk"}}, {}) == "gemini"
    assert engine_name({"visual": {"bg": "plain_warm", "props": []}}, {}) == "svg"
    assert comp_of({"comp": "bars", "prompt": "x"}) is None                # a prompt makes it a painting
    assert is_motion_shot({"engine": "remotion", "visual": {"comp": "quote"}})


def test_props_per_language():
    from studio.remotion import scene_props
    v = {"comp": "case-file", "number": "001", "fields": [{"label": {"en": "SUBJECT", "tr": "KONU"}, "value": "you"}],
         "i18n": {"tr": {"fields": [{"value": "sen"}]}}}
    en, tr = scene_props(v, "en", "en"), scene_props(v, "tr", "en")
    assert "comp" not in en and "i18n" not in en
    assert en["fields"][0] == {"label": "SUBJECT", "value": "you"}
    assert tr["fields"][0] == {"label": "KONU", "value": "sen"}
    assert scene_props({"comp": "verdict", "word": {"en": "WRONG"}}, "tr", "en")["word"] == "WRONG"   # falls back


def test_validate():
    from studio.remotion import validate
    assert validate({"comp": "verdict"}) is None
    assert "bilinmeyen" in validate({"comp": "explosion"})
    assert "number" in validate({"comp": "case-file"})
    assert validate({"prompt": "a painting"}) is None


def test_theme_from_channel(proj):
    from studio.remotion import theme
    ch = channel_mod.Channel("demo")
    d = ch.data
    d["thumbnails"] = {"ink": "#111111", "accent": "#aa0000", "paper": True}
    d["remotion"] = {"wash": "#123456"}
    ch.save(d)
    th = theme(config_mod.load_config("demo"), copy_assets=False)
    assert th["name"] == "ledger" and th["ink"] == "#111111" and th["accent"] == "#aa0000"
    assert th["wash"] == "#123456" and th["paper"] is None
    d["remotion"] = {"theme": "museum"}
    d["thumbnails"] = {}
    ch.save(d)
    assert theme(config_mod.load_config("demo"), copy_assets=False)["name"] == "museum"


def test_gate_and_cost(proj):
    from studio.readiness import check
    sb = proj.load_storyboard()
    sb["shots"][0]["visual"] = {"comp": "case-file", "number": "001"}
    sb["shots"][-1]["visual"] = {"comp": "fireworks"}
    proj.save_storyboard(sb)
    r = {c["key"]: c for c in check(proj)["checks"]}
    assert not r["motion_scenes"]["ok"] and "fireworks" in r["motion_scenes"]["message"]
    assert "AI resmi: 0" in r["cost"]["message"] or "0 sahne" in r["cost"]["message"]


def test_scene_modes_hold_still():
    from studio.render import _scene_modes
    groups = [[{"id": "s001", "visual": {"comp": "verdict"}}], [{"id": "s002", "visual": {"prompt": "x"}}]]
    assert _scene_modes(groups) == ["none", "in"]


def test_sound_treats_charts_as_ink():
    from studio.sound.designer import plan
    groups = [[{"id": "s001", "text": "Thirty percent.", "para": 0, "visual": {"comp": "bars", "bars": []}}]]
    timing = [{"id": "s001", "start": 0.0, "end": 3.0}]
    out = plan(groups, timing, {"chart": "pen", "clerk_amb": "archive"})
    assert out["amb"][0]["id"] == "archive"
    assert any(e["why"] == "chart" for e in out["sfx"]) or not out["sfx"]


def test_render_uses_motion_clip(proj, monkeypatch):
    """render_video asks for one clip per motion scene (beats from the shot timing, the fade tail, the verdict
    stamp on the word "wrong") and cuts it in. The Remotion call is faked with a plain coloured clip."""
    import subprocess

    import studio.remotion as rm
    from studio.config import load_config
    sb = proj.load_storyboard()
    ids = [s["id"] for s in sb["shots"]]
    by_para: dict = {}
    for s in sb["shots"]:
        by_para.setdefault(s["para"], []).append(s)
    by_para[0][0]["visual"] = {"comp": "case-file", "number": "001", "fields": [{"label": "SUBJECT", "value": "you"}]}
    by_para[1][0]["visual"] = {"comp": "verdict", "word": "WRONG"}
    for para in by_para.values():
        for s in para[1:]:
            s["visual"] = {"same": True}
    proj.save_storyboard(sb)
    timing, t = [], 0.0
    for sid in ids:
        timing.append({"id": sid, "start": t, "end": t + 1.0})
        t += 1.0
    proj.write_json(proj.timing_path("en"), timing)
    proj.audio_dir("en").mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono", "-t", str(t),
                    str(proj.audio_dir("en") / "narration.wav")], check=True)
    seen = {}

    def fake(project, cfg, scenes, fps, size, crf, lang):
        seen["scenes"] = scenes
        out = {}
        for sc in scenes:
            path = project.build / f"{sc['head']['id']}_fake.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                            f"color=c=red:s={size[0]}x{size[1]}:r={fps}", "-frames:v", str(sc["frames"] + sc["tail"]),
                            "-pix_fmt", "yuv420p", str(path)], check=True)
            out[sc["head"]["id"]] = path
        return out

    monkeypatch.setattr(rm, "render_scene_clips", fake)
    cfg = load_config("demo")
    cfg["video"].update({"width": 320, "height": 180, "fps": 10})
    cfg["audio"].update({"design": False, "sfx": False})
    cfg.setdefault("channel", {})["outro"] = {"enabled": False}
    from studio.render import render_video
    out = render_video(proj, cfg, "en")
    assert out.exists()
    case, verdict = seen["scenes"]
    n0 = len(by_para[0])
    assert case["beats"] == [10 * i for i in range(n0)] and case["frames"] == 10 * n0 and case["tail"] == 12
    assert verdict["head"]["visual"]["comp"] == "verdict"
    assert 0 < verdict["extra"]["hit"] < 1.0                      # "Verdict: wrong." — on the word "wrong"


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js not installed")
def test_real_render(proj, tmp_path):
    """End to end through Node (skipped when Remotion's packages are not installed)."""
    import studio.remotion as rm
    if not rm.installed():
        pytest.skip("remotion/node_modules missing (python -m studio remotion-setup)")
    from studio.config import load_config
    cfg = load_config("demo")
    head = {"id": "s001", "visual": {"comp": "counter", "value": 42, "label": "test"}}
    clips = rm.render_scene_clips(proj, cfg, [{"head": head, "beats": [0], "frames": 20, "tail": 4}], 10,
                                  (320, 180), 23, "en")
    assert clips["s001"].exists() and clips["s001"].stat().st_size > 1000
