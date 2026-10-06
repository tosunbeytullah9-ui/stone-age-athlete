# Storyboard format (scene planning spec)

`channels/<channel>/projects/<slug>/storyboard.yaml` has one entry per **shot**: a short piece of narration
(`python -m studio split` creates id, para, sent, text). Shots stay small because captions, on-screen text,
claims and translations are timed per shot.

Pictures are planned per **scene**: one painting that stays on screen for **5–9 seconds** (about 2–4 shots, ~15–25
words) while the camera slowly moves over it. The first shot of a scene gets the painting; the following shots of
the same scene get `visual: {same: true}`. A 10-minute video has roughly 70–100 scenes.

```yaml
shots:
  - id: s020
    text: "Throwing let a hunter hurt an animal"
    visual:
      prompt: "An early human hunter in tall golden savanna grass at dusk, body coiled, throwing arm cocked far
               back with a stone, a herd of antelope grazing at a safe distance, low warm sunlight"
      characters: []              # [coach] when the coach is in the picture
    camera: in                    # optional: in | out | left | right | none (default: rotates scene by scene)
  - id: s021
    text: "without getting close to its horns or teeth."
    visual: {same: true}          # same painting, the camera keeps moving
  - id: s022
    text: "But for a long time,"
    visual:
      prompt: "The same hunter a moment later, the stone flying in a long arc toward the herd"
      ref: s020                   # optional: paint it as the next moment of scene s020 (same place, light, people)
  - id: s062
    text: "The braces limited how far the arm could rotate."
    visual:                       # a chart, drawn as a vector (numbers as pictures, never digits)
      bg: plain_warm
      props: [{type: bar_chart, x: 960, y: 860, values: [1.0, 0.92], colors: [ochre, water]}]
```

## The look (set per channel, do not repeat it in prompts)
Every prompt is automatically prefixed with the channel's `visual_style` (channel.yaml) and suffixed with
"no text, no numbers, no logos". Describe only the **scene**: who, doing what, where, light, camera distance.

## Rules for good scenes
1. **The picture shows what the words mean.** The viewer hears the words while seeing the picture. Prefer the
   concrete moment (a pitcher at full extension, a Bajau diver gliding over a reef) over abstract symbols
   (question marks, lightbulbs, whiteboards).
2. **5–9 seconds per painting.** Start a new scene when the narration moves to a new place, person, time or idea;
   otherwise continue with `{same: true}`. Never more than ~4 shots (≈ 10 s) on one painting.
3. **Write prompts like a film director.** Subject + action + setting + era details + light + framing:
   "close-up of", "wide shot of", "over-the-shoulder", "low angle". Name real body parts, real tools, real places.
   40–80 words. Say how many people. Give people age, build and period clothing.
4. **Variety of framing.** Alternate wide establishing shots, medium shots and close-ups (hands, eyes, a shoulder
   joint, a spear tip). A good sequence: wide → medium → close-up → wide.
5. **Continuity.** When a scene is the next moment of the previous one (same people, same place), add
   `ref: <id of that scene>` and say "the same ..." in the prompt.
6. **The coach** (`characters: [coach]`) appears when the narration speaks to the viewer: the hook ("you"), the
   turn, explanations of how the body works today, and the coach's lesson. Show her *doing* something (coaching an
   athlete, demonstrating a movement, holding a bone model, in a gym or on a track), not just standing. Roughly
   10–20% of scenes.
7. **Era and setting.** Ancient scenes: warm earthy light, accurate period clothing and tools. Modern scenes:
   gyms, labs, stadiums, homes, cooler light. Scientific moments: real lab equipment, scientists at work, X-rays,
   anatomical cut-aways painted like a museum plate.
8. **Anatomy and science.** For "how it works" moments use painted anatomical illustrations: "a cut-away
   painting of a human shoulder showing the tendons and ligaments stretched like a slingshot band".
9. **Numbers become charts.** When the words compare quantities (twice as fast, 92%, 35 → 64), use a chart
   recipe (`bg` + `props`, below) or a picture that shows the size difference (a small and a large spleen side by
   side). Charts animate in automatically. Use 2–5 charts per video, not more.
10. **No text inside paintings.** Never ask for words, numbers, signs, labels, scoreboards or book pages that can be
    read. Numbers go into `overlay` (drawn by the factory, translated per language).
11. **Safe prompts.** No gore or blood, injuries are shown as a hand holding a shoulder or a red glow on a joint;
    hunting shows the throw, not the kill. Real living people (named scientists) are shown as "a scientist", never
    as a likeness.

## Charts (vector, free)
`bg: plain_warm | plain_cool` and `props` from: `bar_chart {values, colors}`, `line_chart {values, values2}`,
`pie {value}`, `gauge {value}`, `meter {value}`, `battery {value}`, `people {n, k}` (k of n highlighted),
`balance {tilt: -1..1}`, `timeline {n, highlight}`, `arrow {to: [x, y]}`, `check`, `cross`. Values are relative
0..1. Canvas 1920 × 1080; baseline ≈ 900; bar/line charts stand on `y`, dials and people are centred on (x, y).
Colours: `ochre` (ancient/us), `water` (modern/them), `good` (green), `bad` (red), `clay`, `stone`, `night`.
Add `overlay` with the real numbers. Charts hold still (no camera move) and grow in.

## On-screen text (`overlay`, drawn per language at render time — the picture itself stays text-free)
Use sparingly (the 2–4 key numbers of a video, a label that removes confusion):
`overlay: {kind: stat, text: "+11–16%", i18n: {tr: "%11–16"}}` big number · `kind: label` caption band ·
`kind: cite` small source line (added automatically for claims marked `on_screen`). Optional `pos: top|center|bottom`.
An overlay goes on the shot whose words say the number, even when that shot is `{same: true}`.

## Reply format for the planner
Only a YAML mapping from shot id to its entry, for every shot listed under "Plan these shots":

```yaml
s001:
  visual: {prompt: "...", characters: [coach]}
  camera: in
s002:
  visual: {same: true}
s003:
  visual: {prompt: "...", ref: s001}
```
