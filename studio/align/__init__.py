"""Turns the audio manifest into start/end seconds for every shot (build/<lang>/timing.json).

Strategy per unit, best first:
  1. exact     — the voice provider returned per-character times (ElevenLabs, estimate)
  2. whisper   — word timestamps from faster-whisper (optional install)
  3. proportional — time split by character count, with extra weight for punctuation pauses
With Kokoro, units are single sentences, so proportional timing is already close (±0.2 s).
"""
from __future__ import annotations

from ..config import Config
from ..project import Project


def _weight(text: str) -> float:
    w = len(text)
    w += 4 * sum(text.count(c) for c in ",;:")
    w += 6 * sum(text.count(c) for c in ".!?—")
    return max(w, 1)


def _proportional(u: dict) -> list[float]:
    total = sum(_weight(u["text"][s["start"]:s["end"]]) for s in u["spans"])
    starts, acc = [], 0.0
    for s in u["spans"]:
        starts.append(u["offset"] + u["duration"] * acc / total)
        acc += _weight(u["text"][s["start"]:s["end"]])
    return starts


def _exact(u: dict) -> list[float]:
    cs = u["char_starts"]
    return [u["offset"] + cs[min(s["start"], len(cs) - 1)] for s in u["spans"]]


def align(project: Project, cfg: Config, lang: str | None = None) -> list[dict]:
    lang = lang or project.primary_lang()
    mpath = project.audio_manifest_path(lang)
    if not mpath.exists():
        raise SystemExit(f"[{lang}] seslendirme yok. Önce 'voice' adımını çalıştır.")
    manifest = project.read_json(mpath)
    mode = cfg.get_path("align.provider", "auto")
    whisper = None
    if mode == "whisper" or (mode == "auto" and manifest["unit"] == "paragraph"):
        from .whisper_align import WhisperAligner
        whisper = WhisperAligner.try_create(cfg, required=(mode == "whisper"))

    timeline: list[dict] = []
    for u in manifest["units"]:
        if u.get("char_starts") and mode != "whisper":
            starts, how = _exact(u), "exact"
        elif whisper is not None:
            starts, how = whisper.align_unit(project, u, lang), "whisper"
        else:
            starts, how = _proportional(u), "proportional"
        for s, t in zip(u["spans"], starts):
            timeline.append({"id": s["id"], "start": round(t, 3), "how": how})

    timeline.sort(key=lambda r: r["start"])
    if timeline:
        timeline[0]["start"] = 0.0
    end_of_audio = manifest["duration"] + 0.6
    for i, r in enumerate(timeline):
        r["end"] = timeline[i + 1]["start"] if i + 1 < len(timeline) else round(end_of_audio, 3)
        r["duration"] = round(r["end"] - r["start"], 3)
    project.write_json(project.timing_path(lang), timeline)
    avg = sum(r["duration"] for r in timeline) / max(1, len(timeline))
    print(f"  zamanlama hazır [{lang}]: {len(timeline)} shot, ortalama {avg:.2f} sn/görsel")
    return timeline
