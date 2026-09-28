"""Claims and the shared source library.

library/sources.yaml           every study/article used by any video of any channel (one entry per source)
<project>/claims.yaml          every factual claim in the script: which source, exact wording, which shots say it

A claim links the narration to evidence:
  - {id: c01, text: "Bajau spleens are ~50% larger than Saluan spleens", source: ilardo2018,
     quote: "exact words from the paper or article", shots: [s021, s022], confidence: high,
     caveat: "59 Bajau vs 34 Saluan, one community", verified: true, on_screen: false}

Only sources cited by claims go into the YouTube description. The quality gate blocks unknown sources and
fewer than 3 distinct sources, and warns about unverified claims and numbers the script states without a claim.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

import yaml

from .config import ROOT
from .project import Project

LIBRARY = ROOT / "library" / "sources.yaml"
SOURCE_TYPES = ["meta-analysis", "review", "primary", "dataset", "book", "guideline", "news", "other"]
LIB_HEADER = """# Shared source library — every channel and every video cites sources from here by id.
# id: short and stable (firstauthorYEAR, e.g. ilardo2018). Never change an id that a claims.yaml uses.
# type: meta-analysis | review | primary | dataset | book | guideline | news | other  (prefer primary/review)
# population / method / limits: what the study can and cannot tell us — used for caveats in scripts.
# link: filled by "Bağlantıları kontrol et" (python -m studio check-links)
"""

NUMBER_WORDS = re.compile(
    r"\d|\b(percent|per cent|half|twice|thrice|double|triple|dozen|hundred|thousand|million|billion|"
    r"two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\b", re.I)


# ------------------------------------------------------------------ storage
def load_library() -> dict[str, Any]:
    if not LIBRARY.exists():
        return {"sources": []}
    data = yaml.safe_load(LIBRARY.read_text(encoding="utf-8")) or {}
    data.setdefault("sources", [])
    return data


def save_library(data: dict[str, Any]) -> None:
    from .channel import _flow
    LIBRARY.parent.mkdir(parents=True, exist_ok=True)
    lines = [LIB_HEADER.rstrip(), "sources:"]
    for s in data.get("sources", []):
        lines.append(f"- {_flow(s)}")
    LIBRARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def library_index() -> dict[str, dict]:
    return {s["id"]: s for s in load_library()["sources"] if isinstance(s, dict) and s.get("id")}


def claims_path(project: Project):
    return project.dir / "claims.yaml"


def load_claims(project: Project) -> dict[str, Any]:
    p = claims_path(project)
    if not p.exists():
        return {"claims": []}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    data.setdefault("claims", [])
    return data


def save_claims(project: Project, data: dict[str, Any]) -> None:
    from .channel import _flow
    lines = ["# Claims in this video → shared library (library/sources.yaml). Set verified: true after you have",
             "# checked the quote against the source yourself. Panel: 1 · Senaryo & kaynaklar → İddialar.",
             "claims:"]
    for c in data.get("claims", []):
        lines.append(f"- {_flow(c)}")
    claims_path(project).write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ prompt / apply
PROMPT = """You are the fact-checker of a science-history YouTube channel. Below is a video script split into shots
(ids in brackets), the owner's notes on sources, and the ids already in the shared source library.

