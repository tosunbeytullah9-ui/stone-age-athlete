"""Fast checks that need no network, no models and no browser: python -m pytest -q"""
from studio.align import _proportional
from studio.planner import parse_yaml_reply
from studio.splitter import split_script
from studio.svgkit import catalog, render_svg
from studio.voice import build_units


def test_split_limits_and_order():
    text = ("Right now, somewhere, an elite athlete is finishing a two-hour training session. "
            "They lifted, they sprinted, they pushed to the edge.\n\nNow rewind 7,000 years. "
            "Her bones were 11.5% stronger than Dr. Smith expected.")
    shots = split_script(text, 20, 65)
    assert " ".join(s["text"] for s in shots).replace("  ", " ") == " ".join(text.split())
    assert all(len(s["text"]) <= 65 for s in shots)
    assert any("11.5%" in s["text"] and "Dr. Smith" in s["text"] for s in shots)
    assert shots[-1]["para"] == 1


def test_units_and_proportional_timing():
    shots = [{"id": "s001", "para": 0, "sent": 0, "text": "Right now, somewhere,"},
             {"id": "s002", "para": 0, "sent": 0, "text": "an elite athlete is finishing a session."},
             {"id": "s003", "para": 0, "sent": 1, "text": "In an hour, they'll be sitting."}]
    units = build_units(shots, "sentence")
    assert len(units) == 2 and units[0]["text"].startswith("Right now") and len(units[0]["spans"]) == 2
    u = dict(units[0], offset=1.0, duration=4.0)
    starts = _proportional(u)
    assert starts[0] == 1.0 and 1.0 < starts[1] < 5.0


def test_every_chart_and_background_renders():
    cat = catalog()
    for bg in cat["backgrounds"]:
        assert "<svg" in render_svg({"bg": bg})
    for p in cat["charts"]:
        extra = {"to": (100, 100)} if p == "arrow" else {}
        assert "<svg" in render_svg({"bg": "plain_cool", "props": [{"type": p, "x": 900, "y": 500, **extra}]})


def test_scenes_group_shots_that_share_a_picture():
    from studio.images import drop_orphans, engine_name, scene_map, scenes
    shots = [{"id": "s001", "visual": {"prompt": "a"}}, {"id": "s002", "visual": {"same": True}},
             {"id": "s003", "visual": {"bg": "plain_warm", "props": [{"type": "pie"}]}},
             {"id": "s004", "visual": None}, {"id": "s005", "visual": {"same": True}}]
    assert scene_map(shots) == {"s001": "s001", "s002": "s001", "s003": "s003", "s004": "s004", "s005": "s005"}
    assert [[s["id"] for s in g] for g in scenes(shots)] == [["s001", "s002"], ["s003"], ["s004"], ["s005"]]
    assert engine_name(shots[0], {}) == "gemini" and engine_name(shots[2], {}) == "svg"
    assert drop_orphans(shots) == 1 and shots[4]["visual"] is None


def test_planner_reply_parsing():
    reply = "Here you go:\n```yaml\ns001:\n  visual: {bg: gym}\ns002:\n  camera: out\n  visual: {bg: savanna}\n```"
    plan = parse_yaml_reply(reply)
    assert plan["s002"]["camera"] == "out" and plan["s001"]["visual"]["bg"] == "gym"


def test_gemini_engine_with_fake_api(tmp_path, monkeypatch):
    """The paid engine's request/response handling, without calling Google."""
    import base64
    import io

    from PIL import Image

    from studio.config import Config
    from studio.images import gemini_engine

    buf = io.BytesIO()
    Image.new("RGB", (1344, 768), "orange").save(buf, "PNG")
    payload = {"candidates": [{"content": {"parts": [{"inlineData": {"data": base64.b64encode(buf.getvalue()).decode()}}]}}]}

    class Resp:
        status_code = 200
        text = ""

        def json(self):
            return payload

    sent = {}

    def fake_post(url, json, timeout, headers):
        sent.update(url=url, body=json, headers=headers)
        return Resp()

    monkeypatch.setattr(gemini_engine, "secret", lambda name: "test-key")
    monkeypatch.setattr(gemini_engine.requests, "post", fake_post)
    monkeypatch.setattr(gemini_engine, "CHANNELS", tmp_path)
    (tmp_path / "ch" / "refs").mkdir(parents=True)
    Image.new("RGB", (64, 64), "red").save(tmp_path / "ch" / "refs" / "coach.png")
    eng = gemini_engine.GeminiEngine(Config({
        "images": {"gemini": {"model": "gemini-3.1-flash-image"}},
        "channel": {"id": "ch", "visual_style": "Gouache museum mural.",
                    "characters": {"coach": {"description": "The Coach: a woman.", "ref": "refs/coach.png"}}}}))
    out = tmp_path / "s001.png"
    eng.render({"id": "s001", "visual": {"prompt": "a mammoth herd", "characters": ["coach"]}}, out)
    assert Image.open(out).size == (1920, 1080)
    assert "gemini-3.1-flash-image:generateContent" in sent["url"]
    assert sent["headers"]["x-goog-api-key"] == "test-key"
    parts = sent["body"]["contents"][0]["parts"]
    assert parts[0]["text"].startswith("Gouache museum mural.") and "The Coach: a woman." in parts[0]["text"]
    assert "a mammoth herd" in parts[0]["text"] and "No text" in parts[0]["text"]
    assert len(parts) == 2 and parts[1]["inline_data"]["mime_type"] == "image/png"   # character sheet attached
