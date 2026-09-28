"""Paid planner: Anthropic Messages API, in batches of shots."""
from __future__ import annotations

from ..llm import complete
from . import apply_plan, build_prompt, parse_yaml_reply


def run(project, cfg, todo: list[dict]) -> None:
    model = cfg.get_path("planner.anthropic.model", "claude-sonnet-5")
    size = int(cfg.get_path("planner.anthropic.batch_size", 40))
    for i in range(0, len(todo), size):
        batch = todo[i:i + size]
        n = apply_plan(project, parse_yaml_reply(complete(build_prompt(project, only=batch), model)))
        print(f"  plan: {batch[0]['id']}–{batch[-1]['id']} → {n} shot planlandı")
