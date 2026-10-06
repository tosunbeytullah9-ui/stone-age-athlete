"""Quality gate. Protects the channel against YouTube's 'inauthentic / mass-produced content' rules
(July 2026) by refusing to call a project ready until it is researched, sourced and varied.

Each check: {key, ok, level: block|warn|info, message}. A project is 'ready' when no block fails.
"""
from __future__ import annotations

import re

from .project import Project


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
    from .images import engine_name, scenes
    groups = scenes(shots)
    planned = sum(1 for g in groups if g[0].get("visual"))
    unplanned_ids = [g[0]["id"] for g in groups if not g[0].get("visual")]
    add("plan", not unplanned_ids and shots, "block", f"Sahne planı: {planned}/{len(groups)} sahne"
        + (f" (plansız: {unplanned_ids[0]}…)" if unplanned_ids else ""))

    # pacing: a picture should stay 5-9 s (2-4 shots); long holds bore, 1-shot scenes flicker
    if groups:
        longest = max(groups, key=len)
        add("scene_len", len(longest) <= 5, "warn", f"En uzun sahne: {len(longest)} shot ({longest[0]['id']})"
            + (" — 5'ten fazlası sıkıcı; böl" if len(longest) > 5 else ""))
        singles = sum(1 for g in groups if len(g) == 1)
        add("scene_count", len(groups) <= 0.6 * len(shots) or len(shots) < 20, "warn",
            f"Sahne sayısı: {len(groups)} ({len(shots)} shot; tek shotluk sahne: {singles})")
    prompts = [g[0]["visual"].get("prompt") for g in groups if isinstance(g[0].get("visual"), dict)
               and g[0]["visual"].get("prompt")]
    dup = len(prompts) - len(set(prompts))
    add("variety", dup == 0, "warn", "Tekrarlanan resim istemi yok" if not dup else f"{dup} sahne aynı istemi tekrarlıyor")
    coach = sum(1 for g in groups if "coach" in ((g[0].get("visual") or {}).get("characters") or [])
                if isinstance(g[0].get("visual"), dict))
    if groups:
        add("coach", coach <= 0.3 * len(groups), "warn", f"Koçlu sahne: {coach}/{len(groups)} (en fazla %30 önerilir)")

    paid = sum(1 for g in groups if g[0].get("visual") and engine_name(g[0], {}) == "gemini")
    add("cost", True, "info", f"AI resmi: {paid} sahne (yaklaşık {paid * 0.05:.2f} $; değişmeyen sahne tekrar ödenmez)")

    heads = [g[0] for g in groups if g[0].get("visual")]
    imgs = sum(1 for s in heads if (project.shots_dir / f"{s['id']}.png").exists())
    add("images", imgs == len(heads) and heads, "warn", f"Resimler: {imgs}/{len(heads)} sahne çizildi")

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
