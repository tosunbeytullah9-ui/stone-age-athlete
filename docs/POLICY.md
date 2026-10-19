# YouTube monetization policies in the factory

Every step from research to upload is checked against the rules that decide whether a channel can earn money
(`studio/policy.py`). The checks run in the preparation studio (before a package becomes a project), in the
quality gate (`check`, panel: Kalite kapısı) and before upload. `python -m studio policy <slug>` prints the report.

Researched 19 October 2026. Re-read the sources below when YouTube announces a change and update this file, the
checks and the project doc `fabrika/youtube-politikalari.md`.

## The rules and what the factory does

| YouTube rule | What it means for us | Factory check |
| --- | --- | --- |
| **Generic or repetitive content** (channel monetization policies; called "inauthentic content" from July 2025, reworded July 2026) | Every video needs its own storyline, research and insight. Recurring intros/outros, a recurring character and a series format are fine; templated storylines with the same outcome, slideshows and text read over pictures are not. Judged channel-wide. | `policy_original`: 6-word sequences shared with any other script of the channel (warn ≥ 12 %, block ≥ 25 %). `policy_outcome`: the last 5+ verdicts all identical → warn. The package must state its `research.angle`. |
| **Reused content** | No long readings of other people's texts, no clips from other creators, permission does not help. | `policy_quotes`: quotes over 40 words → warn. The factory never uses third-party footage. |
| **Unsatisfying or off-putting content** (July 2026) | A clear narrative arc and a payoff; no shock for its own sake, no emotionally manipulative formulas, no realistic fake disasters. | The channel's script structure; `policy_meta_shock` for titles/thumbnails. |
| **AI personas related to sensitive topics** (July 2026) | Channels whose AI-generated persona presents itself as a human expert giving health, finance or legal advice are not monetized ("an AI 'doctor' providing … health advice"). | `channel.yaml → policy.sensitive` (+ `sensitive_series`). In sensitive videos `policy_persona` blocks "as a doctor / as a coach / my patients / trust me"; `policy_advice` warns on cure/miracle/"you should take"; `policy_transparency` blocks when the description has no transparency line. |
| **Creator integrity** | Be who you say you are. | `policy.transparency` is printed in every description (`describe`). |
| **Medical misinformation** (Community Guidelines) | Health claims must not contradict health authorities; a myth is stated clearly as false and corrected (EDSA context). | `policy_health_sources`: a sensitive video needs a guideline, review or meta-analysis; `policy_overclaim` blocks a sentence that says more than its source. |
| **Advertiser-friendly guidelines** | Profanity, gore, graphic injury, shock in the title, thumbnail or first seconds limit ads; history violence is fine in an educational, non-graphic telling. | `policy_meta_language`, `policy_meta_shock`, `policy_opening`, `policy_language`. |
| **Spam & deceptive practices** | Titles/thumbnails may not promise what the video does not deliver; no mass uploads of near-identical videos. | `policy_meta_claims`: every number on the title/thumbnails must be in a claim. `policy_pace`: more than `max_long_per_week` long videos in a week → warn. |
| **Altered or synthetic content** ("AI use" on upload) | Disclose realistic AI content (could pass for a real person, place or event) and voices imitating real people. Not required for clearly illustrated/animated content or AI help with scripts and thumbnails. Since May 2026 YouTube auto-labels detected photorealistic AI. | `policy.realistic_visuals` / `real_person_voice` → `policy_ai_label` blocks when `youtube.synthetic_media` is false; `upload` sets `containsSyntheticMedia` itself when required. |
| **Made for kids** (COPPA) | Must be declared. | `policy_kids`: `youtube.made_for_kids` must be true/false. |
| **Music licences** | Only licensed music. | `policy_music`: `audio.music_licence` must name the licence when music is used. |

## The owner's review

The owner is the human control of every video: before `upload` the four steps in `project.yaml → review`
(panel: 5 · Yayın → Sahip onayı) must be ticked: claims checked against the sources, contact sheet checked, the
finished video watched, policy warnings read. `upload` refuses without them, even with `--force`. The record is also
the evidence of human creative work on each video.

## Channel settings

```yaml
policy:
  sensitive: [health]               # health | finance | legal | politics
  sensitive_series: [body-files]    # empty = every video
  narrator: fictional               # fictional | owner (the real expert's own voice)
  realistic_visuals: false
  real_person_voice: false
  transparency: "Mortimer is a fictional character with a synthetic voice ..."
```
Global thresholds: `config.yaml → policy` (`max_long_per_week`, `similarity_warn`, `similarity_block`,
`quote_words`).

## Sources
- YouTube channel monetization policies: https://support.google.com/youtube/answer/1311392
- Tubefilter, 13 July 2026, on the reworded policy: https://www.tubefilter.com/2026/07/13/youtube-inauthentic-content-monetization-policy-update/
- Advertiser-friendly content guidelines: https://support.google.com/youtube/answer/6162278
- Medical misinformation policy: https://support.google.com/youtube/answer/13813322
- Spam, deceptive practices & scams: https://support.google.com/youtube/answer/2801973
- Disclosing altered or synthetic content: https://support.google.com/youtube/answer/14328491
- YouTube blog, how creators disclose AI content: https://blog.youtube/news-and-events/disclosing-ai-generated-content
