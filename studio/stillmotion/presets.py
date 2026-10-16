"""Style presets: the motion a picture gets when nobody planned it, and the base every plan builds on.

painterly   painted/realistic pictures: depth parallax camera, nothing else
ledger      flat drawings on paper (ink, doodles, notebooks): flat camera + gentle line boil
flat        anything flat (charts, diagrams, UI, photos of documents): flat camera only
"""
from __future__ import annotations

PRESETS: dict[str, dict] = {
    "painterly": {"camera": {"amount": 0.07, "parallax": 0.55}},
    "ledger": {"camera": {"amount": 0.05, "parallax": 0.0},
               "fx": [{"type": "boil", "amount": 1.0, "rate": 6}]},
    "flat": {"camera": {"amount": 0.05, "parallax": 0.0}},
    "none": {"camera": {"move": "none", "amount": 0.0}},
}

CYCLE = ("in", "right", "out", "left")


def auto_spec(index: int, preset: str = "painterly", move: str | None = None) -> dict:
    """Spec for the index-th picture of a video when it has no plan: moves rotate so neighbours differ."""
    base = PRESETS.get(preset, PRESETS["painterly"])
    cam = dict(base.get("camera") or {})
    cam["move"] = move or cam.get("move") or CYCLE[index % len(CYCLE)]
    return {"camera": cam, "fx": [dict(e) for e in base.get("fx", [])], "seed": index + 1}
