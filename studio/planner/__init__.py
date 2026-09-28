"""Fills storyboard `visual` fields.

manual     (free)  writes build/planner_prompt.md — paste it into Claude (claude.ai), save the YAML answer
                   as a file, then run: python -m studio apply-plan <slug> <file>
anthropic  (paid)  calls the Anthropic API in batches and writes the visuals directly
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..config import ROOT, Config
from ..project import Project
from ..storyboard import unplanned

SPEC = ROOT / "docs" / "STORYBOARD.md"

INSTRUCTIONS = """You are the visual planner for a YouTube explainer channel ("{channel}": {tagline}) that tells
stories with simple stick-figure drawings. The channel mascot is: {mascot}.
Plan ONE visual per shot, following the spec below exactly. Reply with ONLY a YAML mapping from shot id to
its visual (and optional engine/camera), like:

s001:
  visual: {bg: gym, bg_opts: {clock: "7:00"}, figures: [{pose: overhead_lift, x: 960, hold: barbell, face: strain, sweat: true}]}
s002:
  camera: out
  visual: {...}

Keep continuity between consecutive shots. Do not include any text or numbers inside images.
"""


def _context(shots: list[dict], todo: list[dict], title: str) -> str:
    lines = [f"# Video: {title}", "", "## Full narration (for context; shot ids in brackets)"]
    for s in shots:
        lines.append(f"[{s['id']}] {s['text']}")
    lines += ["", "## Plan these shots", ", ".join(s["id"] for s in todo)]
    return "\n".join(lines)


def build_prompt(project: Project, only: list[dict] | None = None) -> str:
    sb = project.load_storyboard()
    shots = sb["shots"]
    todo = only if only is not None else unplanned(shots)
    ch = project.ch.data if project.ch.exists() else {}
    head = (INSTRUCTIONS.replace("{channel}", str(ch.get("name", project.channel)))
            .replace("{tagline}", str(ch.get("tagline", ""))).replace("{mascot}", str(ch.get("mascot", {}))))
    return f"{head}\n\n{SPEC.read_text(encoding='utf-8')}\n\n{_context(shots, todo, sb.get('title', project.slug))}"


def apply_plan(project: Project, plan: dict) -> int:
    sb = project.load_storyboard()
    n = 0
    for s in sb["shots"]:
        entry = plan.get(s["id"])
        if not entry:
            continue
        if isinstance(entry, dict) and "visual" in entry:
            s["visual"] = entry["visual"]
            for k in ("engine", "camera"):
                if k in entry:
                    s[k] = entry[k]
        else:
            s["visual"] = entry
        n += 1
    project.save_storyboard(sb)
    return n


def parse_yaml_reply(text: str) -> dict:
    if "```" in text:
        parts = text.split("```")
        text = max(parts[1::2], key=len)
        if text.lstrip().startswith(("yaml", "yml")):
            text = text.split("\n", 1)[1]
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("planner reply is not a YAML mapping")
    return data


def plan(project: Project, cfg: Config) -> None:
    provider = cfg.get_path("planner.provider", "manual")
    todo = unplanned(project.load_storyboard()["shots"])
    if not todo:
        print("  tüm shot'ların görsel planı zaten var.")
        return
    if provider == "manual":
        out = project.build / "planner_prompt.md"
        out.write_text(build_prompt(project), encoding="utf-8")
        print(f"  {len(todo)} shot planlanacak. İstem hazır: {out}\n"
              f"  Panelde 'İstemi kopyala' → Claude'a yapıştır → gelen YAML'ı 'Planı uygula' kutusuna yapıştır.")
        return
    if provider == "anthropic":
        from .anthropic_planner import run
        run(project, cfg, todo)
        return
    raise SystemExit(f"Bilinmeyen planner.provider: {provider}")


def apply_plan_file(project: Project, path: Path) -> int:
    return apply_plan(project, parse_yaml_reply(path.read_text(encoding="utf-8")))
