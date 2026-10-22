"""Every channel's ideas.yaml parses into whole titles. An unquoted title with ", " inside a flow mapping
(`{title: A Siphon, Not a Push}`) is silently split into a short title and a stray key `Not a Push: null`."""
import yaml

from studio.config import CHANNELS


def test_no_title_split_by_a_comma():
    bad = []
    for p in sorted(CHANNELS.glob("*/ideas.yaml")):
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for idea in data.get("ideas") or []:
            stray = [k for k, v in idea.items() if v is None and " " in str(k)]
            if stray:
                bad.append(f"{p.parent.name}/{idea.get('id')}: {stray}")
    assert not bad, "quote these titles in ideas.yaml: " + "; ".join(bad)
