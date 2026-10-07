"""YouTube publishing: video id parsing, release time, description template, the upload flow against a fake API."""
from datetime import datetime

import pytest

import studio.config as config_mod
from tests.test_features import proj  # noqa: F401  (fixture)

VID = "dQw4w9WgXcQ"


def test_parse_video_id():
    from studio.youtube import YouTubeError, parse_video_id
    for text in (VID, f"https://youtu.be/{VID}", f"https://www.youtube.com/watch?v={VID}&t=3",
                 f"https://studio.youtube.com/video/{VID}/edit", f"youtube.com/shorts/{VID}"):
        assert parse_video_id(text) == VID, text
    assert parse_video_id("") is None
    with pytest.raises(YouTubeError):
        parse_video_id("https://example.com/nothing")


def test_release_time():
    from studio.youtube import YouTubeError, release
    now = datetime(2026, 10, 7, 12, 0).astimezone()
    yt = {"publish_time": "22:00", "privacy": "private"}
    assert release(yt, {}, "now", now) == ("public", None)
    assert release(yt, {}, None, now) == ("private", None)
    priv, at = release(yt, {"planned_date": "2026-10-09"}, None, now)
    assert priv == "private" and at.endswith("Z")
    assert datetime.fromisoformat(at.replace("Z", "+00:00")) == datetime(2026, 10, 9, 22, 0).astimezone()
    assert release(yt, {"planned_date": "2026-10-01"}, None, now) == ("private", None)   # past plan is ignored
    with pytest.raises(YouTubeError):
        release(yt, {}, "2026-10-01 10:00", now)


def _ready(proj, credit=True):
    from studio.claims import apply_reply
    from studio.channel import Channel
    ch = Channel("demo")
    d = ch.data
    d["languages"] = ["en"]
    if credit:
        d["youtube"] = {"credit": "Made by an expert coach.", "footer": "Not medical advice. <b>"}
    ch.save(d)
    apply_reply(proj, {"sources": [{"id": "ilardo2018", "title": "Adaptations <x>", "year": 2018, "type": "primary",
                                    "url": "https://x.org"}],
                       "claims": [{"text": "Spleens 50% larger", "source": "ilardo2018", "shots": ["s001"]}]})
    proj.write_json(proj.timing_path("en"), [{"id": s["id"], "start": i * 2.0, "end": i * 2.0 + 2.0}
                                             for i, s in enumerate(proj.load_storyboard()["shots"])])
    meta = proj.meta
    meta["description"] = "Why Bajau divers stay down so long."
    proj.save_meta(meta)


def test_description_template(proj):
    from studio.render import describe
    _ready(proj)
    text = describe(proj, config_mod.load_config("demo"), "en").read_text(encoding="utf-8")
    assert text.startswith("Why Bajau divers stay down so long.\n\nMade by an expert coach.\n")
    assert "Sources:" in text and "Adaptations x" in text and "https://x.org" in text
    assert text.rstrip().endswith("Not medical advice. b") and "<" not in text and ">" not in text


class FakeYT:
    def __init__(self, privacy="private"):
        self.calls, self.privacy = [], privacy

    def my_channel(self):
        return {"id": "UC1", "snippet": {"title": "Demo"}}

    def get(self, path, **params):
        self.calls.append(("GET", path, params))
        if path == "videos":
            return {"items": [{"id": VID, "status": {"privacyStatus": self.privacy}}]}
        return {"items": []}

    def call(self, method, url, ok=None, **kw):
        self.calls.append((method, url.rsplit("/", 1)[-1], kw.get("json"), kw.get("params")))

        class R:
            def json(self):
                return {"id": "PL1"}
        return R()


def test_publish_existing_draft(proj):
    from studio.publish import get_publish, save_publish
    from studio.youtube import load_state, publish_video
    _ready(proj)
    save_publish(proj, {"series": "limits", "title_used": "Why Bajau Divers Stay Down So Long"})
    proj.lang_dir("en")
    yt = FakeYT()
    vid = publish_video(proj, config_mod.load_config("demo"), "en", video=f"https://youtu.be/{VID}",
                        at="2099-01-01 10:00", force=True, client=yt)
    assert vid == VID
    put = next(c for c in yt.calls if c[0] == "PUT")
    body = put[2]
    assert body["id"] == VID and body["snippet"]["title"] == "Why Bajau Divers Stay Down So Long"
    assert body["snippet"]["categoryId"] == "27" and body["status"]["selfDeclaredMadeForKids"] is False
    assert body["status"]["privacyStatus"] == "private" and body["status"]["publishAt"].startswith("2099-01-01")
    assert "Made by an expert coach." in body["snippet"]["description"]
    names = [c[1] for c in yt.calls if c[0] == "POST"]
    assert names == ["captions", "playlists", "playlistItems"]            # no thumbnail rendered in this test
    pub = get_publish(proj)
    assert pub["youtube_id"] == VID and pub["planned_date"] == "2099-01-01"
    assert load_state("demo")["playlists"] == {"limits": "PL1"}


def test_live_video_is_never_pulled_back(proj):
    from studio.youtube import publish_video
    _ready(proj)
    yt = FakeYT(privacy="public")
    publish_video(proj, config_mod.load_config("demo"), "en", video=VID, force=True, client=yt)
    status = next(c for c in yt.calls if c[0] == "PUT")[2]["status"]
    assert status["privacyStatus"] == "public" and "publishAt" not in status


def test_upload_needs_audit_or_draft(proj):
    from studio.youtube import YouTubeError, publish_video
    _ready(proj)
    (proj.lang_dir("en") / "video.mp4").write_bytes(b"0")
    with pytest.raises(YouTubeError, match="özel"):
        publish_video(proj, config_mod.load_config("demo"), "en", force=True, client=FakeYT())
