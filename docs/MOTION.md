# Living pictures (motion inside the paintings)

When `video.motion: auto` (config.yaml, or per channel in `channel.yaml → overrides.video.motion`), every scene's
painting moves a little while it is on screen. Nothing is generated: the painting stays the painting, parts of it
move — free, local, on the CPU (`studio/stillmotion`, `studio/motion.py`). It is **off by default** (a render takes
2–3× longer the first time; cached re-renders are fast). `motion` and `motion-preview` work either way.

* **Without a plan** every picture gets the channel preset (`video.motion_preset`):
  `painterly` = depth-based 2.5D camera (near things slide and grow faster than the background) ·
  `ledger` = flat page camera + hand-drawn line boil · `flat` = flat camera.
* **With a plan** (`channels/<c>/projects/<slug>/motion.yaml`) chosen scenes also get local effects.
* Charts and other SVG scenes keep the classic camera (they grow in on their own).
* `video.motion: off` (default) keeps the classic FFmpeg zoompan camera.

The depth model (Depth Anything V2 Small, Apache-2.0, ~100 MB) downloads itself into `models/` the first time.
Scene clips are cached in `build/motion/` by picture + plan + length: re-rendering after a text change only
redoes the scenes that changed.

## Planning (Claude's job, after `images`)
1. `python -m studio motion <slug>` → `build/motion_sheet.png`: every scene picture with a 0..1 grid and its words.
   **Look at it.** Pick the 30–50 % of scenes where something in the picture can believably move.
2. Write `motion.yaml` (scene id = the scene's first shot):
   ```yaml
   s107:   # hunter by a campfire in a snowy forest
     camera: {move: in, parallax: 0.6, focus: [0.62, 0.42]}   # optional; omitted keys come from the preset
     fx:
       - {type: flicker, box: [0.28, 0.62, 0.47, 0.90], amount: 0.35}
       - {type: haze,    box: [0.31, 0.52, 0.43, 0.80]}
       - {type: embers,  box: [0.30, 0.42, 0.44, 0.84], count: 26}
       - {type: snow,    count: 70, size: 2.4, opacity: 0.55}
       - {type: breathe, box: [0.50, 0.08, 0.82, 0.86], amount: 0.008}
   ```
3. `python -m studio motion-preview <slug> --only s107,s020` → `build/motion_preview/<id>/`:
   `strip.png` (4 frames), `motion.png` (red = what moves, camera held still) and `preview.mp4`.
   **Look at strip.png and motion.png** — the red must sit on the thing that should move and nowhere else.
4. `render` as usual.

## Rules
1. **Move what would move in life**: grass, leaves, hair, cloth, water, fire, smoke, dust, snow, rain, light. Bodies
   only breathe (≤ 1 %) or swing a part a few degrees. Never animate faces, hands or anatomy in ways that distort them.
2. **Subtle.** The viewer should feel the picture is alive, not notice an effect. Start with the defaults.
3. **1–4 effects per scene**, boxes tight around the thing (box = [x0, y0, x1, y1], 0..1 of the picture).
4. **Respect the style**: painterly pictures → light (`screen`) particles and glows; ink/ledger pages → dark ink
   (`blend: multiply`, colour ~[40, 40, 45]), no parallax (a page is flat), `boil` already on.
5. **Tie it to the words when you can**: `from`/`to` (seconds from the scene start) make a glow appear when the
   narrator names the joint, a `shake` land on "stamp", a `sweep` cross the medal as it is mentioned.
6. Never let effects carry meaning on their own (no arrows, no text); numbers stay in `overlay`.

## Camera (`camera:`)
`move`: in · out · left · right · up · down · drift (slow 2.5D slide) · orbit (gentle circle) · none.
`amount` (default `video.zoom`), `parallax` 0..1 (painterly 0.55; 0 = flat), `focus: [x, y]` the zoom heads to
(a face, the ball), `ease`: smooth | linear | out.

## Effects (`fx:`)
Common keys: `box`, `shape` (ellipse | rect), `feather` (0..0.5), `depth: [lo, hi]` (only pixels in that depth
band, 1 = near — e.g. `[0, 0.3]` = the far background), `from`, `to`, `ramp`, `seed`.

| type | for | main keys (defaults) |
|---|---|---|
| `sway` | grass, crops, leaves, hair, cloth, flags | `amount` 5 px, `speed` 0.35, `anchor` bottom/top/left/right/none, `dir` x/y/xy |
| `ripple` | water surface, a drink | `amount` 3, `wavelength` 0.035, `speed` 0.5 |
| `haze` | heat above fire or hot ground | `amount` 2.5, `speed` 1.2 |
| `breathe` | chest, resting animal, a beating organ | `amount` 0.012 (scale), `period` 4 s, `anchor` bottom |
| `swing` | raised arm/axe, hanging lamp, branch | `angle` 2°, `period` 3 s, `pivot` [x, y] |
| `drift` | clouds, fog banks, smoke | `speed` 8 px/s, `angle` 0° |
| `boil` | ink/doodle line boil | `amount` 1.2, `rate` 8/s |
| `shake` | impact jolt | `at` [s, …], `amount` 10, `decay` 0.35 |
| `flicker` | firelight, torches, candles | `amount` 0.18, `speed` 1.8, `color` warm |
| `glow` | sore joint, lamp, magic, lit window | `amount` 0.55, `period` 1.8 (0 = steady), `color` [255,80,40] |
| `pulse` | heartbeat, attention on a detail | `amount` 0.15, `period` 1.2, `beat` true |
| `rays` | god rays through window/trees/water | `amount` 0.28, `angle` 20°, `speed` 4 |
| `sweep` | one sheen across metal, stone, a reveal | `from`/`to`, `width` 0.12, `amount` 0.45 |
| `fog` | mist, steam, underwater haze | `amount` 0.22, `speed` 0.08 |
| `dust` | motes in light; plankton (blue-white) | `count` 50, `size` 2.6, `speed` 10, `opacity` 0.55 |
| `embers` | sparks over fire/forge | `count` 35, `speed` 70 |
| `snow` | snow, ash | `count` 70, `speed` 45 |
| `rain` | rain streaks (ink: `blend: multiply`) | `count` 140, `angle` 12°, `length` 38, `opacity` 0.35 |
| `bubbles` | underwater, drinks | `count` 24, `size` 5, `speed` 55 |
| `sparkle` | glints on wet stone, stars, jewels | `count` 14, `size` 5 |

Particles and lights also take `color` ([r, g, b] or "#rrggbb") and `blend` (screen | multiply | normal).
Cost: a preset scene ≈ 30 ms per frame, a busy plan ≈ 70 ms (laptop CPU); `video.motion_workers` scenes in parallel.
