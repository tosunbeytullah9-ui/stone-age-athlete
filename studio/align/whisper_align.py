"""Optional word-level alignment with faster-whisper (pip install faster-whisper)."""
from __future__ import annotations

import difflib
import re

from ..project import Project

_norm = re.compile(r"[^a-z0-9']+")


def _words(text: str) -> list[str]:
    return [w for w in _norm.sub(" ", text.lower()).split() if w]


class WhisperAligner:
    def __init__(self, cfg):
        from faster_whisper import WhisperModel
        name = cfg.get_path("align.whisper.model", "base.en")
        self.model = WhisperModel(name, device="auto", compute_type="int8")

    @classmethod
    def try_create(cls, cfg, required: bool = False):
        try:
            return cls(cfg)
        except ImportError:
            if required:
                raise SystemExit("faster-whisper kurulu değil: pip install faster-whisper")
            return None

    def align_unit(self, project: Project, u: dict, lang: str = "en") -> list[float]:
        segments, _ = self.model.transcribe(str(project.dir / u["file"]), word_timestamps=True,
                                            language=lang, vad_filter=False)
        heard: list[tuple[str, float]] = []
        for seg in segments:
            for w in seg.words or []:
                for token in _words(w.word):
                    heard.append((token, w.start))

        # script words, remembering which shot each belongs to
        script: list[tuple[str, int]] = []
        for si, s in enumerate(u["spans"]):
            for token in _words(u["text"][s["start"]:s["end"]]):
                script.append((token, si))

        sm = difflib.SequenceMatcher(a=[w for w, _ in script], b=[w for w, _ in heard], autojunk=False)
        time_of: dict[int, float] = {}
        for a, b, n in sm.get_matching_blocks():
            for k in range(n):
                time_of[a + k] = heard[b + k][1]

        starts: list[float] = []
        for si in range(len(u["spans"])):
            idxs = [i for i, (_, owner) in enumerate(script) if owner == si]
            t = next((time_of[i] for i in idxs if i in time_of), None)
            if t is None:  # not heard: interpolate from neighbours later
                starts.append(float("nan"))
            else:
                starts.append(u["offset"] + t)
        # fill gaps linearly
        for i, t in enumerate(starts):
            if t != t:  # NaN
                prev = starts[i - 1] if i > 0 else u["offset"]
                nxt = next((x for x in starts[i + 1:] if x == x), u["offset"] + u["duration"])
                starts[i] = (prev + nxt) / 2
        return starts
