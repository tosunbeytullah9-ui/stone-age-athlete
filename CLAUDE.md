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

## Packaging and publishing
- `python -m studio thumbnails <slug>` renders project.yaml → `thumbnails` (≤3 variants; text allowed on thumbnails,
  never in shots). Titles/thumbnail concepts come from the package prompt (panel: Kapak & başlık).
- `publish:` in project.yaml is the publish record (series, hook_type, prediction, youtube_id, metrics).
- Second languages are uploaded as an extra audio track on the same video: `python -m studio dub <slug> --lang tr`.

## Channel artwork and the channel bible
- `python -m studio branding --channel <c>` → `channels/<c>/build/branding/` (profile 800², banner 2560×1440 with
  text in the 1546×423 safe area, watermark 150²). Check `banner_guides.png`.
- `python -m studio knowledge --channel <c>` → `channels/<c>/build/knowledge.md`: identity, rules, scene format,
  ideas, results, sources, a reference script. Upload it to the chatbot (Claude Project) after changes.

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
