"""YouTube monetization policy guard (docs/POLICY.md). Every step from research to upload is checked against
the rules that decide whether a channel can earn money:

  YouTube channel monetization policies (support.google.com/youtube/answer/1311392, July 2026 wording):
    generic or repetitive content · reused content · unsatisfying or off-putting content ·
    AI personas related to sensitive topics (an AI "expert" giving health/finance/legal advice) · creator integrity
  Advertiser-friendly guidelines (answer/6162278): profanity, graphic violence, shock in titles/thumbnails/opening
  Spam & deceptive practices (answer/2801973): titles and thumbnails that promise what the video does not deliver,
    mass uploads of near-identical videos
  Medical misinformation (answer/13813322): health claims must not contradict health authorities
  Altered or synthetic content (answer/14328491): realistic AI depictions must be disclosed ("AI use" on upload)

The checks work on plain inputs (a script, titles, thumbnail words, claims) so the same rules judge a preparation
package before it becomes a project (studio/prep.py) and the project itself (studio/readiness.py). Uploading also
needs the owner's review (`review:` in project.yaml): the owner is the human control of every video.

channel.yaml → policy (defaults in config.yaml → policy):
  sensitive: [health]            # topics where the AI-persona rule applies: health | finance | legal | politics
  sensitive_series: [body-files] # only these series are sensitive (empty = every video of the channel)
  narrator: fictional            # fictional (an openly fictional character, never claims credentials) | owner
  realistic_visuals: false       # photorealistic pictures of real people/places/events → the AI label is required
  transparency: "..."            # printed in every description: who makes the channel and what is AI-made
"""
from __future__ import annotations

import re
from datetime import date
from functools import lru_cache
from typing import Any

SENSITIVE = ("health", "finance", "legal", "politics")
CREDENTIAL = re.compile(
    r"\b(?:as\s+(?:a|an|your)\s+|i\s*(?:'m|\s+am)\s+(?:a|an|your)\s+(?:(?:certified|qualified|licensed|registered)\s+)?)"
    r"(doctor|physician|surgeon|nurse|dietitian|dietician|nutritionist|physio(?:therapist)?|therapist|"
    r"psychologist|pharmacist|coach|trainer|expert|specialist|lawyer|attorney|financial (?:advisor|adviser)|"
    r"accountant)\b", re.I)
PERSONAL = re.compile(r"\b(my (?:patients|clients|athletes)|in my (?:clinic|practice|years as a)|trust me|"
                      r"take my word|i (?:prescribe|diagnose))\b", re.I)
ADVICE_WITHOUT_SOURCE = re.compile(r"\b(you should (?:take|stop taking|drink|eat|fast)|cures?\b|"
                                   r"guaranteed to|miracle|detox(?:es|ify)?)\b", re.I)
PROFANITY_STRONG = re.compile(r"\b(f+u+c+k\w*|motherf\w+|c+u+n+t\w*|n[i1]gg\w*|fag+ot\w*)\b", re.I)
PROFANITY_MODERATE = re.compile(r"\b(shit\w*|bitch\w*|bastard\w*|ass(?:hole)?s?|dick\w*|piss\w*|crap)\b", re.I)
GRAPHIC = re.compile(r"\b(gore|gory|gruesome|decapitat\w+|beheaded|disembowel\w*|mutilat\w+|dismember\w*|"
                     r"blood[- ]?bath|torture[ds]?|snuff|corpses?|dead bod(?:y|ies)|suicide|self[- ]harm)\b", re.I)
SHOCK_BAIT = re.compile(r"\b(you won't believe|gone wrong|shocking|disturbing|(?:will|would) make you (?:sick|cry)|"
                        r"not clickbait|(?:last|final) warning)\b", re.I)


# ------------------------------------------------------------------ settings
def settings(cfg) -> dict[str, Any]:
    """Global defaults (config.yaml → policy) merged with the channel's policy block."""
    out = {"sensitive": [], "sensitive_series": [], "narrator": "fictional", "realistic_visuals": False,
           "transparency": "", "max_long_per_week": 3, "similarity_warn": 0.12, "similarity_block": 0.25,
           "quote_words": 40}
    out.update({k: v for k, v in (cfg.get_path("policy") or {}).items() if v is not None})
    out.update({k: v for k, v in (cfg.get_path("channel.policy") or {}).items() if v is not None})
    if isinstance(out["sensitive"], str):
        out["sensitive"] = [out["sensitive"]]
    return out


