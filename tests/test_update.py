"""Updater + three-way merge: local edits survive an update, renamed channel folders are followed."""
import subprocess
from pathlib import Path

import yaml

from studio.merge3 import merge_value, merge_yaml_text


def test_merge_value_rules():
    base = {"a": 1, "b": 1, "c": {"x": 1}, "ideas": [{"title": "T1"}, {"title": "T2"}]}
    ours = {"a": 2, "b": 1, "c": {"x": 1, "y": 5},
            "ideas": [{"id": "i001", "title": "T1", "status": "scripting"}, {"id": "i002", "title": "T2"},
                      {"id": "i003", "title": "Mine"}]}
    theirs = {"a": 1, "b": 3, "c": {"x": 2}, "d": 4,
              "ideas": [{"id": "i001", "title": "T1", "signals": {"v": 9}}, {"id": "i002", "title": "T2 new"}]}
    m = merge_value(base, ours, theirs)
    assert m["a"] == 2 and m["b"] == 3 and m["c"] == {"x": 2, "y": 5} and m["d"] == 4
    i1, i2, i3 = m["ideas"]
    assert i1["status"] == "scripting" and i1["signals"] == {"v": 9}
    assert i2["title"] == "T2 new" and i3["title"] == "Mine"


def test_merge_yaml_keeps_comments():
    base = "a: 1  # one\nb: 2\n"
    ours = "a: 5\nb: 2\n"
    theirs = "a: 1  # one\nb: 2  # two\nc: 3\n"
    out = merge_yaml_text(base, ours, theirs)
    assert yaml.safe_load(out) == {"a": 5, "b": 2, "c": 3}
    assert "# two" in out


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout


def test_restore_stash_follows_renamed_channel(tmp_path, monkeypatch):
    import studio.channel as channel_mod
    import studio.config as config_mod
    import studio.migrate as migrate_mod
    import studio.updater as up

    repo = tmp_path / "r"
    (repo / "channels/old/projects").mkdir(parents=True)
    (repo / "channels/old/channel.yaml").write_text("name: Old\nlanguages: [en]\n")
    (repo / "channels/old/ideas.yaml").write_text("pillars: {}\nideas:\n- {title: A}\n- {title: B}\n")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v1")
    # owner edits: idea status + a new project (untracked)
    (repo / "channels/old/ideas.yaml").write_text(
        "pillars: {}\nideas:\n- {id: i001, title: A, status: scripting, project: 001-a}\n- {id: i002, title: B}\n")
    (repo / "channels/old/projects/001-a").mkdir()
    (repo / "channels/old/projects/001-a/script.md").write_text("# A\n\nmy words\n")
    _git(repo, "stash", "push", "-u", "-q")
    # new version: channel renamed, ideas get ids + a new field
    _git(repo, "mv", "channels/old", "channels/new")
    (repo / "channels/new/channel.yaml").write_text("name: New\naliases: [old]\nlanguages: [en]\n")
    (repo / "channels/new/ideas.yaml").write_text(
        "pillars: {}\nideas:\n- {id: i001, title: A, signals: {v: 1}}\n- {id: i002, title: B}\n")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "v2")

    for mod in (config_mod, channel_mod, migrate_mod, up):
        if hasattr(mod, "ROOT"):
            monkeypatch.setattr(mod, "ROOT", repo)
    monkeypatch.setattr(config_mod, "CHANNELS", repo / "channels")
    monkeypatch.setattr(channel_mod, "CHANNELS", repo / "channels")
    monkeypatch.setattr(migrate_mod, "CHANNELS", repo / "channels")
    monkeypatch.setattr(up, "STATE", repo / ".fabrika/state.json")

    assert up.restore() == 0
    ideas = yaml.safe_load((repo / "channels/new/ideas.yaml").read_text())["ideas"]
    assert ideas[0]["status"] == "scripting" and ideas[0]["signals"] == {"v": 1}
    assert (repo / "channels/new/projects/001-a/script.md").read_text() == "# A\n\nmy words\n"
    assert not (repo / "channels/old").exists()
    assert _git(repo, "stash", "list") == ""
    assert Path(repo / "backups").exists()
