"""Channel bible: one file that teaches any chatbot (a Claude Project, ChatGPT, Gemini, DeepSeek) the channel.

  python -m studio knowledge [--channel C]   →  channels/<C>/build/knowledge.md

The stick-figure tutorials upload a fixed "source material" PDF to a chatbot so it knows the niche. This is the
same idea, built from the live files, so it never goes stale: identity and series, voice and structure rules,
delivery tags, the storyboard spec (drawing kit), idea bank with demand signals, what has been published and how it
performed, the source library, and one finished script as a reference for tone. Re-run it after publishing or
editing the brand, then replace the file in the chatbot's knowledge.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from .channel import Channel
from .config import ROOT, Config

WRITING_RULES = """- Narration in English, short sentences, second-person hook. Translations are shot-level (same boundaries,
  spoken length within ±10%).
- Structure: HOOK (0–8 s, the most surprising *sourced* fact or stake) → SETUP → EVIDENCE (one study at a time:
  who was measured, what was found) → TURN ("but here is where the story gets complicated": what the evidence
  cannot tell us) → COACH'S LESSON (60–90 s, safe, usable today). About 1,300–1,600 words ≈ 9–11 min.
- Every factual claim is linked to a source in the library and to the shot ids that say it. Never invent a source,
  DOI, number or quote. Never round a claim up: "university women rowers", not "Olympic rowers"; "a group of
  Neolithic women", not "ancient humans".
