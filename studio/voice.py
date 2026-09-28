"""Narration: synthesizes each unit (sentence or paragraph), trims its silence,
joins them with controlled pauses into build/<lang>/audio/narration.wav and writes a manifest.
Units whose text did not change are reused from cache (no re-synthesis, no cost)."""
from __future__ import annotations

import hashlib
import json
import subprocess

import numpy as np
import soundfile as sf

from .config import Config
from .project import Project, shot_text
from .tts import get_provider

OUT_SR = 44100
SENTENCE_PAUSE = 0.16


def _resample(x: np.ndarray, sr: int, target: int = OUT_SR) -> np.ndarray:
    if sr == target:
        return x.astype("float32")
    out = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0",
         "-f", "f32le", "-ar", str(target), "-ac", "1", "pipe:1"],
        input=x.astype("<f4").tobytes(), capture_output=True, check=True,
    ).stdout
    return np.frombuffer(out, dtype="<f4").copy()


def _trim(x: np.ndarray, sr: int, thresh: float = 0.012, margin: float = 0.04) -> tuple[np.ndarray, float]:
    """Remove leading/trailing silence. Returns (audio, seconds removed at the start)."""
    loud = np.flatnonzero(np.abs(x) > thresh)
    if loud.size == 0:
        return x, 0.0
    m = int(margin * sr)
    a, b = max(0, loud[0] - m), min(len(x), loud[-1] + m)
    return x[a:b], a / sr


def build_units(shots: list[dict], unit: str, lang: str | None = None, primary: str | None = None) -> list[dict]:
    key = "sent" if unit == "sentence" else "para"
    units: list[dict] = []
    for s in shots:
        text = shot_text(s, lang, primary) if lang and primary else s["text"]
        if not units or units[-1]["key"] != s.get(key):
            units.append({"key": s.get(key), "para": s["para"], "text": "", "spans": []})
        u = units[-1]
        start = len(u["text"]) + (1 if u["text"] else 0)
        u["text"] = f"{u['text']} {text}" if u["text"] else text
        u["spans"].append({"id": s["id"], "start": start, "end": start + len(text)})
    return units


def make_voice(project: Project, cfg: Config, lang: str | None = None) -> dict:
    lang = lang or project.primary_lang()
    shots = project.load_storyboard()["shots"]
    tts = get_provider(cfg, lang)
    units = build_units(shots, tts.unit, lang, project.primary_lang())
    para_pause = float(cfg.get_path("tts.paragraph_pause", 0.35))
    cache = project.audio_dir(lang) / "units"
    cache.mkdir(exist_ok=True)

    pieces: list[np.ndarray] = []
    cursor = 0.0
    for i, u in enumerate(units):
        h = hashlib.sha1(f"{tts.cache_key()}|{u['text']}".encode()).hexdigest()[:16]
        wav, meta = cache / f"{h}.wav", cache / f"{h}.json"
        if wav.exists() and meta.exists():
            audio, _ = sf.read(wav, dtype="float32")
            char_starts = json.loads(meta.read_text())["char_starts"]
        else:
            print(f"  ses {i + 1}/{len(units)}: {u['text'][:60]}")
            sp = tts.synthesize(u["text"])
            audio = _resample(sp.samples, sp.sample_rate)
            audio, cut = _trim(audio, OUT_SR)
            char_starts = [max(0.0, t - cut) for t in sp.char_starts] if sp.char_starts else None
            sf.write(wav, audio, OUT_SR, subtype="PCM_16")
            meta.write_text(json.dumps({"char_starts": char_starts}))
        dur = len(audio) / OUT_SR
        u.update({"file": str(wav.relative_to(project.dir)), "offset": round(cursor, 3),
                  "duration": round(dur, 3), "char_starts": char_starts})
        pieces.append(audio)
        last_in_para = i == len(units) - 1 or units[i + 1]["para"] != u["para"]
        gap = para_pause if last_in_para else SENTENCE_PAUSE
        if i < len(units) - 1:
            pieces.append(np.zeros(int(gap * OUT_SR), dtype="float32"))
            cursor += gap
        cursor += dur

    narration = np.concatenate(pieces) if pieces else np.zeros(1, dtype="float32")
    out = project.audio_dir(lang) / "narration.wav"
    sf.write(out, narration, OUT_SR, subtype="PCM_16")
    manifest = {"provider": tts.cache_key(), "lang": lang, "unit": tts.unit, "sample_rate": OUT_SR,
                "duration": round(len(narration) / OUT_SR, 3), "units": units}
    project.write_json(project.audio_manifest_path(lang), manifest)
    print(f"  seslendirme hazır [{lang}]: {manifest['duration']:.1f} sn, {len(units)} parça")
    return manifest
