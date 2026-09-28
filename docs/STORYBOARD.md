# Storyboard format (visual planning spec)

`channels/<channel>/projects/<slug>/storyboard.yaml` has one entry per shot. `python -m studio split` creates the
entries (id, para, sent, text); the **planner** fills `visual` for each one. This file is also the
instruction sheet given to the planner (Claude in chat, or the Anthropic API).

```yaml
shots:
  - id: s007
    text: "A woman kneels over a flat stone,"
    visual:                      # a scene recipe → drawn for free by the svg engine
      bg: savanna
      bg_opts: {sun: low, hut: true}
      figures:
        - {pose: kneel_grind, x: 780, wear: [hair_bun, hide], face: focused, sweat: true}
      props:
        - {type: quern, x: 1120}
        - {type: grain, x: 1360, y: 815}
    camera: in                   # optional: in | out | none
  - id: s042
    text: "a herd of mammoths thundering across the frozen plain"
    engine: gemini               # optional: force the paid AI engine for this one shot
    visual:
      prompt: "a herd of woolly mammoths running across a snowy plain, tiny stick-figure hunters watching from a ridge"
      characters: [coach]        # optional character lock (+ reference image if assets/refs/coach.png exists)
```

## Rules for good shots
1. **One idea per shot.** The image must show what the words say *right now* (the viewer hears it while seeing it).
2. **Continuity.** Consecutive shots about the same moment keep the same background and figure positions;
   change only what the words change (pose, a prop, face). This makes the video feel animated.
3. **Era colour code.** Modern life → `gym`, `living_room`, `office`, `plain_cool`. Ancient life → `savanna`,
   `forest`, `cave`, `night_camp`, `plain_warm`. Then-vs-now comparisons → `split`.
4. **Numbers become pictures.** Comparisons use `bar_chart`, two `bone`s of different `thick`, `bone_section`
   with different `density`, `check`/`cross`, `arrow`.
5. **No text inside images.** Never put words or numbers in a prompt or recipe.
6. **The coach** (mascot) = `{pose: point, wear: [headband, whistle], hold: pointer, face: smile}`. Use him when the
   narration explains, compares or gives advice (usually `classroom` background).
7. Prefer the svg recipe. Use `engine: gemini` + `prompt` only for scenes the recipe cannot draw
   (crowds, detailed animals other than deer/mammoth, landscapes with water, close-ups of objects).

## Canvas
1920 × 1080. `x` is horizontal position (0 left → 1920 right). Floor height depends on background
(≈770–880); figures and floor props stand on it automatically, so `y` is usually omitted for them.
A standing figure at scale 1 is ~450 px tall. Keep main figures between x = 350 and 1570.

## Backgrounds (`bg`, options in `bg_opts`)
| name | options | floor y |
| --- | --- | --- |
| gym | clock: "7:00", rack: true/false | 830 |
| living_room | night: true/false, clock | 860 |
| office | clock | 860 |
| plain_cool / plain_warm | — | 900 |
| savanna | sun: low/high/null, hut: bool, trees: bool | 770 |
| forest | — | 800 |
| cave | fire: bool | 850 |
| night_camp | fire: bool | 800 |
| classroom | (board centred at x 1240, y 485, 960×690; left half x 760–1240, right half 1240–1720) | 880 |
| split | left half ancient, right half modern; divider at x 960 | 840 |

## Figures (`figures:` list)
`pose` (required): stand, walk, run, overhead_lift, sit, sit_slouch, kneel_grind, kneel, point, carry,
squat_rest, throw, lie, wave, celebrate, think, bend_dig, climb, tired_bent
Options: `x`, `ground`, `scale` (1.0; 0.5–0.7 for small/distant), `flip` (true = faces left),
`face` (neutral, smile, strain, tired, surprised, sad, focused, sleep), `look` (-10..10 eye shift),
`wear` (headband, whistle, hair_bun, hide, beard, cap), `hold` (barbell, dumbbell, phone, spear, pointer,
rock, log, stick, torch, bowl), `sweat` (bool).
Tips: sit/sit_slouch need a `sofa`/`chair` prop under them (sofa seat top ≈ floor − 200);
kneel_grind hands reach ~ x+320, put a `quern` there; ancient people wear `hide`, women `hair_bun`.

## Props (`props:` list; `type` + `x`, `y`, `scale`, options)
Floor objects (y = floor by default): sofa, chair, desk (laptop: bool), tv, dumbbell_rack, mat, treadmill,
hut, quern, grain, campfire, tree, acacia, rock, bush, deer (flip), mammoth (flip), footprints (n),
spear_ground.
Floating (give x, y = centre): clock (time "H:MM"), window (night), sun, moon, board (w, h, divider),
bone (thick 0.6–1.4, length), bone_section (density 0–1), icon_quern, icon_oar,
bar_chart (y = baseline; values [0..1,...], colors [...]), arrow (to: [x2, y2], color),
check, cross, question, heart, calendar, zzz, sweat, motion (direction both/left/right/speed),
effort, rain.
Colours may be palette names (ochre, sand, olive, clay, stone, grain, water, good, bad, metal, …) or hex.

## Visual catalogs
See `docs/catalog/poses.png`, `props.png`, `backgrounds.png` (regenerate: `python -m studio catalog`).