- Title, thumbnail and hook may not promise more than the claims support.
- Images never contain text; numbers become pictures (charts, gauges, two sizes). Text only on thumbnails and in
  the on-screen overlay layer."""

DELIVERY_TAGS = """Only with the expressive voice model (ElevenLabs `eleven_v3`); ignored by other voices and never shown in
captions. Put the tag before the words, at most one every few sentences:
`[curious]` questions that open a loop · `[excited]` the reveal · `[whispers]` a secret or aside ·
`[pause]` before a number · `[serious]` the turn · `[warm]` the coach's lesson.
Example: `[curious] So why can't a chimpanzee throw? [pause] The answer is in your shoulder.`
Questions without a tag automatically get `tts.question_tag` (default `curious`)."""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def _strip_title(md: str) -> str:
    lines = md.splitlines()
    return "\n".join(lines[1:]).strip() if lines and lines[0].startswith("# ") else md


def _demote(md: str, levels: int = 1) -> str:
    out, fence = [], False
    for ln in md.splitlines():
        if ln.lstrip().startswith("```"):
            fence = not fence
        out.append("#" * levels + ln if ln.startswith("#") and not fence else ln)
    return "\n".join(out)


def _ideas(ch: Channel) -> str:
    data = ch.load_ideas()
    pillars = data.get("pillars") or {}
    rows = []
    for pid, p in pillars.items():
        items = [i for i in data.get("ideas") or [] if i.get("pillar") == pid and i.get("status") != "dropped"]
        if not items:
            continue
        rows.append(f"\n**{pid} {p.get('name', '')}**: {p.get('promise', '')}\n")
        rows.append("| id | title | prio | status | demand/comp/gap | gut |\n| --- | --- | --- | --- | --- | --- |")
        for i in items:
            sg = i.get("signals") or {}
            dcg = "/".join(str(sg.get(k, "–")) for k in ("demand", "competition", "gap")) if sg else "–"
            title = str(i.get("title", "")).replace("|", "/")
            rows.append(f"| {i['id']} | {title} | {i.get('priority', '')} | {i.get('status', '')} | {dcg} | "
                        f"{i.get('gut', '') or ''} |")
    return "\n".join(rows) if rows else "(no ideas yet)"


def _projects(ch: Channel) -> tuple[str, str]:
    """(table of every project with its publish record and latest metrics, slug of the best reference script)."""
    from .project import Project
    rows = ["| video | status | series | hook | youtube | latest metrics |", "| --- | --- | --- | --- | --- | --- |"]
    ref, ref_rank = "", (-1, "")
    for slug in ch.project_slugs():
        p = Project(ch.id, slug)
        meta = p.meta
        pub = meta.get("publish") or {}
        m = (pub.get("metrics") or [{}])[-1]
        mtxt = ", ".join(f"{k} {m[k]}" for k in ("day", "views", "ctr", "avd_sec", "avg_pct", "subs") if k in m)
        rows.append(f"| {meta.get('title', slug)} | {meta.get('status', '')} | {pub.get('series', '')} | "
                    f"{pub.get('hook_type', '')} | {pub.get('youtube_id', '')} | {mtxt} |")
        words = len(_read(p.script_path).split())
        status = meta.get("status")
        rank = (3 if status == "published" else 2 if status == "production" else 1 if words >= 900 else 0, slug)
        if words >= 300 and rank > ref_rank:
            ref, ref_rank = slug, rank
    return "\n".join(rows), ref


def _sources() -> str:
    from .claims import load_library
    rows = []
    for s in load_library().get("sources") or []:
        bits = [s.get("authors", ""), str(s.get("year", "")), s.get("venue", "")]
        meta = ", ".join(b for b in bits if b)
        pop = f" Population: {s['population']}." if s.get("population") else ""
        lim = f" Limits: {s['limits']}." if s.get("limits") else ""
        rows.append(f"- `{s['id']}` ({s.get('type', '')}) {s.get('title', '')}. {meta}.{pop}{lim}")
    return "\n".join(rows) if rows else "(empty)"


def build_knowledge(channel: str, cfg: Config) -> str:
    ch = Channel(channel)
    d = ch.data
    chars = "; ".join(f"{k}: {' '.join(str((v or {}).get('description', '')).split())}"
                      for k, v in (d.get("characters") or {}).items()) or "none"
    series = "\n".join(f"| {s.get('name', sid)} | {', '.join(s.get('pillars') or [])} | {s.get('promise', '')} |"
                       for sid, s in (d.get("series") or {}).items())
    projects, ref = _projects(ch)
    ref_script = ""
    if ref:
        from .project import Project
        import re
        txt = re.sub(r"<!--[\s\S]*?-->", "", _read(Project(ch.id, ref).script_path)).strip()
        ref_script = f"From `{ref}`. Match this voice, rhythm and sourcing discipline, not its topic.\n\n```text\n{txt}\n```"
    brand = _demote(_strip_title(_read(ROOT / "docs" / "BRAND.md")), 1)
    storyboard = _demote(_strip_title(_read(ROOT / "docs" / "STORYBOARD.md")), 1)
    parts = [
        f"# {d.get('name', channel)}: channel bible",
        f"_Generated {date.today().isoformat()} by `python -m studio knowledge`. Upload this file as knowledge to "
        f"the chatbot you work with (Claude Project, ChatGPT, Gemini, DeepSeek) and replace it after each change._",
        "## How to use this file\n"
        "You are the writing and planning partner of this YouTube channel. Use it for: video ideas and angles, "
        "scripts, claim lists, scene plans, titles, thumbnails, Shorts, translations. When the Video "
        "Fabrikası panel gives you a prompt, the prompt's output format wins; this file gives you the context. The "
        "owner speaks Turkish; narration, plans and titles are written in English unless asked otherwise.",
        "## 1. Identity\n"
        f"- **Name:** {d.get('name', '')} ({d.get('pronunciation', '')}) · **Handle:** {d.get('handle', '')} · "
        f"**Category:** {d.get('category', '')}\n"
        f"- **Tagline:** {d.get('tagline', '')}\n"
        f"- **About:** {' '.join(str(d.get('description', '')).split())}\n"
        f"- **Languages:** {', '.join(d.get('languages') or [])} (first = primary; others are extra audio tracks)\n"
        f"- **Look:** {' '.join(str(d.get('visual_style', '')).split())}\n"
        f"- **Recurring characters:** {chars}",
        f"## 2. Series (playlists)\n| series | pillars | promise |\n| --- | --- | --- |\n{series}",
        f"## 3. Writing rules\n{WRITING_RULES}",
        f"## 4. Voice delivery tags\n{DELIVERY_TAGS}",
        f"## 5. Brand architecture (owner's notes, Turkish)\n{brand}",
        f"## 6. Drawing kit and storyboard format\n{storyboard}",
        f"## 7. Videos so far and how they performed\n{projects}",
        f"## 8. Idea bank (demand/competition/gap = YouTube signals 1–5)\n{_ideas(ch)}",
        f"## 9. Source library (cite by id; never invent new ones)\n{_sources()}",
    ]
    if ref_script:
        parts.append(f"## 10. Reference script\n{ref_script}")
    return "\n\n".join(p for p in parts if p) + "\n"


def write_knowledge(channel: str, cfg: Config) -> Path:
    out = Channel(channel).dir / "build" / "knowledge.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_knowledge(channel, cfg), encoding="utf-8")
    return out