def is_sensitive(pol: dict, series: str | None) -> bool:
    topics = [t for t in pol.get("sensitive") or [] if t in SENSITIVE]
    if not topics:
        return False
    only = pol.get("sensitive_series") or []
    return not only or (series or "") in only or not series


def ai_label(cfg, pol: dict | None = None, lang: str = "tr") -> tuple[bool, str]:
    """(required, reason) for YouTube's 'AI use' question on upload."""
    pol = pol or settings(cfg)
    en = lang == "en"
    if pol.get("realistic_visuals"):
        return True, ("the pictures are photorealistic: YouTube requires the 'AI use' disclosure" if en else
                      "resimler gerçekçi (fotoğraf gibi): YouTube 'AI use' etiketini zorunlu tutuyor")
    if pol.get("real_person_voice"):
        return True, ("the narrator imitates a real person's voice" if en else
                      "anlatıcı sesi gerçek bir kişinin sesini taklit ediyor")
    return False, ("not required: the pictures are clearly illustrations and the synthetic narrator imitates no real "
                   "person; never make realistic depictions of real people or events" if en else
                   "gerekmiyor: resimler açıkça çizim, sentetik anlatıcı gerçek bir kişiyi taklit etmiyor; yine de "
                   "açıklamadaki şeffaflık satırı neyin yapay olduğunu söylüyor")


# ------------------------------------------------------------------ text helpers
def _clean(script: str) -> str:
    script = re.sub(r"<!--[\s\S]*?-->", " ", script or "")
    script = "\n".join(ln for ln in script.splitlines() if not ln.lstrip().startswith("#"))
    return re.sub(r"\[[a-z][a-z \-]{0,30}\]", " ", script, flags=re.I)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


@lru_cache(maxsize=256)
def shingles(text: str, n: int = 6) -> frozenset[tuple[str, ...]]:
    w = _words(_clean(text))
    return frozenset(tuple(w[i:i + n]) for i in range(max(0, len(w) - n + 1)))


def overlap(a: str, b: str) -> float:
    """Share of a's 6-word sequences that also occur in b (recurring intros/outros give a few percent)."""
    sa = shingles(a)
    return len(sa & shingles(b)) / len(sa) if sa else 0.0


def channel_scripts(cid: str, exclude: str | None = None) -> dict[str, str]:
    from .channel import Channel
    from .project import Project
    out = {}
    ch = Channel(cid)
    for slug in ch.project_slugs():
        if slug == exclude:
            continue
        p = Project(cid, slug)
        if p.script_path.exists():
            out[slug] = p.script_path.read_text(encoding="utf-8")
    return out


def verdict_of(script: str) -> str | None:
    m = re.search(r"verdict\s*:\s*([^.\n!]+)", _clean(script), re.I)
    return " ".join(m.group(1).upper().split()) if m else None


# ------------------------------------------------------------------ checks on plain inputs
Check = dict


def _c(key: str, ok: bool, level: str, message: str) -> Check:
    return {"key": key, "ok": bool(ok), "level": level, "message": message}


