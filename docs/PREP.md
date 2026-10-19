# Preparation studio (Hazırlık stüdyosu)

Everything a video needs before production, in one package (`prep.yaml`), written by the researcher-scriptwriter
(Claude) and checked by the factory (`studio/prep.py`). Panel: Kanal → **Hazırlık stüdyosu**.

## Who does what (lowest cost)
| who | what | cost |
| --- | --- | --- |
| Claude (claude.ai project "Video Fabrikası", or any chat with the prompt) | research with web search, sources, script in the channel's structure and voice, claims, titles, 3 thumbnail concepts, hooks, Shorts cuts, slot, policy self-check | subscription |
| Gemini | scene pictures, thumbnail pictures, scene plan (`planner.provider: gemini`) | ~0.05 $ per picture, plan ~0.01 $ |
| TTS | narration (channel's voice) | Gemini cheap; Kokoro/Edge free |
| Remotion | case file, verdict, number scenes | free, local |
| FFmpeg | edit, music, sound design, captions, Shorts | free, local |
| owner | reads the package, checks claims and pictures, watches the video, approves | — |

## Flow
1. **Topic**: pick an idea from the idea bank (or type a topic) → "Hazırlık istemini kopyala" → paste into Claude.
   The prompt carries the channel identity, series, script structure, brand book, thumbnail kinds, the YouTube
   policies (docs/POLICY.md), the videos already made (not to repeat them), the library ids and the next free slot.
   In the claude.ai project, "i011'i hazırla" is enough: the channel bible and `fabrika/hazirlik-paketi.md` carry the
   same rules.
2. **Check**: paste the answer → "Paketi incele". Errors (missing script/title/claims, unknown sources) stop the
   import; blocks (fewer than 3 sources, overclaims, policy blocks) need a fix or an explicit override. The sections
   (research, script, claims, packaging, Shorts, schedule, policy, raw YAML) can be edited in place.
3. **Import**: "Projeyi kur ve üretime gönder" creates the project (script, sources.md, claims → library, title and
   variants, thumbnails, description, chapters, hooks, planned date, idea status), splits it, links every claim to
   its shots (`says`) and every Short to a shot range (`from`/`to`), then runs `config.yaml → prep.after_import`
   (default: split → plan → motion-auto → check) as a background job.

Inbox: `channels/<c>/prep/*.yaml`. Claude writes there when the desktop app is linked to the factory folder; a
cloud session commits it and `guncelle.bat` brings it. Imported packages move to `prep/done/`.

## Package format
```yaml
prep: 1
channel: youre-wrong
idea: i011                     # or new_idea: {title, pillar, priority, angle, verdict}
title: "..."                   # chosen title (also in titles)
series: history-files
slot: long
planned_date: 2026-12-08
hook_type: contradiction
research: {question, answer, angle, competition, open_questions: []}
sources: [{id, title, authors, year, venue, doi, url, type, population, method, limits}]   # new ones only
script: |
  # Title
  <!-- chapter: The rumour -->
  ...
claims: [{id, text, source, says: "exact words of the script", quote, confidence, caveat, overclaim, on_screen}]
description: "two lines"
titles: [...]
thumbnails: [{kind: correction|stamp|scene, visual: {prompt, characters}, myth, note, text, pos, claim}]
hooks: [{type, text}]
shorts: [{title, hook, from: "first words", to: "last words"}]
policy: {originality, sensitive, advice_from: [], narrator_claims_expertise, realistic_ai_visuals, risks: []}
```
A minimal valid example: panel → "Biçim örneği" (`studio/prep.py → EXAMPLE`).

## Commands
```
python -m studio prep-prompt --channel C [--only i011 | --title "topic"]
python -m studio prep-check FILE --channel C
python -m studio prep-import FILE --channel C [--force]
python -m studio prep-run <slug> --channel C
python -m studio policy <slug> --channel C
```
