# Working in this repo (instructions for Claude)

**Video Fabrikası**: a local video factory. Several YouTube channels share one production pipeline and one local web
panel (`python -m studio web`, http://127.0.0.1:8765). The owner is a strength & conditioning coach; talk to him in
Turkish; write narration, storyboards and planner output in English (translations go into shot `i18n`).

Layout: `channels/<channel>/{channel.yaml, ideas.yaml, projects/<slug>/}` + the shared `library/sources.yaml`.
Every CLI step takes `<slug> --channel <channel> [--lang xx]`; the default channel is `factory.default_channel`
(`homo-athleticus`, brand: docs/BRAND.md; old id `stone-age-athlete` still resolves via `aliases`).

## Planning a video's pictures (most common task)
Pictures are AI paintings in the channel's look (`channel.yaml → visual_style`), one per **scene** of 5–9 s
(2–4 shots); the following shots of a scene are `visual: {same: true}` and the camera keeps moving over the picture.
Numbers are vector charts printed on the channel's paper (`chart_paper`). The recurring character is the coach
(`characters.coach`, reference sheet `channels/<c>/refs/coach.png`, attached to every picture she is in).
When asked to "plan" a project (e.g. "002'yi planla"):
1. `python -m studio split <slug> --channel <c>` (safe to re-run; keeps visuals, translations and remaps Shorts/claims).
2. Either `python -m studio plan <slug>` (Gemini plans it, `planner.provider: gemini`), or write
   `channels/<c>/projects/<slug>/plan.yaml` yourself following `docs/STORYBOARD.md` exactly (read it fully first)
   and run `apply-plan <slug> <plan.yaml>`.
3. `python -m studio check <slug>`: plan complete, no scene longer than 5 shots, coach in ≤30% of scenes.
4. `images` (paid: ~0.05 $ per scene; say how many scenes will be painted before running it on a whole video),
   then `sheet` and **look at `build/contact_sheet.png`**: pictures that don't match the words, wrong anatomy,
   text that slipped into a painting, the coach looking different. Fix the prompt and re-paint with `--only sNNN`.
   Unchanged scenes are cached and never paid twice.

## Motion scenes (Remotion: case file, verdict stamp, charts, counters, timelines, quotes)
Scenes can be code-drawn and animated instead of painted: `visual: {comp: verdict, word: WRONG, belief: "..."}`
(docs/REMOTION.md: catalogue, props, rules; components in `remotion/src/comps/`, bridge `studio/remotion.py`).
Free, local, in sync with the shots (each shot of the scene is a beat), re-rendered per language. Needs Node.js on
the owner's machine; packages install on first use. Use 4–8 per long video (case file, verdict, key numbers).
After writing one: `python -m studio images <slug> --only sNNN` (poster) and
`python -m studio motion-scenes <slug> --only sNNN` (clip → build/remotion_preview/) and **look at them**.
Changing a component: `npx tsc --noEmit` in `remotion/`, then `python -m pytest -q`.
**Channel rules** (`channel.yaml → remotion.scenes`, docs/REMOTION.md → Rules per channel; `studio/motion_rules.py`):
the cold open, case file and verdict are applied automatically after every plan (`motion-plan`, idempotent); the
data scenes (bars/counter/timeline/quote) come from the planner or `motion-prompt` and are rejected unless every
number is in a claim linked to the scene's shots (a quote must be a claim's quote). `motion-auto <slug>` does both.
When you plan a video by hand, leave the signature beats to the engine and add 2–6 data scenes from claims.yaml.
Never put the motion rules under `remotion.rules` (that name is the paper's ruled lines, `paper_rules`).

## Living pictures (motion inside the paintings)
Renders can animate the scene paintings locally and for free (`studio/motion.py`, `studio/stillmotion`;
docs/MOTION.md). Off by default; the owner turns it on with `video.motion: auto` (config.yaml, or one channel via
`channel.yaml → overrides.video.motion`). Without a plan a picture gets the channel preset (`video.motion_preset`:
`painterly` depth camera, `ledger` line boil). When asked to "make the pictures move" / "canlandır":
1. `python -m studio motion <slug>` and **look at `build/motion_sheet.png`** (pictures with a 0..1 grid).
2. Write `channels/<c>/projects/<slug>/motion.yaml` for the 30–50 % of scenes where something can believably move
   (docs/MOTION.md: rules, camera, effect table). Subtle; never distort faces, hands or anatomy.
3. `python -m studio motion-preview <slug> --only s0NN,...` and **look at `strip.png` and `motion.png`**
   (red = what moves) for each; adjust boxes/amounts. Then `render` (with `video.motion: auto`).

## Writing narration
- Structure (the script template shows it): hook in the first 8 s with the most surprising sourced fact, setup,
  evidence one study at a time, a turn ("but here is where the story gets complicated"), coach's lesson (60–90 s,
  safe advice).
