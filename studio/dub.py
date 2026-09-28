"""Dub track: the narration of a second language fitted onto the primary language's timeline, so it can be uploaded
to YouTube as an extra audio track of the same video (YouTube Studio → Languages → Add audio track). One video then
collects the views, watch time and comments of every language.

Per paragraph: the translated narration is placed where the original paragraph starts; if it is longer than the
original it is sped up (at most `max_tempo`, default 1.15×, which still sounds natural); anything longer still spills
into the pause that follows and the report lists it so the translation can be shortened. It is never slowed down:
shorter paragraphs end with silence.

Output: build/<lang>/dub_track.wav (+ dub_report.json). Requires voice + align for both languages.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

from .config import Config
from .project import Project


def _para_spans(project: Project, lang: str) -> dict[int, tuple[float, float]]:
    shots = {s["id"]: s for s in project.load_storyboard()["shots"]}
    spans: dict[int, list[float]] = {}
    for t in project.read_json(project.timing_path(lang)):
        para = shots[t["id"]]["para"]
        sp = spans.setdefault(para, [t["start"], t["end"]])
        sp[0], sp[1] = min(sp[0], t["start"]), max(sp[1], t["end"])
    return {k: (v[0], v[1]) for k, v in spans.items()}


def _tempo(x: np.ndarray, sr: int, factor: float) -> np.ndarray:
    if abs(factor - 1) < 0.01:
        return x
    out = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0",
         "-af", f"atempo={factor:.4f}", "-f", "f32le", "-ar", str(sr), "-ac", "1", "pipe:1"],
        input=x.astype("<f4").tobytes(), capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype="<f4").copy()


def _trim_end(x: np.ndarray, thresh: float = 0.01, margin: int = 2000) -> np.ndarray:
    loud = np.flatnonzero(np.abs(x) > thresh)
    return x[: min(len(x), loud[-1] + margin)] if loud.size else x


def make_dub(project: Project, cfg: Config, lang: str) -> Path:
    primary = project.primary_lang()
    if lang == primary:
        raise SystemExit("Ana dil için dublaj izi gerekmez.")
    for lg in (primary, lang):
        if not project.timing_path(lg).exists():
            raise SystemExit(f"[{lg}] zamanlama yok: önce '{lg}' için seslendirme + zamanlama adımlarını çalıştır.")
    max_tempo = float(cfg.get_path("dub.max_tempo", 1.15))
    src, sr = sf.read(project.audio_dir(lang) / "narration.wav", dtype="float32")
    if src.ndim > 1:
        src = src.mean(axis=1)
    p_spans, l_spans = _para_spans(project, primary), _para_spans(project, lang)
    total = max(e for _, e in p_spans.values())
    out = np.zeros(int((total + 30) * sr), dtype="float32")
    cursor_end, report, worst = 0.0, [], 0.0
    for para in sorted(p_spans):
        if para not in l_spans:
            continue
        ps, pe = p_spans[para]
        ls, le = l_spans[para]
        seg = _trim_end(src[int(ls * sr): int(le * sr)])
        target = max(pe - ps - 0.12, 0.5)
        length = len(seg) / sr
        factor = min(max(length / target, 1.0), max_tempo)
        seg = _tempo(seg, sr, factor)
        start = max(ps, cursor_end + 0.08)
        a = int(start * sr)
        if a + len(seg) > len(out):
            out = np.concatenate([out, np.zeros(a + len(seg) - len(out), dtype="float32")])
        out[a: a + len(seg)] += seg
        cursor_end = start + len(seg) / sr
        over = round(cursor_end - pe, 2)
        worst = max(worst, over)
        report.append({"para": para, "tempo": round(factor, 3), "late_start": round(start - ps, 2),
                       "overrun": over if over > 0 else 0.0})
    outro = float(cfg.get_path("channel.outro.seconds", 18) or 0) if (cfg.get_path("channel.outro") or {}).get("enabled", True) else 0
    end = max(cursor_end, total) + 0.6 + outro         # same length as the video (outro included)
    out = out[: int(end * sr)]
    path = project.lang_dir(lang) / "dub_track.wav"
    sf.write(path, np.clip(out, -1, 1), sr, subtype="PCM_16")
    # loudness like the main mix (-14 LUFS), mono → stereo wav for upload
    target = float(cfg.get_path("audio.target_lufs", -14))
    final = project.lang_dir(lang) / f"dub_track.{lang}.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-af",
                    f"acompressor=threshold=-20dB:ratio=3:attack=5:release=120,loudnorm=I={target}:TP=-1.5:LRA=11",
                    "-ar", "48000", "-ac", "2", str(final)], check=True)
    path.unlink(missing_ok=True)
    project.write_json(project.lang_dir(lang) / "dub_report.json", {"paragraphs": report, "worst_overrun": worst})
    late = [r for r in report if r["overrun"] > 0.3]
    print(f"  dublaj izi hazır [{lang}]: {final.name} ({end:.1f} sn, ana video {total:.1f} sn)")
    if late:
        print(f"  uyarı: {len(late)} paragraf orijinalinden uzun kaldı (en fazla {worst:.1f} sn). "
              f"Bu paragrafların çevirisini kısalt: {', '.join(str(r['para'] + 1) for r in late)}")
    return final
