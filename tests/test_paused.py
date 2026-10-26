"""A paused channel spends nothing: paid CLI steps stop unless --force (studio/__main__.py)."""
import pytest

from studio import __main__ as cli


class _Ch:
    def __init__(self, data):
        self.data = data


def test_paid_steps_stop_on_a_paused_channel(monkeypatch):
    import studio.channel as chmod
    monkeypatch.setattr(chmod, "Channel", lambda cid: _Ch({"name": "X", "status": "paused", "paused_note": "until Jan"}))
    with pytest.raises(SystemExit) as e:
        cli.stop_if_paused("x")
    assert "donduruldu" in str(e.value) and "--force" in str(e.value)
    monkeypatch.setattr(chmod, "Channel", lambda cid: _Ch({"name": "X"}))
    cli.stop_if_paused("x")                     # an active channel passes
    assert {"images", "thumbnails", "package", "render"} <= cli.PAID_STEPS


def test_homo_athleticus_is_paused_and_myths_moved():
    from studio.channel import Channel
    ha, yw = Channel("homo-athleticus"), Channel("youre-wrong")
    assert ha.data.get("status") == "paused" and ha.data["schedule"]["per_week"] == 1
    moved = {i["id"]: i["moved_to"] for i in ha.load_ideas()["ideas"] if i.get("moved_to")}
    assert {"i010", "i025", "i078", "i081", "i110", "i120", "i132"} <= set(moved)
    yw_ids = {i["id"] for i in yw.load_ideas()["ideas"]}
    assert all(dst.split("/")[1] in yw_ids for dst in moved.values())
