# Motion scenes (Remotion)

Code-drawn scenes that animate in sync with the narration: the case-file card, the verdict stamp, charts that draw
themselves, a number that counts up, a timeline, a typed quote. They are free (rendered locally), look the same in
every video of a channel, and are re-rendered per language, so their words can be translated.

They replace a painting for one scene. Paintings stay the heart of the video; use motion scenes for the moments a
painting cannot carry well: the recurring brand beats (case file, verdict) and the 2–5 key numbers.

```yaml
- id: s179
  text: "Verdict: wrong."
  visual:
    comp: verdict
    word: WRONG
    belief: Eight glasses of water a day
    note: Not dangerous for most people. Not useless. Just wrong.
- id: s180
  text: Not dangerous for most people.
  visual: {same: true}
```

## How it works
- A scene is the head shot plus its `{same: true}` shots (as for paintings). Each shot start becomes a **beat**
  (frame offset from the scene start). Elements appear on their beat: the case-file field "SUBJECT" is typed when
  "Subject: you" is read; bar 2 grows when its number is said (`beat:` = index of the shot inside the scene, 0 = head).
- `images` renders a **poster** (the final state) into `shots/<id>.png`: contact sheet, panel, Shorts, end screen.
- `render` renders each motion scene as a clip of the scene's real length (+ the cross-fade tail) and cuts it in
  instead of a still picture; the scene holds still (no camera move, no ink reveal: it animates itself). Clips are
  cached by props + length + component code (`build/remotion/<lang>/`).
- The verdict stamp lands on the word "wrong" (or "right") — the same moment the stamp sound plays.
- Sound: motion scenes sit on the channel's desk ambience; charts (`bars`, `counter`, `timeline`, `quote`) get
  the channel's chart cue (`sound.chart`, a pen on You're Wrong!).
- Preview without a full render: `python -m studio motion-scenes <slug> --only s004,s179`
  → `build/remotion_preview/<id>.mp4` (uses the real timing when the voice exists). Panel: scene → **Hareketli**.

## Look (per channel)
`channel.yaml → remotion`:

```yaml
remotion:
  theme: ledger        # ledger (ruled paper, typewriter + handwriting, red pen, rubber stamp) | museum (painted paper)
                       # | pop (deep indigo stage, saturated flat colours, thick outlines, Fredoka + JetBrains Mono)
  # optional: ink, accent, wash, wash2, muted, bg, boil (line wobble in px), paper (default: chart_paper),
  # paper_rules: {first, step, margin} (the ruled lines of the paper in 1920×1080 px; ledger knows its own)
```
Ink and accent default to `thumbnails.ink` / `thumbnails.accent`; the paper is the channel's `chart_paper`.
Fonts are local and licence-checked (`remotion/public/fonts`): Special Elite (Apache-2.0, typewriter),
Patrick Hand (OFL, handwriting), Alfa Slab One (OFL, stamp).

## Catalogue
Every text value may be per language (`{en: "...", tr: "..."}`), or patched for one language with
`i18n: {tr: {...same keys...}}` (lists are patched item by item). Numbers on screen must come from a claim.

| comp | props | use it for |
| --- | --- | --- |
| `case-file` | `number` ("001"), `org`, `label` ("CASE FILE"), `fields: [{label, value, beat?}]`, `stamp` (small, optional) | the case-file opening. Field i appears on beat i+1 by default |
| `verdict` | `word` ("WRONG"), `label` ("VERDICT"), `belief` (struck through in red), `note` (written after the stamp, from beat 1), `hit` (seconds; set automatically from the word "wrong"), `hit_beat` (the stamp lands when shot N of the scene starts) | the verdict; also a cold open (`label: BELIEF`, `hit_beat: 1`, with a `stamp` sound on that shot) |
| `bars` | `bars: [{label, value, display?, color?, beat?}]`, `title`, `of` (the whole, e.g. 100 → dashed full length), `max`, `unit` ("%"), `decimals`, `note` | 1–4 quantities compared; part of a whole (`of`). `display` replaces the counted number once the bar is drawn ("< 2%") |
| `counter` | `value`, `from`, `decimals`, `prefix`, `suffix`, `label` (beat 1), `note` (beat 2), `duration` (s), `thousands` | one big number: a sample size, a count |
| `timeline` | `events: [{when, text, beat?, highlight?}]`, `title` | 2–5 dated steps (how a myth grew) |
| `quote` | `text`, `source`, `highlight` (part of the text, underlined in red) | a document quoted word for word |
| `mech` | `items`, `defs`, `camera`, `drift`, `bg` (see below) | a mechanism, force, wave or formula drawn by code, moving on spoken words |