def script_checks(cid: str, script: str, pol: dict, sensitive: bool, exclude: str | None = None) -> list[Check]:
    out: list[Check] = []
    body = _clean(script)
    # 1. generic / repetitive: the body of every video must be its own (recurring intro and outro are fine)
    others = channel_scripts(cid, exclude)
    best, best_slug = 0.0, ""
    for slug, txt in others.items():
        v = overlap(script, txt)
        if v > best:
            best, best_slug = v, slug
    lvl = "block" if best >= pol["similarity_block"] else "warn"
    out.append(_c("policy_original", best < pol["similarity_warn"], lvl,
                  (f"Özgünlük: en benzer video {best_slug} ile %{round(best * 100)} ortak cümle dizisi" if best >= 0.01
                   else "Özgünlük: kanalda benzer senaryo yok")
                  + ("" if best < pol["similarity_warn"] else " — tekrar eden içerik sayılabilir (YouTube: "
                     "generic or repetitive content); gövdeyi yeniden yaz")))
    # 2. the same outcome every time (a template storyline) — only for channels with a verdict
    mine = verdict_of(script)
    if mine:
        recent = [v for v in (verdict_of(t) for t in list(others.values())[-7:]) if v]
        same = len(recent) >= 5 and all(v == mine for v in recent)
        out.append(_c("policy_outcome", not same, "warn",
                      f"Hüküm çeşitliliği: bu video {mine}" + (f", son {len(recent)} videonun hepsi de {mine} — "
                      "aynı sonuçla biten kalıp hikâye riski; arada MOSTLY WRONG / RIGHT, FOR THE WRONG REASON "
                      "gibi farklı sonuçlar seç" if same else "")))
    # 3. AI persona on sensitive topics: the narrator never claims to be a human expert
    cred = CREDENTIAL.findall(body) + PERSONAL.findall(body)
    if sensitive:
        out.append(_c("policy_persona", not cred, "block",
                      "Anlatıcı uzman/doktor/koç olduğunu iddia etmiyor (YouTube: AI personas related to sensitive "
                      "topics)" if not cred else f"Anlatıcı uzmanlık iddia ediyor: “{cred[0]}…” — sentetik ses bir "
                      "sağlık uzmanı gibi konuşamaz; öneriyi kaynağa/sağlık otoritesine bağla"))
        risky = sorted({m.group(0).lower() for m in ADVICE_WITHOUT_SOURCE.finditer(body)})
        out.append(_c("policy_advice", not risky, "warn",
                      "Tedavi/mucize/kesin sonuç dili yok" if not risky else
                      f"Sağlık dili kontrol edilmeli: {', '.join(risky[:4])} — tavsiye kaynağa ve sağlık "
                      "otoritelerine dayanmalı, kişisel tedavi önerisi olmamalı"))
    elif cred:
        out.append(_c("policy_persona", False, "warn", f"Anlatıcı uzmanlık iddia ediyor: “{cred[0]}…”"))
    # 4. advertiser-friendly opening (the first seconds weigh most)
    opening = " ".join(_words(body)[:40])
    bad = PROFANITY_STRONG.findall(opening) + PROFANITY_MODERATE.findall(opening) + GRAPHIC.findall(opening)
    out.append(_c("policy_opening", not bad, "warn", "Açılış reklamveren dostu (küfür/şiddet yok)" if not bad
                  else f"Açılışta reklamveren riski: {', '.join(sorted(set(bad))[:4])} — ilk saniyeleri temiz tut"))
    strong = PROFANITY_STRONG.findall(body)
    if strong:
        out.append(_c("policy_language", False, "warn", f"Ağır küfür: {strong[0]} — sınırlı reklam"))
    # 5. reused content: long word-for-word readings of other people's text
    longq = [q for q in re.findall(r"[\"“]([^\"”]{40,})[\"”]", body) if len(q.split()) > pol["quote_words"]]
    out.append(_c("policy_quotes", not longq, "warn", "Uzun alıntı yok (kendi anlatımın)" if not longq else
                  f"{len(longq)} alıntı {pol['quote_words']} kelimeden uzun — başkasının metnini okumak "
                  "'reused content' sayılır; kısalt ve yorumla"))
    return out


def metadata_checks(titles: list[str], thumb_words: list[str], claim_text: str) -> list[Check]:
    """Titles and thumbnail words: advertiser-friendly and not misleading."""
    out: list[Check] = []
    text = " | ".join([*titles, *thumb_words])
    strong, moderate = PROFANITY_STRONG.findall(text), PROFANITY_MODERATE.findall(text)
    graphic, shock = GRAPHIC.findall(text), SHOCK_BAIT.findall(text)
    out.append(_c("policy_meta_language", not strong, "block", "Başlık/kapakta küfür yok" if not (strong or moderate)
                  else f"Başlık/kapakta küfür: {(strong or moderate)[0]} — reklam kısıtlanır"))
    if moderate and not strong:
        out[-1] = _c("policy_meta_language", False, "warn", f"Başlık/kapakta hafif küfür: {moderate[0]} — sınırlı reklam")
    out.append(_c("policy_meta_shock", not (graphic or shock), "warn", "Başlık/kapak şok ve şiddet dili kullanmıyor"
                  if not (graphic or shock) else f"Başlık/kapakta riskli dil: {', '.join((graphic + shock)[:3])} — "
                  "reklamveren kuralları başlık ve kapakta daha sıkı"))
    from .motion_rules import _numbers
    norm = lambda t: re.sub(r"(?<=\d)\.(?=\d{3}\b)", ",", str(t))   # 7.000 (European) = 7,000
    have = _numbers(norm(claim_text), words=True)
    loose = []
    for t in titles[:1] + thumb_words:
        loose += [f"{n:g}" for n in sorted(_numbers(norm(t))) if n not in have]
    out.append(_c("policy_meta_claims", not loose, "warn", "Başlık ve kapaktaki sayılar iddialarda var" if not loose
                  else f"Başlık/kapakta iddialarda olmayan sayı: {', '.join(loose[:4])} — yanıltıcı başlık sayılabilir"))
    caps = [t for t in titles[:1] if len(t) > 12 and sum(ch.isupper() for ch in t) > 0.6 * sum(ch.isalpha() for ch in t)]
    if caps:
        out.append(_c("policy_meta_caps", False, "warn", "Başlık neredeyse tamamen büyük harf — tık tuzağı gibi görünür"))
    return out


