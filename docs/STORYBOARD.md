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
3. **Era colour code.** Modern life → `gym`, `living_room`, `office`, `track`, `lab`, `plain_cool`. Ancient /
   natural life → `savanna`, `forest`, `cave`, `night_camp`, `desert`, `steppe`, `mountain`, `arctic`, `shore`,
   `village`, `arena`, `gymnasium`, `dojo`, `plain_warm`. Water → `sea`, `underwater`. Then-vs-now → `split`.
4. **Numbers become pictures.** Comparisons use `bar_chart`, `line_chart`, `pie`, `gauge`, `meter`, `battery`,
   `people`, `balance`, `timeline`, two props of different `scale`/`size` (bone thick, spleen size, heart size,
   lungs fill, muscle_fiber fast, eye pupil…), `check`/`cross`, `arrow`. All values are relative 0..1.
5. **No text inside images.** Never put words or numbers in a prompt or recipe.
6. **The coach** (mascot) = `{pose: point, wear: [headband, whistle], hold: pointer, face: smile}`. Use him when the
   narration explains, compares or gives advice (usually `classroom` background).
7. Prefer the svg recipe. Use `engine: gemini` + `prompt` only for scenes the recipe cannot draw
   (crowds, big battles, city streets, animals not in the props list, close-up faces).
8. **Close-ups and variety.** Add `frame: {x, y, zoom}` (zoom 1.3–2.2, centre of interest in drawing coordinates)
   when a face, hand or object matters: the drawing is vector, so a close-up is free and sharp. On phones a
   full-frame figure is tiny. Do not stay on one background for more than ~5 shots in a row, and keep any single
   background under ~35% of the video (the whiteboard/classroom included).

## On-screen text (`overlay`, drawn per language at render time — the image itself stays text-free)
Use sparingly (the 2–4 key numbers of a video, a label that removes confusion):
`overlay: {kind: stat, text: "+11–16%", i18n: {tr: "%11–16"}}` big number · `kind: label` caption band ·
`kind: cite` small source line (added automatically for claims marked `on_screen`). Optional `pos: top|center|bottom`.
Charts (`bar_chart`, `line_chart`, `meter`, `gauge`, `battery`, `pie`) grow in automatically (`animate: false` stops it).
Consecutive shots on the same background cross-fade, so a newly added prop fades in: keep continuity.

## Canvas
1920 × 1080. `x` is horizontal position (0 left → 1920 right). Floor height depends on background
(≈770–960); figures and floor props stand on it automatically, so `y` is usually omitted for them.
A standing figure at scale 1 is ~450 px tall. Keep main figures between x = 350 and 1570.
`frame: {x: 900, y: 600, zoom: 1.8}` on a visual shows only that part of the canvas (a close-up).

## Backgrounds (`bg`, options in `bg_opts`)
| name | options | floor y |
| --- | --- | --- |
| gym | clock: "7:00", rack: true/false | 830 |
| living_room | night: true/false, clock | 860 |
| office | clock | 860 |
| plain_cool / plain_warm | — | 900 |
| track | modern running track + stands | 860 |
| lab | modern lab bench, microscope, screen | 860 |
| savanna | sun: low/high/null, hut: bool, trees: bool | 770 |
| forest | — | 800 |
| cave | fire: bool | 850 |
| night_camp | fire: bool | 800 |
| desert | pyramids: bool, sun: high/low/null | 800 |
| steppe | yurt: bool (ger at x 1500) | 790 |
| mountain | flag: bool (on summit), camp: bool (tent x 1500), snow: bool | 820 |
| arctic | igloo: bool (x 1450), sun: bool | 800 |
| shore | river/lake behind (y 640–800); reeds: bool, boat: bool | 800 |
| village | stilts: bool (stilt houses over water, floor 820; else huts, floor 800) | 800 / 820 |
| arena | Roman amphitheatre arches, sand floor | 820 |
| gymnasium | ancient Greek colonnade | 820 |
| dojo | paper walls, wooden floor; ring: bool (sumo ring x 380–1540 → floor 800) | 860 / 800 |
| sea | horizon 560, water line 760 (= floor); boat: bool (canoe x 960, sitters ground 735), stilts: bool (house x 1520, deck = ground 540), island: bool, sun | 760 |
| underwater | surface line y 120, seabed = floor; surface, rays, plants: bool | 960 |
| classroom | (board centred at x 1240, y 485, 960×690; left half x 760–1240, right half 1240–1720) | 880 |
| split | left half ancient, right half modern; divider at x 960 | 840 |

## Figures (`figures:` list)
`pose` (required):
- everyday: stand, walk, run, sit, sit_slouch, sit_floor (cross-legged), squat_rest, kneel, kneel_grind, lie,
  wave, celebrate, think, point, tired_bent, bend_dig, climb, carry, carry_head (both hands steadying a load on
  the head), push (leaning into a block), pull (leaning back on a rope), crawl, march, throw
- training: overhead_lift, deep_squat (frontal, bar on shoulders), lunge, push_up, plank, sprint_start, jump
  (straight, feet off the floor — Maasai), leap (tuck jump), hang (from a bar), stretch (overhead side bend),
  club_swing (clubs up at shoulders), shiko (sumo leg raise)