Task: list EVERY factual claim in the script (numbers, dates, study results, historical facts, "scientists
found..."). For each claim give the source that supports it. Reuse a library id when the source is already there;
otherwise add the source under `sources:` (only new ones). Prefer the original study (DOI or PubMed link) over press
releases. Never invent a source, DOI or quote: if you cannot name a real source, set source: null and
confidence: low — the owner will research it. `quote` = the source's own words that support the claim, only if
you are sure of them (otherwise leave it empty). `caveat` = what the evidence does NOT show (sample, population,
proxy measure, estimate) when the script could be misunderstood. If the script says more than the source supports,
set overclaim: true and put a safer wording in `suggest`.

Reply with ONLY this YAML:

sources:
  - {{id: ilardo2018, title: "...", authors: "Ilardo MA et al.", year: 2018, venue: Cell, doi: "10.1016/...",
      url: "https://...", type: primary, population: "...", method: "...", limits: "..."}}
claims:
  - {{id: c01, text: "...", source: ilardo2018, quote: "", shots: [s021, s022], confidence: high,
      caveat: "", overclaim: false, suggest: ""}}

Source types: {types}

## Library ids already available
{library}

## Owner's source notes (sources.md)
{notes}

## Script by shot
{script}
"""


def build_prompt(project: Project) -> str:
    lib = library_index()
    lib_lines = "\n".join(f"- {k}: {v.get('authors', '')} {v.get('year', '')}, {v.get('title', '')}"
                          for k, v in lib.items()) or "(empty)"
    notes = project.sources_path.read_text(encoding="utf-8") if project.sources_path.exists() else ""
    if project.storyboard_path.exists():
        shots = project.load_storyboard().get("shots", [])
        script = "\n".join(f"[{s['id']}] {s['text']}" for s in shots)
    else:
        script = project.script_path.read_text(encoding="utf-8") + "\n\n(no shot ids yet: run 'Böl' first, or leave shots empty)"
    return PROMPT.format(types=", ".join(SOURCE_TYPES), library=lib_lines, notes=notes.strip() or "(none)",
                         script=script)


def apply_reply(project: Project, data: dict) -> dict:
    """Adds new sources to the library (existing ids are never overwritten) and writes claims.yaml.
    Existing claims keep their `verified` flag when their text is unchanged."""
    lib = load_library()
    have = {s["id"] for s in lib["sources"] if isinstance(s, dict)}
    added = 0
    for s in data.get("sources") or []:
        if isinstance(s, dict) and s.get("id") and s["id"] not in have:
            s = {k: v for k, v in s.items() if v not in (None, "")}
            s.setdefault("added", date.today().isoformat())
            lib["sources"].append(s)
            have.add(s["id"])
            added += 1
    if added:
        save_library(lib)
    old = {c.get("text"): c for c in load_claims(project)["claims"]}
    claims = []
    for i, c in enumerate(data.get("claims") or [], 1):
        if not isinstance(c, dict) or not c.get("text"):
            continue
        c = {k: v for k, v in c.items() if v not in (None, "", [], False) or k == "source"}
        c.setdefault("id", f"c{i:02d}")
        c["verified"] = bool(old.get(c["text"], {}).get("verified"))
        claims.append(c)
    save_claims(project, {"claims": claims})
    return {"sources_added": added, "claims": len(claims)}


# ------------------------------------------------------------------ checks
def claim_checks(project: Project) -> list[dict]:
    """Readiness checks; each {key, ok, level, message}."""
    out: list[dict] = []

    def add(key, ok, level, message):
        out.append({"key": key, "ok": bool(ok), "level": level, "message": message})

    claims = load_claims(project)["claims"]
    lib = library_index()
    if not claims:
        add("claims", False, "warn", "İddia kaydı yok: 'İddia istemini kopyala' ile claims.yaml oluştur")
        return out
    missing = sorted({c.get("source") or "—" for c in claims if c.get("source") not in lib})
    add("claims_sources", not missing, "block",
        f"İddialar: {len(claims)} · kütüphanede olmayan kaynak: {', '.join(missing)}" if missing
        else f"İddialar: {len(claims)}, hepsi kütüphanedeki bir kaynağa bağlı")
    cited = {c.get("source") for c in claims if c.get("source") in lib}
    add("claims_count", len(cited) >= 3, "block", f"Farklı kaynak: {len(cited)} (en az 3)")
    primary = [s for s in cited if lib[s].get("type") in ("primary", "review", "meta-analysis", "dataset", "book")]
    add("claims_primary", bool(primary), "warn",
        f"Birincil/derleme kaynak: {len(primary)}" + ("" if primary else " — sadece haber kaynağı var"))
    unverified = [c.get("id", "?") for c in claims if not c.get("verified")]
    add("claims_verified", not unverified, "warn",
        f"Doğrulanmamış iddia: {len(unverified)} ({', '.join(unverified[:8])})" if unverified
        else "Tüm iddiaları kaynağıyla karşılaştırdın")
    over = [c.get("id", "?") for c in claims if c.get("overclaim")]
    if over:
        add("claims_overclaim", False, "warn", f"Kaynağın söylediğinden fazlasını söyleyen cümle: {', '.join(over)}")
    if project.storyboard_path.exists():
        shots = project.load_storyboard().get("shots", [])
        covered = {sid for c in claims for sid in c.get("shots") or []}
        numeric = [s["id"] for s in shots if NUMBER_WORDS.search(s["text"]) and s["id"] not in covered]
        add("claims_numbers", not numeric, "warn",
            "Sayı içeren her cümle bir iddiaya bağlı" if not numeric
            else f"Sayı içeren ama iddiaya bağlanmamış shot: {', '.join(numeric[:10])}")
    return out


def cited_sources(project: Project) -> list[dict]:
    """Library entries cited by this project's claims, in first-cited order."""
    lib = library_index()
    seen, out = set(), []
    for c in load_claims(project)["claims"]:
        sid = c.get("source")
        if sid in lib and sid not in seen:
            seen.add(sid)
            out.append(lib[sid])
    return out


def format_source(s: dict) -> str:
    who = s.get("authors") or ""
    year = f" ({s['year']})" if s.get("year") else ""
    venue = f", {s['venue']}" if s.get("venue") else ""
    link = f"https://doi.org/{s['doi']}" if s.get("doi") else (s.get("url") or "")
    title = s.get("title", s["id"])
    return f"{who}{year}. {title}{venue}. {link}".strip(". ").strip()


# ------------------------------------------------------------------ link check
def check_links(timeout: float = 15.0) -> list[str]:
    import requests
    lib = load_library()
    report = []
    headers = {"User-Agent": "Mozilla/5.0 (Video Fabrikasi link check)"}
    for s in lib["sources"]:
        url = s.get("url") or (f"https://doi.org/{s['doi']}" if s.get("doi") else None)
        if not url:
            continue
        try:
            r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True, stream=True)
            status = r.status_code
            r.close()
        except requests.RequestException as e:
            status = f"hata: {type(e).__name__}"
        ok = isinstance(status, int) and (status < 400 or status in (401, 403, 429))
        s["link"] = {"ok": ok, "status": status, "checked": date.today().isoformat()}
        report.append(f"{'✓' if ok else '✗'} {s['id']}: {status}")
    save_library(lib)
    return report
