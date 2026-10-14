# Sound design (ambience + effects)

A narrated video with nothing under the voice feels like a slideshow. The factory now layers sound under every
scene, automatically, so the viewer feels *inside* the picture: a murmuring crowd under a market, a quiet hum in a
lab, a gulp when someone drinks, a page turning when the story moves on.

```
voice (narration)              centre, -14 LUFS after the final loudness pass
music (optional)               audio.music, ducked 15-20 dB under the voice
ambience  ── one bed per scene  audio.ambience_db (default -22 dB vs. the voice), dips audio.duck_db (5 dB) under speech
effects   ── on words / actions audio.sfx_db (default -12 dB vs. the voice)
```

Output is stereo (beds and effects spread left and right, the voice stays in the middle).

## Music
Put licence-safe tracks (YouTube Audio Library "no attribution required", your own) into
`assets/music/<channel id>/` (never committed). The factory plays them in name order, one per chapter
(`project.yaml → chapters`, at least 60 s each), fades between them, keeps them `audio.music_db` (-16 dB) under the
voice in pauses and another `audio.music_duck_db` (8 dB) lower while the narrator talks, and goes silent for a
moment before "Verdict:" so the verdict lands. Name tracks 01_..., 02_... to control the order.

## How it decides (studio/sound/designer.py)
- **Ambience**: read from the scene's picture prompt. The setting named first wins: "A 1980s newsroom … a park
  outside" → office. Mortimer's desk (`characters: [clerk]`), anatomy plates, maps and charts → `archive`.
  Old streets/markets → `street_old`, modern ones (years, cars, pedestrians) → `city`.
- **Effects from the picture** (once per scene, ~0.6 s in): drinking → gulp, pouring → pour, coins, bells, running
  feet, cheering crowds, sword clashes, horses, typewriters, chalk ...
- **Effects from the words**: "drinks", "paid", "coins" ... land on the word itself.
- **The channel's own sound language** (`channel.yaml → sound`): `transition` when a new paragraph opens on a new
  picture (at most every 20 s), `chart` when a chart grows in, `case_file` on "Case file …", `verdict` on "Verdict:".
- Rationing: at least 1.2 s between any two effects, cooldowns per sound (a gulp at most every 25 s), so it stays
  documentary, never cartoon.

## Overriding (storyboard.yaml, or plan.yaml → apply-plan)
```yaml
- id: s042
  text: "He drinks the whole jug."
  visual: {prompt: "..."}
  sound:
    amb: rain                          # bed for the whole scene (scene head only); none = silence
    sfx: [{id: gulp, at: drinks, db: -3}]   # at = a word of this shot or seconds from its start; [] = no effects
```
`python -m studio sound <slug>` prints the plan (which bed, which effect, why) without rendering; it is also saved
to `build/<lang>/sound_plan.json`. `check` warns about unknown sound names.

## Where the sounds come from (studio/sound/catalog.py)
1. **Built-in, made by code** (studio/sound/synth.py): no licence, no download, no attribution.
   Beds: room archive home office rain wind sea fire night forest murmur street_old city lab gym hall battle stadium
   ship desert tavern. Effects: gulp sip pour drip splash stamp paper page_turn pen tick clock knock footsteps coins
   bell ding whistle heartbeat whoosh pop boom impact riser sword cheer typewriter camera glass chalk gallop.
2. **Files in the shared library** (`library/sounds/catalog.yaml`): every entry has a licence; only CC0, CC-BY,
   Pixabay, YouTube Audio Library, own recordings or generated audio are accepted. CC-BY gets a credit line.
   `python -m studio sounds-fetch` downloads entries that have a url into `library/sounds/files/` (not in git).
   A file may replace a built-in id (e.g. a real recording called `gulp`); while it is missing the `fallback` plays.
3. Listen to everything: `python -m studio sounds-demo` → `build/sounds_demo.wav` + an index with timestamps.

Never use BBC Sound Effects (RemArc licence = non-commercial) or CC-BY-NC sounds on a monetised channel.

## Writing for sound
Leave room for it in the script: a short beat after a punchline, an action the viewer can hear ("He drinks.
Again."), a scene that *sounds* like somewhere (a market, a storm, a stadium). One audible moment every 20-40 s is
plenty.
