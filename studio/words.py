"""Word-level timing: when each spoken word of a shot is said.

`align` stores per-word times in timing.json (`words: [[word, seconds], ...]`) when it knows them — from the voice
provider's character times (ElevenLabs, estimate) or from faster-whisper's word timestamps. Without them the time
inside a shot is split by character weight (punctuation counts as a pause), the same rule the shot timing uses.

Motion scenes use it to put a movement on a word: in a `mech` scene a key with `at: "@valve"` starts when "valve" is
said (`@valve#2` = the second time inside the scene, `@valve+0.3` = 0.3 s later). Sound effects use it too.
"""
from __future__ import annotations

import re

_TOKEN = re.compile(r"[A-Za-z0-9']+")   # same split as the whisper aligner (hyphens and dots split words)
_NORM = re.compile(r"[^a-z0-9']+")
CUE = re.compile(r"^\s*@([^+\-#\s][^+\-#]*?)(?:#(\d+))?\s*(?:[+-]\s*\d+(?:\.\d+)?)?\s*$")


def norm(word: str) -> str:
    return _NORM.sub("", word.lower().replace("’", "'"))


def tokens(text: str) -> list[tuple[str, int]]:
    """[(normalised word, character offset)] of a shot's spoken text (delivery tags like [pause] removed)."""
    clean = re.sub(r"\[[a-z ]+\]", lambda m: " " * len(m.group(0)), text or "")
    out = []
    for m in _TOKEN.finditer(clean):
        w = norm(m.group(0))
        if w:
            out.append((w, m.start()))
    return out


def _weight(s: str) -> float:
    w = len(s)
    w += 4 * sum(s.count(c) for c in ",;:")
    w += 6 * sum(s.count(c) for c in ".!?—")
    return max(w, 1)


def shot_words(shot: dict, entry: dict) -> list[tuple[str, float]]:
    """[(word, seconds)] for one shot: the stored word times when align knew them, else split by character weight."""
    text = shot.get("text") or ""
    toks = tokens(text)
    t0 = float(entry.get("start", 0.0))
    t1 = float(entry.get("end", t0 + max(1.0, len(text) / 15)))
    stored = entry.get("words")
    if isinstance(stored, list) and len(stored) == len(toks) and all(isinstance(x, (list, tuple)) and len(x) == 2 for x in stored):
        return [(w, float(t)) for (w, _), (_, t) in zip(toks, stored)]
    if not toks:
        return []
    total = _weight(text)
    return [(w, t0 + (t1 - t0) * _weight(text[:off]) / total if off else t0) for w, off in toks]


def _match(token: str, word: str) -> bool:
    if word.endswith("*"):
        return token.startswith(word[:-1])
    return token == word or token == word + "s" or token == word + "es" or token.rstrip("'s") == word


def find(shots: list[dict], timing: dict[str, dict], word: str, nth: int = 1) -> float | None:
    """Seconds when `word` is said the nth time across these shots (in order), or None."""
    w = norm(word.rstrip("*")) + ("*" if word.endswith("*") else "")
    if not w.strip("*"):
        return None
    seen = 0
    for s in shots:
        e = timing.get(s["id"])
        if not e:
            continue
        for tok, t in shot_words(s, e):
            if _match(tok, w):
                seen += 1
                if seen == nth:
                    return t
    return None


def cue_keys(obj) -> set[str]:
    """Every "@word" cue string inside a motion visual (props are walked recursively)."""
    found: set[str] = set()

    def walk(v):
        if isinstance(v, str):
            m = CUE.match(v)
            if m and v.strip().startswith("@"):
                found.add(base_key(v))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(obj)
    return found


def base_key(cue: str) -> str:
    """"@Valve#2+0.3" → "@valve#2": the cue without its offset, lower case (the component looks it up like this)."""
    head = re.split(r"[+-]\s*\d", cue.strip(), maxsplit=1)[0]
    return re.sub(r"\s+", "", head).lower()


def cue_table(group: list[dict], timing: dict[str, dict], fps: int, keys: set[str]) -> tuple[dict[str, int], list[str]]:
    """{"@valve": frame from the scene start} for a scene's word cues, and the cues whose word is never said."""
    if not group or not keys:
        return {}, []
    start = float(timing[group[0]["id"]]["start"])
    table, missing = {}, []
    for k in sorted(keys):
        m = re.match(r"^@(.+?)(?:#(\d+))?$", k)  # "@valve" | "@valve#2" | "@spring*"
        if not m:
            continue
        t = find(group, timing, m.group(1), int(m.group(2) or 1))
        if t is None:
            missing.append(k)
            continue
        table[k] = max(0, round((t - start) * fps))
    return table, missing


def nominal_timing(group: list[dict], seconds_per_char: float = 1 / 15) -> dict[str, dict]:
    """Timing for shots that have no voice yet (posters, previews): about 15 characters per second."""
    out, t = {}, 0.0
    for s in group:
        d = max(0.8, len(s.get("text") or "") * seconds_per_char)
        out[s["id"]] = {"start": t, "end": t + d}
        t += d
    return out