def channel_checks(cfg, pol: dict, sensitive: bool) -> list[Check]:
    out: list[Check] = []
    yt = cfg.get_path("channel.youtube") or {}
    need, why = ai_label(cfg, pol)
    if need:
        out.append(_c("policy_ai_label", bool(yt.get("synthetic_media")), "block",
                      f"YouTube 'AI use' etiketi: {why}" + ("" if yt.get("synthetic_media") else
                      " → channel.yaml youtube.synthetic_media: true")))
    else:
        out.append(_c("policy_ai_label", True, "info", f"YouTube 'AI use' etiketi {why}"))
    out.append(_c("policy_kids", isinstance(yt.get("made_for_kids"), bool), "block",
                  "Çocuklara yönelik değil/öyle olarak beyan edildi" if isinstance(yt.get("made_for_kids"), bool)
                  else "channel.yaml youtube.made_for_kids: true/false yazılmalı (COPPA beyanı)"))
    transparency = (pol.get("transparency") or "").strip()
    out.append(_c("policy_transparency", bool(transparency) or not sensitive, "block" if sensitive else "warn",
                  "Açıklamada şeffaflık satırı var (kim yapıyor, ne yapay)" if transparency else
                  "channel.yaml policy.transparency boş — hassas konuda kimin ürettiği ve neyin yapay olduğu "
                  "açıklamada yazmalı (YouTube: creator integrity, AI personas)"))
    if pol.get("narrator") not in ("fictional", "owner"):
        out.append(_c("policy_narrator", False, "warn", "policy.narrator: fictional | owner olmalı"))
    tracks = cfg.get_path("audio.music_tracks") or cfg.get_path("audio.music")
    if tracks:
        lic = cfg.get_path("audio.music_licence")
        out.append(_c("policy_music", bool(lic), "warn", f"Müzik lisansı: {lic}" if lic else
                      "Müzik kullanılıyor ama lisansı yazılmamış (audio.music_licence: youtube-audio-library ...)"))
    return out


def pace_check(cid: str, planned: str | None, slot: str, pol: dict, exclude: str | None = None) -> Check | None:
    """Mass uploads: how many long videos of the channel fall in the same calendar week."""
    if not planned or slot != "long":
        return None
    try:
        d = date.fromisoformat(str(planned))
    except ValueError:
        return None
    from .channel import Channel
    from .project import Project
    from .publish import get_publish
    wk = d.isocalendar()[:2]
    n = 1
    for slug in Channel(cid).project_slugs():
        if slug == exclude:
            continue
        pub = Project(cid, slug).meta.get("publish") or {}   # no idea-bank lookup in a loop
        day = pub.get("published_at") or pub.get("planned_date")
        try:
            if day and pub.get("slot", "long") == "long" and date.fromisoformat(str(day)).isocalendar()[:2] == wk:
                n += 1
        except ValueError:
            continue
    mx = int(pol.get("max_long_per_week", 3))
    return _c("policy_pace", n <= mx, "warn", f"Yayın temposu: o hafta {n} uzun video (en fazla {mx})"
              + ("" if n <= mx else " — seri üretim izlenimi verir; tarihi kaydır"))


