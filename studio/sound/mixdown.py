"""Renders a sound plan into two stereo stems that the video mix layers under the narration:

  ambience.wav   scene beds, cross-faded at scene changes, ducked while Mortimer speaks
  effects.wav    spot effects placed on their words

Levels are relative to the narration, so every voice, language and TTS engine gets the same balance:
  audio.ambience_db  bed level vs. the voice (default -22 dB) · audio.duck_db  extra dip under speech (5 dB)
  audio.sfx_db       effect level vs. the voice (default -12 dB)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import catalog

SR = catalog.SR


def _rms(x: np.ndarray, gate: float = 0.02) -> float:
    """RMS of the active part (ignores silence below `gate` × peak)."""
    a = np.abs(x).reshape(-1) if x.ndim == 1 else np.abs(x).mean(axis=1)
    if not a.size:
        return 0.0
    win = max(1, SR // 50)
    m = len(a) // win * win
    if m == 0:
        return float(np.sqrt((a ** 2).mean()))
    frames = np.sqrt((a[:m].reshape(-1, win) ** 2).mean(axis=1))
    act = frames[frames > gate * frames.max()] if frames.max() > 0 else frames
    return float(np.sqrt((act ** 2).mean())) if act.size else 0.0


def voice_envelope(voice: np.ndarray, n: int, attack: float = 0.03, release: float = 0.35) -> np.ndarray:
    """0..1 'someone is talking' curve at audio rate (fast attack, slow release)."""
    mono = np.abs(voice if voice.ndim == 1 else voice.mean(axis=1))
    hop = SR // 100
    m = len(mono) // hop * hop
    fr = np.sqrt((mono[:m].reshape(-1, hop) ** 2).mean(axis=1)) if m else np.zeros(1)
    thr = 0.1 * (np.percentile(fr, 95) if fr.size else 0) + 1e-9
    on = (fr > thr).astype("float32")
    out = np.zeros_like(on)
    a_up, a_dn = 1 - np.exp(-1 / (attack * 100)), 1 - np.exp(-1 / (release * 100))
    acc = 0.0
    for i, v in enumerate(on):
        acc += (a_up if v > acc else a_dn) * (v - acc)
        out[i] = acc
    t = np.arange(n) / SR
    return np.interp(t, np.arange(len(out)) / 100.0, out, right=0.0).astype("float32")


def _bed(sid: str, n: int, offset: int) -> np.ndarray:
    x = catalog.get(sid)
    if len(x) == 0:
        return np.zeros((n, 2), "float32")
    idx = (np.arange(n) + offset) % len(x)
    return x[idx]


def render_ambience(amb: list[dict], total: float, voice: np.ndarray, level_db: float = -26.0,
                    duck_db: float = 6.0, xfade: float = 0.8) -> np.ndarray:
    n = int(total * SR) + SR
    out = np.zeros((n, 2), "float32")
    v_rms = _rms(voice) or 0.05
    for k, seg in enumerate(amb):
        if seg["id"] in (None, "none"):
            continue
        a, b = int(seg["t0"] * SR), int(seg["t1"] * SR)
        fa = int(xfade * SR) if k else 0
        a0, b1 = max(0, a - fa // 2), min(n, b + int(xfade * SR) // 2)
        if b1 <= a0:
            continue
        bed = _bed(seg["id"], b1 - a0, offset=(k * 7919 * 101) % (SR * 10))
        g = v_rms * 10 ** (level_db / 20) / (_rms(bed) or 1e-6)
        ramp = np.ones(b1 - a0, "float32")
        r = min(int(xfade * SR), (b1 - a0) // 2)
        if r > 1:
            ramp[:r] = np.linspace(0, 1, r)
            ramp[-r:] = np.linspace(1, 0, r)
        out[a0:b1] += bed * (g * ramp)[:, None]
    env = voice_envelope(voice, n)
    duck = 10 ** (-duck_db / 20)
    out *= (1 - (1 - duck) * env)[:, None]
    return out


def render_effects(events: list[dict], total: float, voice: np.ndarray, level_db: float = -12.0) -> np.ndarray:
    n = int(total * SR) + 3 * SR
    out = np.zeros((n, 2), "float32")
    v_rms = _rms(voice) or 0.05
    cache: dict[tuple, np.ndarray] = {}
    for e in events:
        key = (e["id"], e.get("variant", 0))
        if key not in cache:
            cache[key] = catalog.get(e["id"], e.get("variant", 0))
        s = cache[key]
        g = v_rms * 10 ** ((level_db + float(e.get("db", 0))) / 20) / (_rms(s, 0.1) or 1e-6)
        a = int(e["t"] * SR)
        b = min(n, a + len(s))
        if 0 <= a < n:
            out[a:b] += s[: b - a] * g
    return out


def read_voice(path: Path) -> np.ndarray:
    import soundfile as sf
    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        idx = np.linspace(0, len(x) - 1, int(len(x) * SR / sr))
        x = np.interp(idx, np.arange(len(x)), x).astype("float32")
    return x


def build_stems(plan: dict, voice_path: Path, total: float, work: Path, cfg) -> dict[str, Path]:
    voice = read_voice(voice_path)
    stems = {}
    if plan.get("amb"):
        amb = render_ambience(plan["amb"], total, voice, float(cfg.get_path("audio.ambience_db", -22)),
                              float(cfg.get_path("audio.duck_db", 5)))
        stems["ambience"] = catalog.write_wav(work / "ambience.wav", amb)
    if plan.get("sfx"):
        fx = render_effects(plan["sfx"], total, voice, float(cfg.get_path("audio.sfx_db", -12)))
        stems["effects"] = catalog.write_wav(work / "effects.wav", fx)
    return stems