- Every factual claim goes into `claims.yaml` (panel: İddialar) linked to a `library/sources.yaml` id and the shot
  ids that state it. Never invent a source, DOI or quote; never round a number into a claim the source does not make
  ("university women rowers", not "Olympic rowers"; "a group of Neolithic women", not "ancient humans").
- Delivery tags for the expressive voice (ElevenLabs `eleven_v3`): `[curious]`, `[excited]`, `[whispers]`, `[pause]`,
  `[serious]`, `[warm]` before the words in script.md, sparingly. `split` moves them to shot `tone` (captions never
  see them); other voices ignore them. Untagged questions get `tts.question_tag`.
- Short sentences, second-person hook. Use the idea bank (`ideas.yaml`: priority, signals, gut score) and avoid
  saturated titles.

## Sound
Every render layers an ambience bed per scene and effects on audible actions/words under the narration
(docs/SOUND.md, studio/sound/). It is automatic; override per shot with `sound:` only when it is wrong.
`python -m studio sound <slug>` shows the plan, `sounds-demo` plays every sound. Only licence-checked sounds
(built-in synthesis, CC0/CC-BY files in library/sounds/catalog.yaml) are ever used.

## Packaging and publishing
- `python -m studio thumbnails <slug>` renders project.yaml → `thumbnails`: three kinds, one each (`correction`,
  `stamp`, `scene`; docs/THUMBNAILS.md), look from `channel.yaml → thumbnails`, words printed by the factory (never in
  the AI picture or in shots), ≤3 words, numbers tied to a `claim`. Check `preview.png` (light/dark feed, 168 px).
  Titles/thumbnail concepts come from the package prompt (panel: Kapak & başlık), fed by `channel.yaml → package`.
- `publish:` in project.yaml is the publish record (series, hook_type, prediction, youtube_id, metrics).
- `describe` builds the YouTube description: hook paragraph, `channel.yaml → youtube.credit`, chapters, the sources
  cited in claims.yaml, `youtube.footer`. Never name the coach (owner's decision); the credit line says "an expert
  strength and conditioning coach".
- `python -m studio upload <slug> [VIDEO_ID|URL] [--at "YYYY-MM-DD HH:MM" | --at now]` publishes through the YouTube
  Data API (studio/youtube.py: one-time OAuth setup, `youtube-login`). Until `youtube.api_audited: true` Google
  locks API-uploaded files as private, so the owner drags video.mp4 into Studio as a draft and passes its link.
- Second languages are uploaded as an extra audio track on the same video: `python -m studio dub <slug> --lang tr`.

## Channel artwork and the channel bible
- `python -m studio branding --channel <c>` → `channels/<c>/build/branding/` (profile 800², banner 2560×1440 with
  text in the 1546×423 safe area, watermark 150²). Check `banner_guides.png`.
- `python -m studio knowledge --channel <c>` → `channels/<c>/build/knowledge.md`: identity, the channel's own script
  structure (`channel.yaml → package.script_structure`) and brand/persona book (`channels/<c>/BRAND.md`, or
  `brand_doc`), thumbnails, scene format, ideas, results, the sources it cites, a reference script. It is the
  channel's file in the claude.ai project "Video Fabrikası" (`kanallar/<c>/kanal-kitabi.md`); replace it after changes.

## Translating
`python -m studio translate <slug> --lang tr` writes a prompt; answer it as YAML `sNNN: "..."` (natural spoken
language, same shot boundaries, about the same spoken length ±10% because it must fit the primary timeline),
then `apply-translation <slug> <file> --lang tr`.

## Changing the look
- Style and characters: `channel.yaml → visual_style, characters`. A new character needs a reference sheet in
  `channels/<c>/refs/` (full body, front + three-quarter view, plain background, painted in the channel style).
- Charts: `studio/svgkit/props.py` and `props_charts.py` (values 0..1). After adding: update `docs/STORYBOARD.md`
  (Charts) and run `python -m pytest -q`.

## Updates on the owner's machine
He updates with `guncelle.bat` (`python -m studio update`): stashes local changes, fast-forwards, merges YAML value
by value (studio/merge3.py) and follows renamed folders. When you rename a channel, add the old id to `aliases`.
Keep idea ids stable (never renumber `ideas.yaml`).

## Never
- Commit `.env`, `models/`, `channels/*/projects/*/build/`, `backups/`, `.fabrika/` or music files.
- Drive web UIs (e.g. Google Flow, YouTube Studio) with browser automation; use official APIs only.
