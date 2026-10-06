"""Delivery tags ([curious] ...) for expressive voices: split, storyboard, units, ElevenLabs v3 request + timing."""
import base64
import subprocess

import numpy as np
import pytest

import studio.channel as channel_mod
import studio.config as config_mod
from studio.splitter import split_script, strip_tones
from studio.tts.elevenlabs_tts import tag_text
from studio.voice import build_units, with_question_tone


def test_strip_tones_offsets():
    clean, tags = strip_tones("It was cold. [whispers] And then   [pause] he ran.")
    assert clean == "It was cold. And then he ran."
    assert [(clean[o:o + 3], t) for o, t in tags] == [("And", "whispers"), ("he ", "pause")]
    assert strip_tones("[curious]") == ("", [(0, "curious")])
    assert strip_tones("No tags [1] here? [x2]")[0] == "No tags [1] here? [x2]"   # digits are not tags


def test_split_keeps_tone_on_beat_and_text_clean():
    shots = split_script("[curious] Why do humans throw so well, when chimps with far stronger arms cannot hit "
                         "anything at all? [excited] Because of the shoulder.\n\nPlain one.")
    assert all("[" not in s["text"] for s in shots)
    assert shots[0]["tone"] == ["curious"] and "tone" not in shots[1]
    assert shots[2] == {"para": 0, "sent": 1, "text": "Because of the shoulder.", "tone": ["excited"]}


def test_question_tone_and_units():
    shots = [{"id": "s001", "para": 0, "sent": 0, "text": "Why do we sweat"},
             {"id": "s002", "para": 0, "sent": 0, "text": "when dogs pant?"},
             {"id": "s003", "para": 0, "sent": 1, "text": "Heat.", "tone": ["excited"]},
             {"id": "s004", "para": 0, "sent": 2, "text": "Really?", "tone": ["whispers"]}]
    tagged = with_question_tone(shots, "curious")
    assert tagged[0]["tone"] == ["curious"] and "tone" not in shots[0]       # input untouched
    assert tagged[3]["tone"] == ["whispers"]                                  # own tag wins
    u = build_units(tagged, "paragraph")[0]
    assert u["text"] == "Why do we sweat when dogs pant? Heat. Really?"
    assert [(u["text"][p:p + 4], t) for p, t in u["cues"]] == [("Why ", "curious"), ("Heat", "excited"),
                                                               ("Real", "whispers")]
    assert with_question_tone(shots, "") is shots


def test_tag_text_roundtrip():
    text = "Why? Because."
    out, keep = tag_text(text, [[0, "curious"], [5, "excited"], [99, "pause"]])
    assert out == "[curious] Why? [excited] Because.[pause] "
    assert "".join(out[i] for i in keep) == text


@pytest.fixture()
def cfg(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CHANNELS", tmp_path / "channels")
    monkeypatch.setattr(channel_mod, "CHANNELS", tmp_path / "channels")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    from studio.channel import create_channel
    ch = create_channel("demo", "Demo", ["en"])
    d = ch.data
    d["overrides"] = {"tts": {"provider": "elevenlabs", "elevenlabs": {
        "voice_id": "v", "model": "eleven_v3", "settings": {"stability": 0.35, "style": 0.4}}}}
    ch.save(d)
    return config_mod.load_config("demo")


def test_elevenlabs_v3_sends_tags_and_maps_timing(cfg, monkeypatch):
    from studio.tts import elevenlabs_tts as el
    mp3 = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=d=0.3", "-f", "mp3", "pipe:1"],
                         capture_output=True, check=True).stdout
    seen = {}

    class R:
        status_code = 200

        def __init__(self, sent):
            self.sent = sent

        def json(self):
            return {"audio_base64": base64.b64encode(mp3).decode(),
                    "alignment": {"character_start_times_seconds": [i * 0.01 for i in range(len(self.sent))]}}

    def post(url, params, headers, json, timeout):
        seen.update(json)
        return R(json["text"])

    monkeypatch.setattr(el.requests, "post", post)
    tts = el.ElevenLabsTTS(cfg)
    assert tts.supports_tags and tts.settings["stability"] == 0.5          # v3 accepts 0 / 0.5 / 1 only
    sp = tts.synthesize("Why? Heat.", [[0, "curious"], [5, "excited"]])
    assert seen["text"] == "[curious] Why? [excited] Heat."
    assert len(sp.char_starts) == len("Why? Heat.")
    assert sp.char_starts[0] == pytest.approx(0.10) and sp.char_starts[5] == pytest.approx(0.25)
    assert isinstance(sp.samples, np.ndarray)


def test_resplit_follows_script_tags(cfg):
    from studio.project import create_project
    from studio.storyboard import build_storyboard
    p = create_project("demo", "Throw")
    p.script_path.write_text("[curious] Why can we throw?\n\nBecause of the shoulder.\n", encoding="utf-8")
    sb = build_storyboard(p, cfg)
    sb["shots"][0]["visual"] = {"bg": "savanna"}
    p.save_storyboard(sb)
    p.script_path.write_text("Why can we throw?\n\n[excited] Because of the shoulder.\n", encoding="utf-8")
    shots = build_storyboard(p, cfg)["shots"]
    assert shots[0]["visual"] == {"bg": "savanna"} and "tone" not in shots[0]   # visual kept, removed tag gone
    assert shots[1]["tone"] == ["excited"]
