"""The fixed channel style for AI-generated images. Every Gemini prompt = STYLE + scene (+ character lock)."""
from __future__ import annotations

STYLE = (
    "Minimalist hand-drawn 2D illustration, clean bold black ink line art, doodle webcomic style. "
    "All humans are simple stick figures with round pure-white heads, black outlines, thin black limbs, "
    "no realistic anatomy, no skin tones. Flat muted earthy palette (ochre, sand, olive, clay) with subtle "
    "paper texture; modern-day scenes use cool grey-blue tones instead. The only saturated color is a single "
    "red accent. Full-bleed 16:9 scene with a simple grounded background, no borders, no text, no letters, "
    "no numbers, no watermark."
)

CHARACTERS = {
    "coach": "The coach character: a stick figure with a round white head, a red sweatband across the forehead, "
             "a whistle on a cord around the neck.",
}


def build_prompt(visual, extra_style: str = "") -> str:
    if visual is None:
        return ""
    if isinstance(visual, str):
        scene, chars = visual, []
    else:
        scene, chars = visual.get("prompt", ""), visual.get("characters", []) or []
    lock = " ".join(CHARACTERS[c] for c in chars if c in CHARACTERS)
    style = f"{STYLE} {extra_style.strip()}".strip()
    return f"{style}\n\nScene: {scene.strip()}" + (f"\n\n{lock}" if lock else "")
