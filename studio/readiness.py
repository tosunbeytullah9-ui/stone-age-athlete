"""Quality gate. Protects the channel against YouTube's 'inauthentic / mass-produced content' rules
(July 2026) by refusing to call a project ready until it is researched, sourced and varied.

Each check: {key, ok, level: block|warn|info, message}. A project is 'ready' when no block fails.
"""
from __future__ import annotations

import json
import re

from .project import Project


def _visual_key(shot: dict) -> str:
    return json.dumps(shot.get("visual"), sort_keys=True, default=str)


def check(project: Project, lang: str | None = None) -> dict:
    out: list[dict] = []

    def add(key, ok, level, message):
        out.append({"key": key, "ok": bool(ok), "level": level, "message": message})

    script = project.script_path.read_text(encoding="utf-8") if project.script_path.exists() else ""
    body = "\n".join(ln for ln in re.sub(r"<!--[\s\S]*?-->", "", script).splitlines() if not ln.lstrip().startswith("#"))
    words = len(re.findall(r"\b\w+\b", body))
    templ = "Write the first paragraph" in script
    add("script", words >= 150 and not templ, "block",
        f"Senaryo: {words} kelime" + (" (şablon metni duruyor)" if templ else "") + " — en az 150 kelime gerekli")

    from .claims import claim_checks, load_claims
    if load_claims(project)["claims"]:
        out.extend(claim_checks(project))
    else:
        src = project.sources_path.read_text(encoding="utf-8") if project.sources_path.exists() else ""
        links = len(re.findall(r"https?://", src))
        add("sources", links >= 3, "block", f"Kaynaklar: {links} bağlantı — en az 3 gerekli (her iddiaya bir kaynak)")
        out.extend(claim_checks(project))

    if not project.storyboard_path.exists():
        add("storyboard", False, "block", "Storyboard yok — 'Böl' adımını çalıştır")
        return _summary(out)
    shots = project.load_storyboard().get("shots", [])
    planned = sum(1 for s in shots if s.get("visual"))
    add("plan", planned == len(shots) and shots, "block", f"Görsel planı: {planned}/{len(shots)} shot")

    # repetition: the same recipe many times in a row looks mass-produced
    run, worst, worst_at = 1, 1, None
    for a, b in zip(shots, shots[1:]):
        if a.get("visual") and _visual_key(a) == _visual_key(b):
            run += 1
            if run > worst:
                worst, worst_at = run, b["id"]
        else:
            run = 1
    add("variety", worst <= 3, "warn",
        f"Çeşitlilik: aynı sahne en fazla {worst} kez art arda" + (f" ({worst_at} civarı)" if worst > 3 else ""))
    bgs = [(s.get("visual") or {}).get("bg") if isinstance(s.get("visual"), dict) else None for s in shots]
    named = [b for b in bgs if b]
    if named:
        top = max(set(named), key=named.count)
        share = named.count(top) / len(shots)
        add("bg_share", share <= 0.35, "warn", f"En çok kullanılan arka plan: {top} (%{share * 100:.0f}; en fazla %35 önerilir)")
        run, worst_bg, where = 1, 1, None
        for a, b, sh in zip(bgs, bgs[1:], shots[1:]):
            run = run + 1 if a and a == b else 1
            if run > worst_bg:
                worst_bg, where = run, sh["id"]
        add("bg_run", worst_bg <= 6, "warn", f"Aynı arka planda en uzun seri: {worst_bg} shot"
            + (f" ({where} civarı; yakın çekim/farklı sahne ekle)" if worst_bg > 6 else ""))
    distinct = len({_visual_key(s) for s in shots if s.get("visual")})
    if shots:
        add("distinct", distinct >= 0.6 * len(shots), "warn", f"Farklı sahne sayısı: {distinct}/{len(shots)}")

    gem = sum(1 for s in shots if s.get("engine") == "gemini" or isinstance(s.get("visual"), str)
              or (isinstance(s.get("visual"), dict) and "prompt" in s["visual"] and "bg" not in s["visual"]))
    add("cost", True, "info", f"Ücretli AI görseli: {gem} shot" if gem else "Tüm görseller ücretsiz (kodla çizim)")

    imgs = sum(1 for s in shots if (project.shots_dir / f"{s['id']}.png").exists())
    add("images", imgs == len(shots) and shots, "warn", f"Görseller: {imgs}/{len(shots)} üretildi")

    for lg in project.ch.languages:
        prefix = f"[{lg}] "
        if lg != project.primary_lang():
            tr = sum(1 for s in shots if (s.get("i18n") or {}).get(lg))
            add(f"i18n_{lg}", tr == len(shots), "warn", prefix + f"Çeviri: {tr}/{len(shots)}")
        add(f"voice_{lg}", project.audio_manifest_path(lg).exists(), "info", prefix + "Seslendirme")
        add(f"video_{lg}", project.video_path(lg).exists(), "info", prefix + "Video")
    return _summary(out)


def _summary(checks: list[dict]) -> dict:
    blocked = [c for c in checks if c["level"] == "block" and not c["ok"]]
    return {"ready": not blocked, "checks": checks}
