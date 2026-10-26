"""Preparation studio (docs/PREP.md): everything a video needs before production, in one package.

A preparation package (`prep.yaml`) is what the researcher-scriptwriter (Claude, in the claude.ai project
"Video Fabrikası" or any chat with the prompt) hands to the factory: the research, new sources, the script in the
channel's structure, every claim (with the exact words of the script that state it), titles, three thumbnail
concepts, hooks, Shorts cut from the script, the publishing slot and a YouTube-policy self-check. The factory
checks it (structure + studio/policy.py), turns it into a project, splits the script, links claims and Shorts to
shot ids and runs the next steps (config.yaml → prep.after_import).

  python -m studio prep-prompt --channel C [--idea i011 | --topic "..."]   → the prompt for Claude
  python -m studio prep-check  <prep.yaml> --channel C                      → what is missing, policy report
  python -m studio prep-import <prep.yaml> --channel C                      → project + split + links
  python -m studio prep-run    <slug> --channel C                           → plan, motion scenes, gate

Inbox: channels/<C>/prep/*.yaml (Claude can write packages there when the Claude desktop app is linked to this
folder, or the cloud session commits them and `guncelle.bat` brings them); imported ones move to prep/done/.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .channel import Channel
from .config import Config, load_config
from .project import Project

FORMAT = 1
SHORT_WORDS = (60, 160)                 # a Short of 25–58 s at ~165 wpm


# ------------------------------------------------------------------ inbox
def inbox(cid: str) -> Path:
    return Channel(cid).dir / "prep"


def list_inbox(cid: str) -> list[dict]:
    out = []
    d = inbox(cid)
    for f in sorted(d.glob("*.yaml"), key=lambda x: x.stat().st_mtime, reverse=True) if d.exists() else []:
        try:
            data = parse(f.read_text(encoding="utf-8"))
        except Exception as e:                                  # noqa: BLE001
            out.append({"name": f.name, "title": f"(okunamadı: {e})", "idea": "", "mtime": f.stat().st_mtime})
            continue
        out.append({"name": f.name, "title": data.get("title", ""), "idea": _idea_ref(data),
                    "planned_date": str(data.get("planned_date") or ""), "mtime": f.stat().st_mtime})
    return out


def save_inbox(cid: str, text: str, name: str | None = None) -> str:
    data = parse(text)
    base = name or f"{date.today().isoformat()}-{_slug(data.get('title') or 'video')}.yaml"
    base = re.sub(r"[^\w.\-]", "-", Path(base).name)
    if not base.endswith(".yaml"):
        base += ".yaml"
    d = inbox(cid)
    d.mkdir(parents=True, exist_ok=True)
    (d / base).write_text(text.strip() + "\n", encoding="utf-8")
    return base


def read_inbox(cid: str, name: str) -> str:
    f = inbox(cid) / Path(name).name
    if not f.exists():
        raise FileNotFoundError(name)
    return f.read_text(encoding="utf-8")


def _done(cid: str, name: str | None) -> None:
    if not name:
        return
    f = inbox(cid) / Path(name).name
    if f.exists():
        (inbox(cid) / "done").mkdir(parents=True, exist_ok=True)
        f.replace(inbox(cid) / "done" / f.name)          # moved, never deleted


def _slug(t: str) -> str:
    from .channel import slugify
    return slugify(str(t))[:40].rstrip("-") or "video"


def _idea_ref(data: dict) -> str:
    if data.get("idea"):
        return str(data["idea"])
    return "yeni fikir" if isinstance(data.get("new_idea"), dict) else ""


# ------------------------------------------------------------------ parse
def parse(text: str) -> dict:
    """The package as YAML (a ```yaml fence around it is fine)."""
    from .planner import parse_yaml_reply
    data = parse_yaml_reply(text)
    if not isinstance(data.get("script"), str):
        raise ValueError("paket 'script' alanı içermiyor (senaryo metni)")
    return data


# ------------------------------------------------------------------ the prompt
PROMPT = """# Preparation package: one video for the YouTube channel "{name}"

You are the researcher, scriptwriter, fact-checker and packaging strategist of this channel. The owner is a strength
and conditioning coach who only reviews and approves; the factory (a local pipeline) turns your package into the
video: it paints the pictures (Gemini), voices the script (TTS), animates the case file / verdict / numbers
(Remotion) and edits it (FFmpeg). Your package must be complete, true and ready to paste.

## The video
{video}

## How to work (in this order)
1. **Research** with web search. Find the original studies, primary documents and current health-authority guidance
   (NHS, CDC, WHO, national bodies) behind the topic. Read them; note sample, method and limits. Never invent a source,
   DOI, number or quote; if you cannot verify something, leave it out or mark it `confidence: low` and list it under
   `research.open_questions`. Prefer primary studies, meta-analyses and reviews; news only as support.
2. **Originality.** Look at what the top YouTube videos on this topic already say. Write down what this video adds
   that they do not (`research.angle`): a source they skip, a mechanism, a better explanation, the channel's own
   analysis. A video that only repeats them must not be made (YouTube: generic or repetitive content).
3. **Script** in the channel's structure and voice (below). Short sentences, spoken English, numbers written as they
   are said ("eighteen twenty-one"). One idea per sentence; the body is this video's own argument, never a template.
   Put `<!-- chapter: Title -->` on its own line before the paragraph where each chapter starts (4–8 chapters, the
   first at the first paragraph). Comments are not read aloud.
4. **Claims.** Every factual statement (numbers, dates, study results, "researchers found") is a claim with its
   source and `says`: the exact words of the script that state it (copied, 3–12 words, unique in the script). If the
   script says more than the source supports, fix the script; never round a number up.
5. **Packaging:** 10 titles (≤ 60 characters, true to the claims), exactly 3 thumbnails (one of each of the channel's
   kinds below; the picture never contains text; at most 3 words; `claim:` for any number), 3 hooks,
   a 2-line description.
6. **Shorts:** 2 vertical cut-downs taken from the script itself: `from` = the first words, `to` = the last words of
   a passage of {short_min}–{short_max} words that works alone (a hook in its first line, a payoff at its end).
7. **Schedule:** use the planned slot below unless the topic belongs to another series day.
8. **Policy self-check** (YouTube monetization policies, below) and write it under `policy:`.

## Channel identity
{identity}

## Series (playlists)
{series}

## Script structure (follow it)
{structure}
Target length: {words}.
{signature}
## Voice and persona (brand book)
{brand}

## Delivery tags (optional, sparingly)
`[curious]` `[excited]` `[whispers]` `[pause]` `[serious]` `[warm]` before the words; they are not shown in captions.

## Thumbnails
Kinds of this channel (one of each):
{kinds_block}
`pos` = where the words go (top-left | top | top-right | left | right | bottom-left | bottom; never bottom-right).
Pictures in the channel's look:
{style}
{thumb_rules}
## YouTube monetization policies (the package must pass all of them)
{policy}

## Videos already made on this channel (do not repeat their stories, openings or jokes)
{made}

## Sources already in the shared library (reuse the id; add only new sources)
{library}

## Reply with ONLY this YAML (one code block), nothing else
```yaml
prep: 1
channel: {cid}
{idea_line}
title: "..."                         # the chosen title (also first in `titles`)
series: {series_id}
slot: long
planned_date: {planned}
hook_type: contradiction             # {hook_types}
research:
  question: "..."                    # the question the video answers
  answer: "..."                      # what the evidence says, 3–6 sentences
  angle: "..."                       # what this video adds that the top videos do not
  competition: "..."                 # what existing videos claim, in one or two sentences
  open_questions: []                 # anything the owner should double-check
sources:                             # only sources not yet in the library
  - {{id: smith2019, title: "...", authors: "Smith J, Lee K", year: 2019, venue: "...", doi: "10....",
      url: "https://...", type: primary, population: "...", method: "...", limits: "..."}}
script: |
  # {title_hint}
  <!-- chapter: ... -->
  First paragraph ...
claims:
  - {{id: c01, text: "...", source: smith2019, says: "exact words from the script", quote: "", confidence: high,
      caveat: "", overclaim: false, on_screen: false}}
description: "two lines for the top of the YouTube description, no hashtags"
titles: ["...", "..."]
thumbnails:
{kinds_yaml}
hooks:
  - {{type: cold_open_stat, text: "..."}}
shorts:
  - {{title: "...", hook: "...", from: "first words of the passage", to: "last words of the passage"}}
policy:
  originality: "..."                 # one sentence: why this is not a copy of anything
  sensitive: {sensitive}                  # health / finance / legal advice in this video?
  advice_from: []                    # source ids the practical advice rests on (health authority, review)
  narrator_claims_expertise: false
  realistic_ai_visuals: false
  risks: []                          # anything that could limit ads (violence, death, shock) and how it is handled
```
"""

POLICY_TEXT = """- **Generic or repetitive content** (not monetizable): each video must have its own storyline, research and
  insight; recurring intros, outros, a recurring character and a series format are fine. Never the same outcome by a
  template ("same story, new numbers"). No slideshows or text read over pictures without a narrative.
- **Reused content:** no long word-for-word readings of other people's texts (quotes ≤ {quote_words} words, with
  commentary); no clips from other creators.
- **Unsatisfying or off-putting content:** a clear narrative arc and a real payoff; no shock for its own sake, no
  emotionally manipulative formulas, no realistic fake disasters.
- **AI personas on sensitive topics:** {persona}
- **Medical misinformation:** health claims must agree with health authorities; a myth is stated clearly as false
  and corrected with the evidence; no remedies, no "cures", no personal medical advice; "talk to a professional"
  where the advice could matter.
- **Advertiser-friendly:** no profanity, gore, graphic injury or shock words in the title, thumbnail or the first
  seconds; violence and death in history are described soberly, in an educational context.
- **Misleading metadata:** the title and thumbnail promise only what the video delivers; every number on them is a
  claim.
- **Creator integrity:** the channel is honest about what it is; the description carries this line:
  "{transparency}"
- **AI label:** {ai_label}"""


def _brand(ch: Channel, d: dict) -> str:
    from .config import ROOT
    f = ROOT / d["brand_doc"] if d.get("brand_doc") else ch.dir / "BRAND.md"
    txt = f.read_text(encoding="utf-8").strip() if f.exists() else ""
    return txt or "(no brand book: write in the channel's tagline and positioning)"


def _made(ch: Channel) -> str:
    from .policy import verdict_of
    rows = []
    for slug in ch.project_slugs():
        p = Project(ch.id, slug)
        meta = p.meta
        script = p.script_path.read_text(encoding="utf-8") if p.script_path.exists() else ""
        from .splitter import paragraphs
        paras = paragraphs(script)
        first = paras[0][:160] if paras else ""
        v = verdict_of(script)
        rows.append(f"- {slug}: \"{meta.get('title', slug)}\"" + (f" · verdict {v}" if v else "")
                    + (f" · opens: {first}" if first else ""))
    return "\n".join(rows) or "(none yet)"


def next_slots(cid: str, n: int = 6, lead_days: int = 3) -> list[dict]:
    """Free calendar slots after the channel's last planned video (the queue stays in order) and at least
    `lead_days` from today (time to produce it)."""
    from datetime import timedelta

    from .publish import get_publish
    out: list[dict] = []
    last = date.today() + timedelta(days=lead_days - 1)
    for slug in Channel(cid).project_slugs():
        pub = Project(cid, slug).meta.get("publish") or {}   # no idea-bank lookup in a loop
        for k in ("planned_date", "published_at"):
            try:
                if pub.get(k):
                    last = max(last, date.fromisoformat(str(pub[k])))
            except ValueError:
                pass
    from .schedule import DAYS, DAYS_TR, settings
    st = settings(Channel(cid))
    types = dict(zip(st["days"], st["slot_types"] + ["long"] * 7))
    d = last + timedelta(days=1)
    while len(out) < n and (d - last).days < 120:
        day = DAYS[d.weekday()]
        if day in types:
            out.append({"date": d.isoformat(), "day": DAYS_TR[day], "type": types[day]})
        d += timedelta(days=1)
    return out


def build_prompt(cid: str, idea_id: str | None = None, topic: str | None = None, cfg: Config | None = None) -> str:
    from .claims import library_index
    from .policy import ai_label, settings
    from .publish import HOOK_TYPES
    cfg = cfg or load_config(cid)
    ch = Channel(cid)
    d = ch.data
    pkg = d.get("package") or {}
    ideas = ch.load_ideas()
    idea = next((i for i in ideas["ideas"] if i["id"] == idea_id), None) if idea_id else None
    pillars = ideas.get("pillars") or {}
    series = d.get("series") or {}
    series_id = ""
    if idea:
        series_id = next((k for k, s in series.items() if idea.get("pillar") in (s.get("pillars") or [])), "")
        video = (f"Idea {idea['id']}: \"{idea.get('title')}\"\nAngle from the idea bank: {idea.get('angle', '')}\n"
                 + (f"Expected verdict: {idea['verdict']}\n" if idea.get("verdict") else "")
                 + (f"Pillar: {idea.get('pillar')} ({(pillars.get(idea.get('pillar')) or {}).get('name', '')})\n"
                    if idea.get("pillar") else "")
                 + (f"Owner's notes: {idea['notes']}\n" if idea.get("notes") else "")
                 + ("Check the angle against the evidence: if the evidence says something else, the video says "
                    "what the evidence says." ))
        idea_line = f"idea: {idea['id']}"
    else:
        video = (f"Topic chosen by the owner: {topic or '(choose the strongest unmade idea that fits the channel)'}\n"
                 "It is not in the idea bank yet: fill `new_idea` so it is added.")
        idea_line = ("new_idea: {title: \"...\", pillar: " + (next(iter(pillars), "P1")) +
                     ", priority: B, angle: \"...\"}")
    slots = next_slots(cid)
    planned = slots[0]["date"] if slots else ""
    from .policy import is_sensitive
    pol = settings(cfg)
    sensitive = is_sensitive(pol, series_id or None)
    policy = policy_text(cfg, sensitive)
    return _fill(cid, cfg, ch, d, pkg, series, series_id, video, idea_line, idea, policy, sensitive, slots, lib=None)


def policy_text(cfg: Config, sensitive: bool = True) -> str:
    """The YouTube rules written for the scriptwriter (prompt and channel bible)."""
    from .policy import ai_label, settings
    pol = settings(cfg)
    persona = ("the narrator is a fictional character (or a synthetic voice) and must NEVER present itself as a human "
               "expert, doctor, coach or adviser, never say \"as a coach / as a doctor / my patients / trust me\". "
               "Practical advice is attributed to the evidence and to health authorities (\"the NHS recommends…\", "
               "\"in these trials…\"), stays general and safe, and ends with \"talk to a qualified professional\" "
               "where it matters. YouTube does not monetize AI personas that pose as experts on health, finance or "
               "legal topics." if sensitive else
               "the narrator never claims credentials it does not have.")
    need, why = ai_label(cfg, pol, lang="en")
    return POLICY_TEXT.format(quote_words=pol["quote_words"], persona=persona,
                              transparency=" ".join(str(pol.get("transparency") or "(not set)").split()),
                              ai_label=("required: " if need else "") + why)


def _fill(cid, cfg, ch, d, pkg, series, series_id, video, idea_line, idea, policy, sensitive, slots, lib=None) -> str:
    from .claims import library_index
    from .publish import HOOK_TYPES
    from .thumbnails import kinds_block, kinds_yaml
    planned = slots[0]["date"] if slots else ""
    words = "1,300–1,600 words (8–11 minutes)"
    m = re.search(r"(\d[\d,.]*)\s*[–-]\s*(\d[\d,.]*)\s*words", str(pkg.get("script_structure") or ""))
    if m:
        words = f"{m.group(1)}–{m.group(2)} words"
    rm = (d.get("remotion") or {}).get("scenes") or {}
    sig = []
    if rm.get("case_file"):
        sig.append("- Keep the case-file lines on their own sentences: \"Case file zero zero N.\" (N = the next case "
                   f"number, {ch.next_project_slug('x').split('-')[0].lstrip('0') or '1'}), \"Subject: …\", \"Belief: …\": the factory types them onto "
                   "the case-file card.")
    if rm.get("verdict"):
        sig.append("- The verdict is its own sentence: \"Verdict: wrong.\" (or \"Verdict: mostly wrong.\", "
                   "\"Verdict: annoyingly, correct.\"): the stamp lands on that word. Vary the verdict when the "
                   "evidence allows; not every case ends the same way.")
    if rm.get("cold_open"):
        sig.append("- If the first sentence states the belief itself (\"You need eight glasses of water a day.\"), "
                   "the factory opens with that belief struck through and stamped.")
    lib = library_index()
    identity = "\n".join(x for x in [
        f"Name: {d.get('name', cid)} — {d.get('tagline', '')}",
        " ".join(str(d.get("description") or "").split()),
        f"Positioning: {' '.join(str(pkg.get('positioning') or '').split())}" if pkg.get("positioning") else "",
        f"Languages: {', '.join(d.get('languages') or ['en'])} (write in the first one)",
        "Recurring characters: " + "; ".join(f"{k}: {' '.join(str((v or {}).get('description', '')).split())}"
                                             for k, v in (d.get("characters") or {}).items())
        if d.get("characters") else ""] if x)
    rules = pkg.get("thumbnail_rules") or []
    return PROMPT.format(
        name=d.get("name", cid), cid=cid, video=video, identity=identity,
        series="\n".join(f"- {k}: {s.get('name', '')} — {s.get('promise', '')}" for k, s in series.items()) or "-",
        structure=" ".join(str(pkg.get("script_structure") or "Hook (0–8 s) → setup → evidence → turn → ending")
                           .split()),
        words=words, signature=("\n".join(sig) + "\n") if sig else "", brand=_brand(ch, d),
        kinds_block=kinds_block(d), kinds_yaml=kinds_yaml(d), style=" ".join(str(d.get("visual_style") or "").split()),
        thumb_rules="".join(f"- {r}\n" for r in (rules if isinstance(rules, list) else [rules])),
        policy=policy, made=_made(ch),
        library="\n".join(f"- {k}: {v.get('authors', '')} {v.get('year', '')}, {v.get('title', '')}"
                          for k, v in lib.items()) or "(empty)",
        idea_line=idea_line, series_id=series_id or (next(iter(series), "") if series else ""),
        planned=planned or "YYYY-MM-DD", hook_types=" | ".join(HOOK_TYPES), short_min=SHORT_WORDS[0],
        short_max=SHORT_WORDS[1], sensitive=str(sensitive).lower(),
        title_hint=(idea or {}).get("title") or "Title")


# ------------------------------------------------------------------ locating script words in shots
def _w(t: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(t).lower())


def locate(shots: list[dict], phrase: str) -> tuple[int, int] | None:
    """(first shot index, last shot index) of the words `phrase` in the narration, or None."""
    words, owner = [], []
    for i, s in enumerate(shots):
        w = _w(s.get("text", ""))
        words += w
        owner += [i] * len(w)
    p = _w(phrase)
    if not p or not words:
        return None
    for size in (len(p), min(len(p), 8), min(len(p), 5)):     # exact, then the first words only
        q = p[:size]
        for k in range(len(words) - size + 1):
            if words[k:k + size] == q:
                end = k + len(p) - 1 if size == len(p) else k + size - 1
                return owner[k], owner[min(end, len(owner) - 1)]
    return None


def _in_script(script: str, phrase: str) -> bool:
    from .splitter import paragraphs, strip_tones
    body = " ".join(strip_tones(p)[0] for p in paragraphs(script))
    return locate([{"text": body}], phrase) is not None


def chapters_from_script(script: str) -> dict[int, str]:
    """`<!-- chapter: Title -->` before a paragraph → {paragraph index: title} (same counting as the splitter)."""
    from .splitter import paragraphs
    out: dict[int, str] = {}
    pending = None
    idx = 0
    for block in re.split(r"\n\s*\n", script.strip()):
        for m in re.finditer(r"<!--\s*chapter\s*:\s*(.+?)\s*-->", block, re.I):
            pending = m.group(1).strip()
        if paragraphs(block):
            if pending:
                out[idx] = pending
                pending = None
            idx += len(paragraphs(block))
    return out


def _words_between(script: str, a: str, b: str) -> int | None:
    from .splitter import paragraphs, strip_tones
    words = _w(" ".join(strip_tones(p)[0] for p in paragraphs(script)))
    pa, pb = _w(a), _w(b)
    if not pa or not pb:
        return None
    find = lambda q, start=0: next((k for k in range(start, len(words) - len(q) + 1) if words[k:k + len(q)] == q), None)
    i = find(pa)
    j = find(pb, i or 0) if i is not None else None
    return (j + len(pb) - i) if i is not None and j is not None else None


# ------------------------------------------------------------------ check
def check(cid: str, data: dict, cfg: Config | None = None) -> dict:
    """{ok, errors: [...], checks: [{key, ok, level, message, section}], summary}. Errors stop the import."""
    from .thumbkit import kinds_of
    from .claims import SOURCE_TYPES, library_index
    from .policy import channel_checks, is_sensitive, metadata_checks, pace_check, script_checks, settings
    cfg = cfg or load_config(cid)
    ch = Channel(cid)
    pol = settings(cfg)
    errors: list[str] = []
    checks: list[dict] = []

    def add(section, key, ok, level, message):
        checks.append({"section": section, "key": key, "ok": bool(ok), "level": level, "message": message})

    if data.get("channel") and str(data["channel"]) not in (cid, *ch.aliases):
        errors.append(f"Paket başka bir kanal için: {data['channel']}")
    script = str(data.get("script") or "")
    from .splitter import paragraphs
    paras = paragraphs(script)
    words = len(_w(" ".join(paras)))
    title = str(data.get("title") or "").strip()
    if not title:
        errors.append("title (başlık) yok")
    if words < 150:
        errors.append(f"Senaryo çok kısa: {words} kelime")
    ideas = {i["id"]: i for i in ch.load_ideas()["ideas"]}
    if data.get("idea") and str(data["idea"]) not in ideas:
        errors.append(f"Fikir havuzunda yok: {data['idea']}")
    if not data.get("idea") and not isinstance(data.get("new_idea"), dict):
        add("research", "idea", False, "warn", "Fikir bağlantısı yok (idea ya da new_idea): fikir havuzuna eklenecek")

    # research
    r = data.get("research") or {}
    add("research", "research", bool(r.get("answer")) and bool(r.get("angle")), "warn",
        "Araştırma özeti ve videonun farkı (angle) yazılmış" if r.get("answer") and r.get("angle")
        else "research.answer / research.angle eksik — videonun neyi farklı söylediği yazılmalı (özgünlük)")
    if r.get("open_questions"):
        add("research", "open_questions", False, "warn",
            f"Sahibin bakması gereken {len(r['open_questions'])} açık soru: {r['open_questions'][0]}")

    # sources and claims
    lib = library_index()
    new = {s.get("id"): s for s in data.get("sources") or [] if isinstance(s, dict) and s.get("id")}
    for sid, s in new.items():
        if not (s.get("url") or s.get("doi")):
            add("sources", f"src_{sid}", False, "warn", f"Kaynak {sid}: bağlantı/DOI yok")
        if s.get("type") and s["type"] not in SOURCE_TYPES:
            add("sources", f"src_{sid}", False, "warn", f"Kaynak {sid}: bilinmeyen tür {s['type']}")
    claims = [c for c in data.get("claims") or [] if isinstance(c, dict) and c.get("text")]
    if not claims:
        errors.append("claims (iddialar) yok")
    known = set(lib) | set(new)
    unknown = sorted({str(c.get("source")) for c in claims if c.get("source") and c["source"] not in known})
    if unknown:
        errors.append(f"İddiaların kaynağı ne pakette ne kütüphanede: {', '.join(unknown)}")
    cited = {c.get("source") for c in claims if c.get("source") in known}
    add("sources", "sources_count", len(cited) >= 3, "block", f"Farklı kaynak: {len(cited)} (en az 3)")
    nosrc = [c.get("id", "?") for c in claims if not c.get("source")]
    if nosrc:
        add("sources", "claims_nosource", False, "warn", f"Kaynaksız iddia: {', '.join(nosrc[:6])} — senaryodan çıkar ya da kaynak bul")
    notfound = [c.get("id", "?") for c in claims if not c.get("says") or not _in_script(script, str(c.get("says")))]
    add("sources", "claims_says", not notfound, "warn", "Her iddianın cümlesi senaryoda bulundu" if not notfound
        else f"Senaryoda bulunamayan iddia cümlesi (says): {', '.join(notfound[:8])} — shot'a bağlanamaz")
    over = [c.get("id", "?") for c in claims if c.get("overclaim")]
    if over:
        add("sources", "overclaim", False, "block", f"Kaynaktan fazlasını söyleyen iddia: {', '.join(over)} — senaryoyu düzelt")

    # script
    m = re.search(r"(\d[\d,.]*)\s*[–-]\s*(\d[\d,.]*)\s*words", str((ch.data.get("package") or {}).get("script_structure") or ""))
    lo, hi = (int(m.group(1).replace(",", "").replace(".", "")), int(m.group(2).replace(",", "").replace(".", ""))) if m else (1100, 1800)
    add("script", "length", lo * 0.85 <= words <= hi * 1.15, "warn",
        f"Uzunluk: {words} kelime ≈ {words / 160:.1f} dk (kanal hedefi {lo}–{hi})")
    chaps = chapters_from_script(script)
    add("script", "chapters", len(chaps) >= 3 and 0 in chaps, "warn", f"Bölüm: {len(chaps)}"
        + ("" if len(chaps) >= 3 and 0 in chaps else " — en az 3 ve ilki ilk paragrafta (<!-- chapter: … -->)"))
    rm = (ch.data.get("remotion") or {}).get("scenes") or {}
    if rm.get("case_file"):
        ok = re.search(r"case file\b", script, re.I) and re.search(r"subject\s*:", script, re.I)
        add("script", "case_file", bool(ok), "warn", "Dosya kartı cümleleri var (Case file … Subject: …)" if ok
            else "Kanalın dosya kartı cümleleri yok: \"Case file zero zero N.\" ve \"Subject: …\"")
    if rm.get("verdict"):
        ok = re.search(r"verdict\s*:", script, re.I)
        add("script", "verdict", bool(ok), "warn", "Hüküm cümlesi var (Verdict: …)" if ok else "\"Verdict: …\" cümlesi yok")

    # packaging
    titles = [str(t) for t in data.get("titles") or []]
    if title and title not in titles:
        titles = [title, *titles]
    long_t = [t for t in titles if len(t) > 60]
    add("package", "titles", len(titles) >= 3 and not long_t, "warn", f"Başlık adayı: {len(titles)}"
        + (f" · 60 karakteri aşan: {len(long_t)}" if long_t else ""))
    th = [t for t in data.get("thumbnails") or [] if isinstance(t, dict)]
    kinds = sorted(t.get("kind", "?") for t in th)
    want = sorted(kinds_of(ch.data if ch else {}))
    add("package", "thumbnails", kinds == want, "warn",
        f"Kapak: {len(th)} ({', '.join(kinds) or '—'})" + ("" if kinds == want
                                                          else f" — kanalın her türünden bir tane gerekli ({', '.join(want)})"))
    ids = {c.get("id") for c in claims}
    loose = [t.get("kind") for t in th if t.get("claim") and t["claim"] not in ids]
    if loose:
        add("package", "thumb_claim", False, "warn", f"Kapağın dayandığı iddia pakette yok: {', '.join(loose)}")
    if not str(data.get("description") or "").strip():
        add("package", "description", False, "warn", "Açıklamanın ilk satırları (description) yok")

    # shorts
    shorts = [s for s in data.get("shorts") or [] if isinstance(s, dict)]
    for i, s in enumerate(shorts, 1):
        n = _words_between(script, str(s.get("from", "")), str(s.get("to", "")))
        ok = n is not None and SHORT_WORDS[0] <= n <= SHORT_WORDS[1]
        add("shorts", f"short{i}", ok, "warn", f"Short {i} «{s.get('title', '')}»: "
            + ("başlangıç/bitiş cümlesi senaryoda bulunamadı" if n is None else f"{n} kelime ≈ {n / 2.75:.0f} sn")
            + ("" if ok or n is None else f" (hedef {SHORT_WORDS[0]}–{SHORT_WORDS[1]} kelime)"))
    if not shorts:
        add("shorts", "shorts", False, "warn", "Shorts yok (shorts: [{title, hook, from, to}])")

    # schedule
    planned = str(data.get("planned_date") or "")
    if planned:
        taken = []
        from .publish import get_publish
        for slug in ch.project_slugs():
            pub = Project(cid, slug).meta.get("publish") or {}   # no idea-bank lookup in a loop
            if str(pub.get("planned_date") or "") == planned:
                taken.append(slug)
        add("schedule", "slot", not taken, "warn", f"Yayın günü {planned}" + (f" — dolu: {taken[0]}" if taken else ""))
        pc = pace_check(cid, planned, str(data.get("slot") or "long"), pol)
        if pc:
            checks.append({"section": "schedule", **pc})
    else:
        add("schedule", "slot", False, "warn", "Yayın günü (planned_date) yok — takvimde boş güne yerleştir")

    # policy
    sensitive = is_sensitive(pol, data.get("series"))
    for c in script_checks(cid, script, pol, sensitive):
        checks.append({"section": "policy", **c})
    claim_text = " ".join(str(c.get("text", "")) for c in claims)
    from .policy import thumb_words
    for c in metadata_checks(titles[:1], thumb_words({"thumbnails": th}), claim_text):
        checks.append({"section": "policy", **c})
    if sensitive:
        strong = [c for c in claims if ((new.get(c.get("source")) or lib.get(c.get("source")) or {}).get("type")
                                        in ("guideline", "review", "meta-analysis"))]
        add("policy", "policy_health_sources", bool(strong), "warn",
            f"Sağlık konusu: {len(strong)} iddia kılavuz/derleme/meta-analize dayanıyor" if strong else
            "Sağlık konusu ama kılavuz/derleme/meta-analiz yok — sağlık otoritesinin görüşü eklenmeli")
    self_ = data.get("policy") or {}
    if self_.get("narrator_claims_expertise"):
        add("policy", "self_persona", False, "block", "Paket anlatıcının uzmanlık iddia ettiğini söylüyor")
    if self_.get("realistic_ai_visuals") and not cfg.get_path("channel.youtube.synthetic_media"):
        add("policy", "self_ai", False, "block", "Gerçekçi AI görüntü var: youtube.synthetic_media: true olmalı")
    for c in channel_checks(cfg, pol, sensitive):
        checks.append({"section": "policy", **c})

    blocks = [c for c in checks if c["level"] == "block" and not c["ok"]]
    summary = {"title": title, "words": words, "minutes": round(words / 160, 1), "claims": len(claims),
               "new_sources": len(new), "chapters": len(chaps), "shorts": len(shorts), "titles": len(titles),
               "thumbnails": len(th), "planned_date": planned, "series": data.get("series", ""),
               "sensitive": sensitive}
    return {"ok": not errors and not blocks, "importable": not errors, "errors": errors, "checks": checks,
            "summary": summary}


# ------------------------------------------------------------------ import
def import_bundle(cid: str, data: dict, cfg: Config | None = None, name: str | None = None,
                  force: bool = False) -> Project:
    """Package → project (script, sources, claims, packaging, schedule), split into shots, claims and Shorts
    linked to shot ids. Policy blocks stop the import unless force=True (errors always stop it)."""
    from .claims import apply_reply
    from .publish import save_publish
    from .storyboard import build_storyboard
    cfg = cfg or load_config(cid)
    rep = check(cid, data, cfg)
    if rep["errors"]:
        raise ValueError("Paket içe aktarılamaz: " + "; ".join(rep["errors"]))
    if not rep["ok"] and not force:
        bad = [c["message"] for c in rep["checks"] if c["level"] == "block" and not c["ok"]]
        raise ValueError("Paket engel taşıyor (düzelt ya da bilerek zorla): " + "; ".join(bad))
    ch = Channel(cid)
    ideas = ch.load_ideas()
    idea_id = str(data.get("idea") or "")
    if not idea_id and isinstance(data.get("new_idea"), dict):
        nums = [int(i["id"][1:]) for i in ideas["ideas"] if str(i.get("id", "")).startswith("i") and i["id"][1:].isdigit()]
        ni = data["new_idea"]
        idea_id = f"i{(max(nums) + 1) if nums else 1:03d}"
        ideas["ideas"].append({"id": idea_id, "title": str(ni.get("title") or data.get("title")),
                               "pillar": ni.get("pillar", ""), "priority": ni.get("priority", "B"),
                               "angle": ni.get("angle", ""), "status": "idea",
                               **({"verdict": ni["verdict"]} if ni.get("verdict") else {})})
    from .project import create_project
    title = str(data["title"]).strip()
    p = create_project(cid, title, idea_id=idea_id or None)
    script = str(data["script"]).strip() + "\n"
    p.script_path.write_text(script, encoding="utf-8")
    r = data.get("research") or {}
    notes = [f"# Sources — {title}", "<!-- From the preparation package (prep.yaml). Claims are in claims.yaml. -->", ""]
    for k, lab in (("question", "Question"), ("answer", "What the evidence says"), ("angle", "This video's angle"),
                   ("competition", "What other videos say")):
        if r.get(k):
            notes += [f"**{lab}:** {' '.join(str(r[k]).split())}", ""]
    if r.get("open_questions"):
        notes += ["**Open questions (check before publishing):**", *[f"- {q}" for q in r["open_questions"]], ""]
    for s in data.get("sources") or []:
        if isinstance(s, dict):
            href = s.get("url") or (f"https://doi.org/{s['doi']}" if s.get("doi") else "")
            notes.append(f"- {s.get('authors', '')} {s.get('year', '')}. {s.get('title', s.get('id'))}. {href}".strip())
    p.sources_path.write_text("\n".join(notes).strip() + "\n", encoding="utf-8")
    claims = [{k: v for k, v in c.items()} for c in data.get("claims") or [] if isinstance(c, dict)]
    apply_reply(p, {"sources": data.get("sources") or [], "claims": claims})

    meta = p.meta
    meta["status"] = "scripting"
    if data.get("description"):
        meta["description"] = " ".join(str(data["description"]).split())
    ch_ = chapters_from_script(script)
    if ch_:
        meta["chapters"] = ch_
    th = [t for t in data.get("thumbnails") or [] if isinstance(t, dict)][:3]
    if th:
        meta["thumbnails"] = th
    meta["prep"] = {"imported": date.today().isoformat(), "file": name or "",
                    **({"research": r} if r else {}),
                    **({"policy": data["policy"]} if data.get("policy") else {}),
                    **({"shorts_plan": data["shorts"]} if data.get("shorts") else {})}
    p.save_meta(meta)
    titles = [str(t) for t in data.get("titles") or []]
    if title not in titles:
        titles = [title, *titles]
    save_publish(p, {"series": data.get("series") or "", "slot": data.get("slot") or "long",
                     "hook_type": data.get("hook_type") or "", "planned_date": str(data.get("planned_date") or ""),
                     "title_used": title, "title_variants": titles[:12],
                     **({"hook_options": data["hooks"][:5]} if isinstance(data.get("hooks"), list) else {})})
    for i in ideas["ideas"]:
        if i["id"] == idea_id:
            i["status"], i["project"] = "scripting", p.slug
    ch.save_ideas(ideas)
    build_storyboard(p, cfg)
    link(p)
    _done(cid, name)
    return p


def link(p: Project) -> dict:
    """Claims → shot ids (from `says`) and Shorts → shot ranges (from `from` / `to`), after every split."""
    from .claims import load_claims, save_claims
    shots = p.load_storyboard()["shots"]
    data = load_claims(p)
    n_c = 0
    for c in data["claims"]:
        if c.get("says"):
            hit = locate(shots, str(c["says"]))
            if hit:
                c["shots"] = [s["id"] for s in shots[hit[0]: hit[1] + 1]]
                n_c += 1
    save_claims(p, data)
    meta = p.meta
    plan = (meta.get("prep") or {}).get("shorts_plan") or []
    cuts = []
    for s in plan:
        a, b = locate(shots, str(s.get("from", ""))), locate(shots, str(s.get("to", "")))
        if a and b and b[1] >= a[0]:
            cut = {"title": s.get("title", ""), "from": shots[a[0]]["id"], "to": shots[b[1]]["id"]}
            if s.get("hook"):
                cut["hook"] = s["hook"]
            cuts.append(cut)
    if cuts:
        meta["shorts"] = cuts
        p.save_meta(meta)
    return {"claims": n_c, "shorts": len(cuts)}


def run_after(p: Project, cfg: Config) -> list[str]:
    """config.yaml → prep.after_import: split, plan, motion-auto, check (each step prints what it did)."""
    from .readiness import check as gate
    steps = cfg.get_path("prep.after_import") or ["split", "plan", "motion-auto", "check"]
    out = []
    for st in steps:
        try:
            out += _step(p, cfg, st, gate)
        except SystemExit as e:                     # e.g. no API key: report it, go on with the free steps
            out.append(f"{st}: atlandı — {str(e).strip().splitlines()[0] if str(e).strip() else 'durdu'}")
    return out


def _step(p: Project, cfg: Config, st: str, gate) -> list[str]:
    out: list[str] = []
    if st == "split":
        from .storyboard import build_storyboard
        build_storyboard(p, cfg)
        r = link(p)
        out.append(f"bölündü: {len(p.load_storyboard()['shots'])} shot · {r['claims']} iddia ve {r['shorts']} Short bağlandı")
    elif st == "plan":
        if cfg.get_path("planner.provider", "gemini") == "manual":
            out.append("plan: planlayıcı 'manual' — 2 · Sahneler → 'Plan istemini kopyala' ile Claude'a planlat")
            return out
        from .planner import plan
        plan(p, cfg)
        out.append("plan: resimler planlandı")
    elif st == "motion-auto":
        from .motion_rules import apply_signature, data_scenes, rules_for, run_data
        if not rules_for(cfg, p):
            return out
        out += [f"hareketli: {ln}" for ln in apply_signature(p, cfg)]
        d = rules_for(cfg, p).get("data") or {}
        if len(data_scenes(p.load_storyboard()["shots"])) < d.get("min", 2):
            out.append("hareketli: " + run_data(p, cfg))
    elif st == "check":
        r = gate(p)
        blocks = [c["message"] for c in r["checks"] if c["level"] == "block" and not c["ok"]]
        out.append("kalite kapısı: " + ("HAZIR" if r["ready"] else f"{len(blocks)} engel — {blocks[0]}"))
    return out


def dump(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110)


def example() -> dict[str, Any]:
    """A tiny valid package (tests and the panel's 'örnek' button)."""
    return yaml.safe_load(EXAMPLE)


EXAMPLE = """prep: 1
channel: demo
title: "Your Shoulder Is a Catapult"
series: ""
slot: long
planned_date: ""
hook_type: contradiction
research:
  question: "Why can humans throw so much faster than chimpanzees?"
  answer: "Roach and colleagues (2013) filmed baseball pitchers and found the shoulder stores elastic energy before
    release. Chimpanzees are stronger but cannot store energy this way."
  angle: "Explains the elastic-energy mechanism with the original motion-capture study instead of 'humans are just strong'."
  competition: "Most videos say humans throw well because of practice."
  open_questions: []
sources:
  - {id: roach2013, title: "Elastic energy storage in the shoulder and the evolution of high-speed throwing in Homo",
     authors: "Roach NT, Venkadesan M, Rainbow MJ, Lieberman DE", year: 2013, venue: Nature,
     doi: "10.1038/nature12267", url: "https://www.nature.com/articles/nature12267", type: primary}
script: |
  # Your Shoulder Is a Catapult
  <!-- chapter: The throw -->
  A twelve-year-old can throw a ball faster than any chimpanzee alive. That sounds wrong. Chimpanzees are far
  stronger than we are. So where does the speed come from?

  <!-- chapter: The study -->
  In two thousand thirteen, a team at Harvard filmed twenty baseball players with motion capture. They measured how
  the shoulder moves in the moment before the ball leaves the hand. The arm twists backwards, like a spring being
  wound. Then it snaps forward.

  <!-- chapter: The spring -->
  The tendons and ligaments around the shoulder store that energy and release it all at once. The researchers call
  it a catapult. Muscles alone could never move the arm that fast. Chimpanzees lack the low, wide shoulder that
  makes this possible, so their throws stay slow, however strong they are.

  So the next time you throw, remember: the speed is not only in your muscles. It is in your shape, a design that is
  about two million years old. Train the whole chain, from the legs through the hips to the shoulder, and talk to a
  qualified coach before you add heavy throwing to your week.
claims:
  - {id: c01, text: "Roach et al. 2013 filmed 20 baseball players with motion capture", source: roach2013,
     says: "filmed twenty baseball players with motion capture", confidence: high}
  - {id: c02, text: "The shoulder stores elastic energy before the release (catapult)", source: roach2013,
     says: "store that energy and release it all at once", confidence: high}
  - {id: c03, text: "The throwing shoulder design is about two million years old", source: roach2013,
     says: "about two million years old", confidence: medium}
description: "Why a child out-throws a chimpanzee: the elastic catapult in your shoulder."
titles: ["Your Shoulder Is a Catapult", "Why a Kid Out-Throws a Chimp"]
thumbnails:
  - {kind: correction, visual: {prompt: "a flexed arm", characters: []}, myth: {en: "MUSCLE"}, note: {en: "a spring?"}, pos: top-left}
  - {kind: stamp, visual: {prompt: "a baseball in flight", characters: []}, pos: top-left}
  - {kind: scene, visual: {prompt: "a child throwing past a chimpanzee", characters: []}, text: {en: "CATAPULT"}, pos: top}
hooks:
  - {type: contradiction, text: "A twelve-year-old can throw faster than any chimpanzee alive."}
shorts:
  - {title: "Your shoulder is a catapult", hook: "Why kids out-throw chimps",
     from: "The tendons and ligaments around the shoulder", to: "about two million years old"}
policy:
  originality: "Built on the original motion-capture study."
  sensitive: true
  advice_from: [roach2013]
  narrator_claims_expertise: false
  realistic_ai_visuals: false
  risks: []
"""