## `mech`: code-drawn mechanisms that move on the exact word
A whole scene drawn by code on a 1920×1080 design canvas (fitted to any output size): shapes, gears, springs,
arrows, waves, gauges, particles, labels and formulas. Built for channels whose pictures are mostly diagrams
(Drawer Physics, theme `pop`). Every movement is tied to the narration:

| cue (`at`, `in`, `out`, `spin.from`…) | starts |
| --- | --- |
| `2` | when shot 2 of the scene starts (0 = the scene's first shot) |
| `"@valve"` | when the word "valve" is said in the scene (`@valve#2` = the second time, `@valve+0.3` = 0.3 s later, `@spring*` = any word starting with "spring"; plurals match) |
| `"t1.5"` / `"b2+0.4"` | 1.5 s after the scene start / 0.4 s after shot 2 starts |

Word times come from `align` (studio/words.py): exact with ElevenLabs/estimate, from faster-whisper word
timestamps when installed, otherwise split by character weight inside the shot. A cue whose word is not in the
scene's shots starts at the scene start and `render` prints a warning.

```yaml
visual:
  comp: mech
  camera: [{at: "@sliver", x: 1180, y: 560, zoom: 1.5, dur: 1.4}]   # optional; a slow push-in is on by default (drift)
  items:
    - {kind: gear, id: fw, x: 1395, y: 740, r: 100, teeth: 22, fill: yellow, in: "@second", spin: {speed: -110, from: "@drives"}, glow: yellow}
    - {kind: arrow, x: 1300, y: 520, to: [-300, 0], color: sky, bend: -30, in: "@drag"}
    - {kind: label, x: 1395, y: 640, to: [-560, 160], text: small teeth, in: "@teeth"}
    - {kind: formula, x: 960, y: 200, text: "pressure = force ÷ area", in: "@divided", bg: bg2}
    - {kind: rect, x: 760, y: 640, w: 420, h: 160, fill: sky, keys: [{at: "@shrink", w: 60, dur: 1.2}]}
```

**Every item:** `x, y` (origin), `rotate`, `scale`, `sx`, `sy`, `opacity`, `pivot: [x, y]` (rotation centre, local),
`fill`, `stroke` (default the outline colour), `sw`, `dash`, `glow` (a coloured halo: the part being talked about),
`in` (cue, or `{at, fx: pop|fade|draw|grow|slide|type|none, dur}`; lines/arrows draw, text types, the rest pops),
`out` (cue), `keys: [{at, dur, ease, <any numeric or colour prop>}]` (eases: inOut, out, in, linear, back, bounce,
elastic), `spin: {speed °/s, from, to}`, `bob`, `pulse: {amount, period, from, to}`, `shake: {at, amount}`.
Colours are palette names of the theme (`yellow, gold, orange, coral, red, pink, violet, blue, sky, teal, mint, lime,
steel, steel2, dark, cream, white, hot, cold, steam, food, line, text, muted, bg, bg2`) or any CSS colour.

| kind | props |
| --- | --- |
| `group` | `items`, `clip: [x, y, w, h]` — children move with it (a blade with its handle around the pivot) |
| `use` | `def: name` + overrides — a drawing from the scene's `defs` |
| `rect` / `circle` / `ellipse` | `w, h, r (corner), ax, ay (anchor 0..1, default centre)` / `r` / `rx, ry` |
| `path` / `poly` | `d` (SVG path, local) / `points: [[x, y]…]`, `closed` |
| `line` / `arrow` | `to: [dx, dy]`; arrow: `color`, `bend`, `head` |
| `spring` | `to`, `coils`, `width`, `value` (length factor: 1 rest, 0.5 squeezed) |
| `gear` | `r, teeth, depth, hole` (spin it) |
| `wave` | `w, amp, length (wavelength), speed (Hz), standing: true, value (amplitude factor), color` |
| `gauge` | `r, value 0..1` (needle; animate `value`) |
| `particles` | `w, h, count, size, speed, mode: gas \| steam \| bubbles, value (energy: animate it = heat up), color` |
| `text` / `formula` / `counter` | `text`, `size`, `align`, `bg` (pill), `maxW`; formula uses the mono face; counter: `value, decimals, prefix, suffix` |
| `label` | a callout: dot at (x, y), leader line to `to`, the words in a pill (`text, size, bg, color`) |

**Numbers on a `mech` scene** must be in a claim of the video or said in the scene's own sentences; illustrative
maths ("say your hand is five times farther") is marked `example: true` on the item and labelled "example" on
screen (`apply-plan` and `check` enforce it). Top-level text and labels are kept inside the canvas.
Thumbnails can be code-drawn too: `thumbnails[n].visual: {comp: mech, items: [...]}` (rendered as a still, free).
A long video's scenes are best written as code (helpers for the recurring objects): see
`channels/drawer-physics/projects/001-*/scenes.py` → `python scenes.py > plan.yaml` → `apply-plan`.

## Rules
1. One idea per scene, words short: titles ≤ 10 words, bar labels 1–3 words, timeline notes ≤ 8 words.
2. Every number on a motion scene is in `claims.yaml` (the gate still checks the shots that say it). Do not round
   a number into something the source does not say (`≥ 5%` if the source says "at least five percent").
3. Do not put an `overlay` on a motion scene's shots that repeats what the scene already writes.
4. 4–8 motion scenes in a long video. The case file and the verdict are the channel's signature beats; the rest are
   numbers. Never two motion scenes in a row unless the narration really moves from one number to the next.
5. After changing props, look at the poster (`images --only sNNN`, panel) and the clip (`motion-scenes --only sNNN`).

## Rules per channel (every video gets its motion scenes by itself)
Which scenes are motion scenes is decided by the channel, the same way in every video, so nobody chooses them by
hand (`studio/motion_rules.py`):

```yaml
remotion:
  theme: ledger
  scenes:                          # off when missing (the channel then has only hand-placed motion scenes)
    cold_open: true                # the first sentence restates the belief → "BELIEF: …" struck through, stamp after it
    case_file: {org: BUREAU OF HUMAN ERROR}   # "Case file zero zero N." + "Subject: …" (+ "Belief: …") → typed card
    verdict: {note: true}          # "Verdict: wrong." → stamp on the word, the rest of that scene written under it
    data: {min: 2, max: 6}         # key numbers / quotes / dated steps, taken from the claims
```

- **Signature beats** (cold open, case file, verdict) are read from the script's fixed structure: deterministic, free,
  idempotent. They run after every `plan` / `apply-plan` / panel "Planı uygula", and with `motion-plan`. The cold open
  is used only when the opening sentence really says the belief (≥ 2 shared words and ≥ 35 % of the belief's words);
  otherwise the opening painting stays.
- **Data scenes** (`bars`, `counter`, `timeline`, `quote`) are chosen by the planner (Gemini/Anthropic) inside `plan`,
  or by `motion-prompt` (manual provider: a prompt file for Claude, the answer goes into "Planı uygula"). Every number
  must appear in a claim linked to the scene's shots (a timeline may use any claim of the video), a quote must be a
  claim's `quote` (or words quoted inside the claim text). Anything else is **skipped** by `apply-plan` and blocks the
  quality gate, so an invented or rounded number never reaches a video.
- `python -m studio motion-auto <slug>` = signature beats + data scenes when the video has fewer than `data.min`.
  Panel: 2 · Sahneler → **Hareketli sahneleri kur**.
- Per video (`project.yaml`): `motion: {cold_open: false | true, case_file: false, verdict: false, belief: "…"}`
  (`cold_open: true` forces it; `belief` replaces the belief read from "Belief: …").
- The gate (`check`) warns when a signature beat is missing or the number of data scenes is outside `data`.

New video: write script → `split` → `plan` (signature + data scenes come with it) → `check` → `images` (posters are
free; only the paintings cost) → `render`.

## Installation (once per computer)
Node.js LTS: `winget install OpenJS.NodeJS.LTS`, then reopen the window. The npm packages are installed on the
first motion scene (or `python -m studio remotion-setup`); `guncelle.bat` refreshes them when `remotion/package.json`
changes. Remotion downloads its own headless Chrome once. Without Node.js the factory still runs: motion scenes stay
their poster frame (or a text card) and `check` warns.

Settings (`config.yaml → remotion`): `concurrency` (frames rendered at the same time, 0 = automatic),
`browser` (path to a Chrome/Chrome Headless Shell instead of the download).

Licence: Remotion is free for individuals and companies of up to 3 people (commercial use included); a bigger
company needs a Remotion company licence (remotion.dev/license).

## Adding a component (developers)
`remotion/src/comps/<Name>.tsx` (use `usePageScene`, `Page`, `Write`, `Draw`, `Wash`, `Stamp` from `src/lib`),
register it in `src/comps/index.ts` with example props, add its id to `studio/remotion.py → COMPS` (and required
props to `validate`), document it here and in docs/STORYBOARD.md, run `npx tsc --noEmit` in `remotion/` and
`python -m pytest -q`. `npm run studio` in `remotion/` opens Remotion Studio with the examples.
