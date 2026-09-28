"""Shot-level translation for dubbed versions. Each shot keeps its image; only the words change,
so a Turkish (or any other) video reuses every drawing. Result stored in storyboard shot.i18n.<lang>.

manual (free): prompt file → paste into Claude → save YAML answer → apply
anthropic (paid): automatic, in batches
"""
from __future__ import annotations

from .config import Config
from .planner import parse_yaml_reply
from .project import Project

LANG_NAMES = {"tr": "Turkish", "es": "Spanish", "pt": "Brazilian Portuguese", "de": "German", "fr": "French",
              "ar": "Arabic", "hi": "Hindi", "en": "English"}

INSTRUCTIONS = """Translate the narration of a YouTube explainer video into {name}, shot by shot.
Each shot is shown on screen while its words are spoken, so:
- translate every shot separately and keep the same order; never move words between shots,
- sound like natural spoken {name} narration (not literal), keep numbers and facts exact,
- the translation becomes an extra audio track on the SAME video, so each sentence must fit the time of the
  original: aim for about the same spoken length (within ±10%). Where {name} naturally runs longer, choose the
  shorter natural wording rather than a literal one.
Reply with ONLY a YAML mapping of shot id to translated text, e.g.
s001: "..."
s002: "..."
"""


def build_prompt(project: Project, lang: str, subset: list[dict] | None = None) -> str:
    shots = project.load_storyboard()["shots"]
    todo = subset if subset is not None else [s for s in shots if not (s.get("i18n") or {}).get(lang)]
    lines = [INSTRUCTIONS.format(name=LANG_NAMES.get(lang, lang)), "", f"# {project.meta.get('title', project.slug)}", ""]
    lines += [f"{s['id']}: {s['text']}" for s in todo]
    return "\n".join(lines)


def apply_translation(project: Project, lang: str, mapping: dict) -> int:
    sb = project.load_storyboard()
    n = 0
    for s in sb["shots"]:
        t = mapping.get(s["id"])
        if t:
            s.setdefault("i18n", {})[lang] = str(t).strip()
            n += 1
    project.save_storyboard(sb)
    return n


def translate(project: Project, cfg: Config, lang: str) -> None:
    if lang == project.primary_lang():
        print("  ana dil çevrilmez.")
        return
    provider = cfg.get_path("planner.provider", "manual")
    if provider == "manual":
        out = project.build / f"translate_{lang}_prompt.md"
        out.write_text(build_prompt(project, lang), encoding="utf-8")
        print(f"  çeviri istemi hazır: {out}\n  Claude'a yapıştır, YAML cevabını panelde 'Çeviriyi uygula' kutusuna yapıştır.")
        return
    from .llm import complete
    shots = [s for s in project.load_storyboard()["shots"] if not (s.get("i18n") or {}).get(lang)]
    model = cfg.get_path("planner.anthropic.model", "claude-sonnet-5")
    for i in range(0, len(shots), 80):
        prompt = build_prompt(project, lang, subset=shots[i:i + 80])
        n = apply_translation(project, lang, parse_yaml_reply(complete(prompt, model)))
        print(f"  çeviri [{lang}]: {n} shot")
