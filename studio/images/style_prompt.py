"""The channel's fixed look for AI images. Every prompt = STYLE + scene + character descriptions.

The style and the recurring characters live in channel.yaml so each channel keeps its own identity:

  visual_style: "Hand-painted gouache illustration ..."
  characters:
    coach: {description: "The Coach: an athletic woman ...", ref: refs/coach.png}
"""
from __future__ import annotations

DEFAULT_STYLE = (
    "Hand-painted gouache illustration in the style of a natural-history museum mural: rich warm light, visible "
    "brush texture, painterly atmosphere, accurate believable anatomy, documentary mood, muted earthy palette."
)
RULES = (
    "Full-bleed 16:9 frame, cinematic composition with one clear subject. No text, no letters, no numbers, "
    "no captions, no labels, no logos, no watermark, no borders, no split panels."
)


def scene_prompt(visual) -> str:
    if isinstance(visual, str):
        return visual
    return (visual or {}).get("prompt", "") if isinstance(visual, dict) else ""


def build_prompt(visual, style: str = "", characters: dict | None = None) -> str:
    """style: channel visual_style ('' = default). characters: {name: {description, ref}} from channel.yaml."""
    scene = scene_prompt(visual).strip()
    if not scene:
        return ""
    names = visual.get("characters", []) if isinstance(visual, dict) else []
    chars = characters or {}
    lock = " ".join(str((chars.get(n) or {}).get("description", "")).strip() for n in names or [] if n in chars)
    if lock and any((chars.get(n) or {}).get("ref") for n in names or []):
        lock += " Keep the character exactly as in the attached reference sheet (face, hair, clothes)."
    parts = [(style or DEFAULT_STYLE).strip(), f"Scene: {scene}"]
    if lock:
        parts.append(lock)
    parts.append(RULES)
    return "\n\n".join(parts)
