"""Splits a narration script into short 'beats'. Each beat gets one image (~1-2.5 s on screen).

Rules
- Never cut inside a word; prefer cutting at punctuation, then before a joining word.
- Pieces stay between min_chars and max_chars where the sentence allows it.
- Decimals ("99.9%"), money ("$3.50") and common abbreviations do not end a sentence.
- Delivery tags for expressive voices (ElevenLabs v3), e.g. "[curious] Why do we sweat?", are taken out of the
  text (captions, translation and claims never see them) and kept on the beat as `tone: [curious]`.
"""
from __future__ import annotations

import re

ABBREV = {"dr", "mr", "mrs", "ms", "prof", "st", "vs", "etc", "e.g", "i.e", "approx", "no", "fig"}
JOINERS = {
    "and", "but", "or", "because", "which", "that", "who", "while", "when", "before", "after",
    "so", "yet", "than", "until", "unless", "although", "though", "where", "if", "as",
    "with", "without", "for", "to", "into", "from", "of", "in", "on", "by", "about", "also", "then",
}
TONE_TAG = re.compile(r"\[([a-z][a-z \-]{0,30})\]", re.I)
PUNCT_BREAK = re.compile(r"(?<=[,;:—])\s+|\s+(?=[—–-]\s)")


def paragraphs(script: str) -> list[str]:
    """Blank-line separated paragraphs; markdown headings and comments are ignored."""
    out = []
    script = re.sub(r"<!--[\s\S]*?-->", "", script)       # comments may span several lines
    for block in re.split(r"\n\s*\n", script.strip()):
        lines = [ln for ln in block.splitlines()
                 if ln.strip() and not ln.lstrip().startswith(("#", "<!--", "//"))]
        text = " ".join(ln.strip() for ln in lines)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append(text)
    return out


def sentences(paragraph: str) -> list[str]:
    tokens = re.split(r"(?<=[.!?])\s+", paragraph)
    out: list[str] = []
    buf = ""
    for tok in tokens:
        buf = f"{buf} {tok}".strip() if buf else tok
        last = buf.split()[-1].rstrip(".!?").lower() if buf.split() else ""
        if last in ABBREV:
            continue
        out.append(buf)
        buf = ""
    if buf:
        out.append(buf)
    return out


def _split_words(text: str, max_chars: int) -> list[str]:
    """Split an over-long clause at the word boundary closest to the middle,
    preferring to start the second half with a joining word."""
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    best, best_score = None, None
    total = len(text)
    pos = 0
    for i in range(1, len(words)):
        pos += len(words[i - 1]) + 1
        left, right = pos - 1, total - pos
        if left < 12 or right < 12:
            continue
        score = abs(left - right)
        if words[i].lower().strip(",;:") in JOINERS:
            score -= 24
        if best_score is None or score < best_score:
            best, best_score = i, score
    if best is None:
        return [text]
    a, b = " ".join(words[:best]), " ".join(words[best:])
    return _split_words(a, max_chars) + _split_words(b, max_chars)


def beats_for_sentence(sentence: str, min_chars: int = 20, max_chars: int = 65) -> list[str]:
    if len(sentence) <= max_chars:
        return [sentence]
    clauses = [c for c in PUNCT_BREAK.split(sentence) if c.strip()]
    pieces: list[str] = []
    for clause in clauses:
        pieces.extend(_split_words(clause.strip(), max_chars))
    # greedy re-join of neighbours while under max
    merged: list[str] = []
    for p in pieces:
        if merged and len(merged[-1]) + 1 + len(p) <= max_chars and (
            len(merged[-1]) < min_chars or len(p) < min_chars
        ):
            merged[-1] = f"{merged[-1]} {p}"
        else:
            merged.append(p)
    # a tail that is still too short joins its left neighbour
    if len(merged) > 1 and len(merged[-1]) < min_chars:
        tail = merged.pop()
        merged[-1] = f"{merged[-1]} {tail}"
    return merged


def strip_tones(text: str) -> tuple[str, list[tuple[int, str]]]:
    """'[curious] Why do we sweat?' → ('Why do we sweat?', [(0, 'curious')]). Offsets point into the clean text."""
    clean, tags, pos = "", [], 0
    for m in TONE_TAG.finditer(text):
        clean += text[pos:m.start()]
        clean = re.sub(r"\s+", " ", clean.lstrip()) if not clean.strip() else re.sub(r"\s+", " ", clean)
        tags.append((len(clean.rstrip()) + (1 if clean.rstrip() else 0), m.group(1).strip().lower()))
        pos = m.end()
    clean += text[pos:]
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean, [(min(o, len(clean)), t) for o, t in tags]


def split_script(script: str, min_chars: int = 20, max_chars: int = 65) -> list[dict]:
    """Returns [{'para': i, 'sent': j, 'text': beat, 'tone'?: [tags]}, ...] in reading order."""
    shots = []
    si = 0
    for pi, para in enumerate(paragraphs(script)):
        for sent in sentences(para):
            sent, tags = strip_tones(sent)
            if not sent:
                continue
            cursor = 0
            beats = beats_for_sentence(sent, min_chars, max_chars)
            for bi, beat in enumerate(beats):
                start = sent.find(beat, cursor)
                start = cursor if start < 0 else start
                end = start + len(beat)
                cursor = end
                shot = {"para": pi, "sent": si, "text": beat}
                last = bi == len(beats) - 1
                tone = [t for o, t in tags if start <= o < end or (last and o >= end)]
                if tone:
                    shot["tone"] = tone
                shots.append(shot)
            si += 1
    return shots