- water: swim (horizontal crawl), dive (head-down), float (spread, weightless), tread (upright, arms sculling)
- war & sport: draw_bow, guard (sword up, shield forward), wrestle (lean-in grip), ride (seated astride), row (paddling)
Options: `x`, `ground`, `lift` (px above ground; mid-water or mid-air), `rotate` (deg, tilt the whole pose),
`scale` (1.0; 0.5–0.7 for small/distant), `flip` (true = faces left),
`face` (neutral, smile, strain, tired, surprised, sad, focused, sleep), `look` (-10..10 eye shift),
`wear` (list): headband, whistle, hair_bun, hide, beard, cap, roman_helmet, knight_helmet (covers face),
samurai_helmet, goggles, turban, janissary_hat, beanie, fur_hood, topknot, headscarf, armor, tunic, parka
(fur coat + hood), loincloth, mawashi, tights (knee trousers/kispet), shoes, sandals, backpack, medal.
`hold` (one name or a list, e.g. `[sword, shield]`): barbell, dumbbell, phone, spear, pointer, rock, log, stick,
torch, bowl, bow, sword, shield (round), scutum (Roman), indian_club, meel, gada, kettlebell, fish, paddle, rope,
jar / basket / bundle (on the head with carry_head, else in the arms), baby, shaker. `sweat` (bool).
Tips:
- sit/sit_slouch need a `sofa`/`chair` prop under them (sofa seat top ≈ floor − 200);
  kneel_grind hands reach ~ x+320, put a `quern` there; ancient people wear `hide`, women `hair_bun`.
- **Rider:** `horse` prop and `ride` figure with the same `x` and `scale` → the rider sits in the saddle.
- **Swimmer / diver:** on `underwater` use swim/dive/float/tread with `lift: 250–550` (the default ground is the
  seabed); add `bubbles` above the head and `fish`. At the surface of `sea`: `tread` with `ground: 880` plus a
  `water_surface` prop (y 760) and `order: figures_first` so the water covers the lower body.
- **In a boat:** `sea` with `boat: true` (or a `boat` prop at the water line y); `row` + `hold: paddle`,
  `ground` = boat y − 25; use `order: figures_first` if the hull should hide the legs.
- **Two wrestlers:** `wrestle` at x = X − 252 and x = X + 252 with `flip: true` on the second (hands meet at X; at
  scale s use ±252·s). Sumo ring: bg `dojo` with `ring: true`, `wear: [mawashi, topknot]`.
- **Jumps:** `jump`/`leap` already float ~90 px; add `lift` for higher jumps (show the floor under them).
- **Hanging:** `hang` + `pullup_bar` (or `pullup_bar` with `ancient: true` = branch) with the same x and scale.
- **Treadwheel:** `walk` figure at the treadwheel's x with ground = floor − 505·scale.
- **Stilt house deck:** figure ground = house y − 220·scale.

## Props (`props:` list; `type` + `x`, `y`, `scale`, options)
Floor objects (y = floor by default; (x, y) = bottom centre):
- modern: sofa, chair, desk (laptop: bool), tv, dumbbell_rack, mat, treadmill, bed, barbell, kettlebell,
  pullup_bar (ancient: bool), oxygen_tank, microscope, radio, protein_tub, tent
- ancient/nature: hut, quern, grain, campfire, tree, acacia, palm, pine (snow: bool), reeds, seaweed,
  coral (color), rock, bush, footprints (n), spear_ground, amphora, indian_club (pair), meel (pair), treadwheel,
  pyramid, column (broken: bool), stone_block (sled: bool), pillar (Göbekli T-pillar), igloo, yurt, stilt_house,
  ice_hole, flag (color)
- animals (flip: faces left): deer, mammoth, horse (saddle: bool, color), chimp, gorilla, bear, cheetah (run: bool),
  seal, calf
- water: boat (y = water line; flip, outrigger: bool, sail: bool), water_surface (y = water line, w: width;
  see-through, draw over figures)
- charts on a baseline: bar_chart (values [0..1], colors), line_chart (values, values2, color, color2),
  timeline (y = the line; n ticks, highlight: index), balance (tilt -1..1)
Floating (x, y = centre):
- marks: clock (time "H:MM"), window (night), sun, sunbeam, moon, cloud (dark), rain, wind, heat, wave, splash,
  bubbles (n), snowflake, mountain_icon (flag), check, cross, question, heart (love/like), zzz, sweat,
  motion (direction both/left/right/speed), effort, arrow (to: [x2, y2], color), map_pin (y = tip; color),
  board (w, h, divider), calendar
- body: heart_organ (size 0.7–1.4, beat: bool), lungs (fill 0..1), spleen (size), brain, muscle (size, vertical),
  muscle_fiber (fast 0..1 = share of pale fast-twitch), tendon (thick), foot_arch (arch 0..1), knee_joint
  (cartilage 0..1), skull (chin: bool, brow: bool, flip), tooth (decay: bool), dna (n), blood_cells (n),
  mitochondria, eye (pupil 0..1), spine (pain: bool), sweat_gland (drops), fat_cell (size, n), bone (thick
  0.6–1.4, length), bone_section (density 0–1), pulse (rate 0.5–2, ECG line)
- objects: shield (kind round/scutum), sword, bow, helmet (kind roman/knight/samurai), sandal, shoe, dumbbell
  (ancient: stone halteres), pedometer (value), stopwatch (value), thermometer (value), scroll, book, bread,
  wreath, medal (color), icon_quern, icon_oar
- charts: pie (value, colors), gauge (value), meter (value, color, w), battery (value), people (n, k, cols, color)
Colours may be palette names (ochre, sand, olive, clay, stone, grain, water, sea, snow, ice, flesh, organ, vein,
bronze, steel, good, bad, metal, …) or hex.

## Visual catalogs
See `docs/catalog/poses.png` (poses, then every wear and hold item), `props.png`, `backgrounds.png`
(regenerate: `python -m studio catalog`).
