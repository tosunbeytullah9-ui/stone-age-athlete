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