# ------------------------------------------------------------------ project
def thumb_words(meta: dict) -> list[str]:
    out = []
    for t in meta.get("thumbnails") or []:
        for k in ("myth", "note", "text", "stamp"):
            v = t.get(k) if isinstance(t, dict) else None
            if isinstance(v, dict):
                out += [str(x) for x in v.values()]
            elif v:
                out.append(str(v))
    return out


def project_checks(project, cfg=None) -> list[Check]:
    from .claims import library_index, load_claims
    from .config import load_config
    from .publish import get_publish
    cfg = cfg or load_config(project.channel)
    pol = settings(cfg)
    pub = get_publish(project)
    sensitive = is_sensitive(pol, pub.get("series"))
    script = project.script_path.read_text(encoding="utf-8") if project.script_path.exists() else ""
    out = script_checks(project.channel, script, pol, sensitive, exclude=project.slug)
    claims = load_claims(project)["claims"]
    titles = [t for t in [pub.get("title_used") or project.meta.get("title") or ""] if t]
    out += metadata_checks(titles, thumb_words(project.meta), " ".join(str(c.get("text", "")) for c in claims))
    if sensitive and claims:
        lib = library_index()
        strong = [c for c in claims if (lib.get(c.get("source")) or {}).get("type") in
                  ("guideline", "review", "meta-analysis")]
        out.append(_c("policy_health_sources", bool(strong), "warn",
                      f"Sağlık videosu: {len(strong)} iddia kılavuz/derleme/meta-analize dayanıyor" if strong else
                      "Sağlık videosu ama hiçbir iddia kılavuz, derleme ya da meta-analize dayanmıyor — sağlık "
                      "otoritesinin görüşünü ekle (YouTube: medical misinformation)"))
        over = [c.get("id", "?") for c in claims if c.get("overclaim")]
        out.append(_c("policy_overclaim", not over, "block", "Kaynağın söylediğinden fazlası yok" if not over else
                      f"Sağlık videosunda kaynaktan fazlasını söyleyen cümle: {', '.join(over)} — düzelt"))
    out += channel_checks(cfg, pol, sensitive)
    pc = pace_check(project.channel, pub.get("planned_date"), pub.get("slot", "long"), pol, exclude=project.slug)
    if pc:
        out.append(pc)
    rv = review_state(project)
    out.append(_c("owner_review", rv["approved"], "warn", "Sahip onayı: " + rv["message"]))
    return out


# ------------------------------------------------------------------ the owner's review (human control)
REVIEW_STEPS = {
    "claims_checked": "İddiaları kaynaklarıyla karşılaştırdım",
    "pictures_checked": "Kontak sayfasına baktım (resimler sözlerle uyumlu, anatomi doğru)",
    "watched_final": "Bitmiş videoyu baştan sona izledim",
    "policy_ok": "Politika uyarılarını okudum; bu video kendi bakış açısını taşıyor",
}


def review_state(project) -> dict:
    rv = project.meta.get("review") or {}
    done = [k for k in REVIEW_STEPS if rv.get(k)]
    missing = [REVIEW_STEPS[k] for k in REVIEW_STEPS if not rv.get(k)]
    return {"steps": {k: bool(rv.get(k)) for k in REVIEW_STEPS}, "labels": REVIEW_STEPS,
            "approved": not missing, "by": rv.get("by", ""), "date": rv.get("date", ""),
            "message": "tamam" + (f" ({rv.get('date')})" if rv.get("date") else "") if not missing
            else f"{len(done)}/{len(REVIEW_STEPS)} — eksik: {missing[0]}"}


def save_review(project, steps: dict) -> dict:
    meta = project.meta
    rv = {**(meta.get("review") or {})}
    for k in REVIEW_STEPS:
        if k in steps:
            rv[k] = bool(steps[k])
    rv["date"] = date.today().isoformat()
    meta["review"] = rv
    project.save_meta(meta)
    return review_state(project)


def upload_blocks(project, cfg) -> list[str]:
    """What stops an upload even when the production gate is green: the owner's review and policy blocks."""
    out = [c["message"] for c in project_checks(project, cfg) if c["level"] == "block" and not c["ok"]]
    rv = review_state(project)
    if not rv["approved"]:
        out.append("Sahip onayı eksik: " + rv["message"])
    return out
