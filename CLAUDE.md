# Working in this repo (instructions for Claude)

A local **video factory**: several YouTube channels share one production pipeline and one local web panel
(`python -m studio web`, http://127.0.0.1:8765). The owner is a strength & conditioning coach; talk to him in
Turkish; write narration, storyboards and planner output in English (translations go into shot `i18n`).

Layout: `channels/<channel>/{channel.yaml, ideas.yaml, projects/<slug>/}`. Every CLI step takes
`<slug> --channel <channel> [--lang xx]`; the default channel is `factory.default_channel` in config.yaml.

## Planning a video's visuals (most common task)
When asked to "plan" a project (e.g. "002'yi planla"):
1. `python -m studio split <slug> --channel <c>` (safe to re-run; keeps existing visuals).
2. Read `docs/STORYBOARD.md` fully and look at `docs/catalog/*.png` before writing anything.
3. Read the storyboard. Write `channels/<c>/projects/<slug>/plan.yaml` mapping every unplanned shot id →
   `{visual: {...}, camera?: in|out|none, engine?: gemini}`. Rules: one idea per shot, continuity between
   consecutive shots, era colour code, numbers as pictures, no text in images, mascot for explanations.
4. `python -m studio apply-plan <slug> <plan.yaml> --channel <c>`, then `images` and `sheet`. **Look at
   `build/contact_sheet.png`** and single shots; fix overlaps, floating figures, hands missing props, images that
   don't match the words; re-render with `--only`.
5. Default to the free svg engine; propose `engine: gemini` only where the recipe can't express the scene and say
   how many such (paid) shots there are.

## Translating
`python -m studio translate <slug> --lang tr` writes a prompt; answer it as YAML `sNNN: "..."` (natural spoken
language, same shot boundaries, ±30% length), then `apply-translation <slug> <file> --lang tr`.

## Writing narration
- Every factual claim has a line in `sources.md` (claim + link). Never round a number into a claim the source does
  not make (e.g. "university rowers", not "Olympic rowers"). The quality gate blocks projects with <3 sources.
- Short sentences, second-person hook, a turn ("but here is where they fell short"), closing "coach's lesson".
- Use the idea bank (`ideas.yaml`, priority A first) and the research doc; avoid saturated titles.

## Extending the drawing kit
Poses: `studio/svgkit/figure.py` (joints relative to hip). Props: `props.py`. Backgrounds: `backgrounds.py`.
After adding: update `docs/STORYBOARD.md`, run `python -m studio catalog`, check the images, run `python -m pytest -q`.

## Never
- Commit `.env`, `models/`, `channels/*/projects/*/build/` or music files.
- Drive web UIs (e.g. Google Flow) with browser automation to generate images; use official APIs only.
