"""Paid planner: Anthropic Messages API, in batches of shots."""
from __future__ import annotations

import requests

from ..config import secret
from . import apply_plan, build_prompt, parse_yaml_reply

API = "https://api.anthropic.com/v1/messages"


def run(project, cfg, todo: list[dict]) -> None:
    key = secret("ANTHROPIC_API_KEY")
    model = cfg.get_path("planner.anthropic.model", "claude-sonnet-5")
    size = int(cfg.get_path("planner.anthropic.batch_size", 40))
    for i in range(0, len(todo), size):
        batch = todo[i:i + size]
        prompt = build_prompt(project, only=batch)
        r = requests.post(API, timeout=300, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model, "max_tokens": 16000, "messages": [{"role": "user", "content": prompt}]})
        if r.status_code != 200:
            raise SystemExit(f"Anthropic API hatası {r.status_code}: {r.text[:300]}")
        text = "".join(b.get("text", "") for b in r.json().get("content", []))
        n = apply_plan(project, parse_yaml_reply(text))
        print(f"  plan: {batch[0]['id']}–{batch[-1]['id']} → {n} shot planlandı")
