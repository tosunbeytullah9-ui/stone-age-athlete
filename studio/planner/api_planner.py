"""Automatic planner: Gemini or Anthropic, in batches of shots cut at paragraph boundaries."""
from __future__ import annotations

from ..llm import complete
from . import apply_plan, build_prompt, parse_yaml_reply


def _batches(todo: list[dict], size: int) -> list[list[dict]]:
    out, cur = [], []
    for s in todo:
        if len(cur) >= size and s.get("para") != cur[-1].get("para"):
            out.append(cur)
            cur = []
        cur.append(s)
    return out + ([cur] if cur else [])


def run(project, cfg, todo: list[dict], provider: str = "gemini") -> None:
    defaults = {"gemini": "gemini-3.8-flash", "anthropic": "claude-sonnet-5"}
    model = cfg.get_path(f"planner.{provider}.model", defaults[provider])
    size = int(cfg.get_path(f"planner.{provider}.batch_size", 60))
    for batch in _batches(todo, size):
        reply = complete(build_prompt(project, only=batch), model, provider=provider)
        plan = parse_yaml_reply(reply)
        ids = {s["id"] for s in batch}
        n = apply_plan(project, {k: v for k, v in plan.items() if k in ids})
        print(f"  plan: {batch[0]['id']}-{batch[-1]['id']}: {n}/{len(batch)} shot planlandı")
