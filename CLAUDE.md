# Working in this repo (instructions for Claude)

This is a video production pipeline for the YouTube channel **Stone Age Athlete** (ancient humans, the human
body and sports science, told with stick-figure drawings). The owner is a strength & conditioning coach; talk to
him in Turkish, write narration and planner output in English.

## Planning a video's visuals (the most common task)
When asked to "plan" a project (e.g. "002'yi planla"):
1. `python -m studio split <slug>` (safe to re-run; keeps existing visuals).
2. Read `docs/STORYBOARD.md` fully and look at `docs/catalog/*.png` before writing anything.
3. Read `projects/<slug>/storyboard.yaml`. Write `projects/<slug>/plan.yaml` mapping every shot id without a
   visual → `{visual: {...}, camera?: in|out|none, engine?: gemini}`. Follow the spec's rules: one idea per shot,
   continuity between consecutive shots, era colour code, numbers as pictures, no text in images,
   coach mascot for explanations.
4. `python -m studio apply-plan <slug> projects/<slug>/plan.yaml`, then `python -m studio images <slug>` and
   `python -m studio sheet <slug>`. **Look at `build/contact_sheet.png`** (and single shots when in doubt), fix
   shots that are wrong (overlaps, figures off the floor, hands not reaching props, image not matching the
   words), re-render with `--only`.
5. Default to the free svg engine. Suggest `engine: gemini` only for shots the recipe cannot express, and say
   how many such shots there are (they cost money).

## Writing narration
- Every factual claim needs a source listed in `projects/<slug>/sources.md`; do not round numbers into claims the
  source does not make (e.g. "university rowers", not "Olympic rowers").
- Short sentences, second person hooks, a turn ("but here is where they fell short"), and a closing
  "coach's lesson" that turns the science into training advice.

## Extending the drawing kit
Poses live in `studio/svgkit/figure.py` (joints relative to hip), props in `props.py`, backgrounds in
`backgrounds.py`. After adding anything: update `docs/STORYBOARD.md`, run `python -m studio catalog`, check the
catalog images, and run `python -m pytest -q`.

## Never
- Commit `.env`, `models/`, `projects/*/build/` or music files.
- Drive web UIs (e.g. Google Flow) with browser automation to generate images; use the official APIs only.
