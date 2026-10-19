"""Which scenes of a video are motion scenes (Remotion) instead of paintings — decided the same way in every video of
a channel, so a new video gets them without anyone choosing by hand (docs/REMOTION.md → Rules per channel).

Two kinds:
  signature beats   deterministic, read from the script's fixed structure (channel.yaml → remotion.scenes):
                      cold_open  the opening sentence restates the belief → "BELIEF: …" struck through, the stamp
                                 lands right after that sentence (with the stamp sound)
                      case_file  "Case file zero zero N." + "Subject: …" (+ "Belief: …" when it is on the same
                                 picture) → the typed case-file card
                      verdict    "Verdict: wrong." → belief struck through, stamp on the word, the rest of the
                                 scene written under it
  data scenes       the key numbers, a document quoted word for word, a dated sequence: chosen by the planner (LLM)
                    or by Claude from the claims (`motion-prompt`). Every number they show must appear in a claim
                    linked to the scene's shots, and a quote must be a claim's quote — checked here (`validate_data`),
                    in `apply-plan` and in the quality gate.

Per video: project.yaml → motion: {cold_open: false, case_file: false, verdict: false, belief: "…"}.

  python -m studio motion-plan <slug>      signature beats now (idempotent; also runs after `plan`)
  python -m studio motion-prompt <slug>    data scenes: through planner.provider, or a prompt file for Claude
"""
from __future__ import annotations

import copy
import re

from .config import Config
from .project import Project

DATA_COMPS = ("bars", "counter", "timeline", "quote")
SIGNATURE_COMPS = ("case-file", "verdict")
NOT_NUMBERS = {"beat", "max", "of", "decimals", "seed", "duration", "hit", "hit_beat", "color", "thousands", "highlight"}

DEFAULT_RULES = {"cold_open": True, "case_file": {"org": ""}, "verdict": {"note": True},
                 "data": {"min": 2, "max": 5}}

_DIGIT = {"zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
          "seven": "7", "eight": "8", "nine": "9"}
_WORDNUM = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                       "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
_WORDNUM.update({"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
                 "hundred": 100, "thousand": 1000, "half": 0.5, "dozen": 12})
_ORD = {w: i + 1 for i, w in enumerate("first second third fourth fifth sixth seventh eighth ninth tenth eleventh "
                                       "twelfth thirteenth fourteenth fifteenth sixteenth seventeenth eighteenth "
                                       "nineteenth twentieth".split())}
STOP = set("a an the of to in on at by for and or but is are was were be been it its this that you your we our "
           "they their he his she her with as from into than then so not no do does did must will would can could "
           "about around most all every everyone".split())


# ------------------------------------------------------------------ settings
def rules_for(cfg: Config, project: Project | None = None) -> dict | None:
    """The channel's rules merged with the project's switches; None when the channel uses no motion rules."""
    rm = cfg.get_path("channel.remotion") or {}
    rules = rm.get("scenes")
    if not rules:
        return None
    out = copy.deepcopy(DEFAULT_RULES)
    for k, v in rules.items():
        out[k] = ({**out[k], **v} if isinstance(out.get(k), dict) and isinstance(v, dict) else v)
    mine = (project.meta.get("motion") or {}) if project is not None else {}
    for k in ("cold_open", "case_file", "verdict"):
        if mine.get(k) is False:
            out[k] = False
        elif mine.get(k) is True and not out.get(k):
            out[k] = copy.deepcopy(DEFAULT_RULES[k])
    out["belief"] = mine.get("belief")
    out["force_cold_open"] = mine.get("cold_open") is True
    return out


# ------------------------------------------------------------------ reading the script's structure
def _words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z]+", (text or "").lower()):
        if w in STOP or len(w) < 3 or w in _WORDNUM or w in _ORD:   # numbers alone do not state a belief
            continue
        out.add(w[:-1] if w.endswith("s") and len(w) > 4 else w)
    return out


def _sentence_from(shots: list[dict], i: int, limit: int = 4) -> tuple[str, int]:
    """Text of the sentence starting at shot i (it may run over a few shots) and how many shots it took."""
    parts, n = [], 0
    for s in shots[i:i + limit]:
        parts.append(s["text"].strip())
        n += 1
        if re.search(r"[.?!][\"”']?\s*$", s["text"].strip()):
            break
    return " ".join(parts), n


def _strip(text: str) -> str:
    return re.sub(r"[\s.!?;:,]+$", "", text.strip())


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def find(shots: list[dict], pattern: str, within: int | None = None) -> int | None:
    rx = re.compile(pattern, re.I)
    for i, s in enumerate(shots[: within or len(shots)]):
        if rx.match(s.get("text") or ""):
            return i
    return None


def belief_text(shots: list[dict]) -> str | None:
    """"Belief: you must drink eight glasses of water a day, or …" → "You must drink eight glasses of water a day"."""
    i = find(shots, r"\s*belief\s*:", 60)
    if i is None:
        return None
    text, _ = _sentence_from(shots, i)
    text = re.sub(r"^\s*belief\s*:\s*", "", text, flags=re.I)
    text = re.split(r",\s+(?:or|and so|so that)\s+|;\s+", _strip(text))[0]
    if len(text) > 70 and "," in text:
        text = text.split(",")[0]
    return _cap(_strip(text))


def verdict_word(text: str) -> str:
    """"Verdict: mostly wrong." → "MOSTLY WRONG"; "Verdict: annoyingly, correct." → "CORRECT"."""
    w = _strip(re.sub(r"^\s*verdict\s*:\s*", "", text, flags=re.I))
    w = re.sub(r"^(annoyingly|sadly|alas)\W+", "", w, flags=re.I)
    return w.upper() or "WRONG"


def case_number(text: str) -> str | None:
    """"Case file zero zero one." → "001"; "Case file zero one zero." → "010"."""
    rest = re.sub(r"^\s*case file\s*", "", text, flags=re.I)
    digits = "".join(_DIGIT.get(w, "") for w in re.findall(r"[a-z]+", rest.lower()))
    digits += "".join(re.findall(r"\d", rest))
    return digits or None


# ------------------------------------------------------------------ signature beats
def _heads(shots: list[dict]) -> dict[str, str]:
    from .images import scene_map
    return scene_map(shots)


def _scene_of(shots: list[dict], head_id: str) -> list[dict]:
    heads = _heads(shots)
    return [s for s in shots if heads[s["id"]] == head_id]


def _make_head(shots: list[dict], i: int, visual: dict) -> None:
    s = shots[i]
    s["visual"] = visual
    for k in ("camera", "engine"):
        s.pop(k, None)


def _clear_overlays(scene: list[dict]) -> None:
    for s in scene:
        if (s.get("overlay") or {}).get("kind") in ("label", "stat"):
            s.pop("overlay", None)


def _join(shots: list[dict], i: int) -> None:
    """Shot i continues the previous scene (its own picture is dropped)."""
    shots[i]["visual"] = {"same": True}
    for k in ("camera", "engine"):
        shots[i].pop(k, None)


def signature_plan(project: Project, cfg: Config, shots: list[dict] | None = None) -> tuple[list[dict], list[str]]:
    """Returns the storyboard shots with the signature beats applied (a copy) and a report."""
    rules = rules_for(cfg, project)
    shots = copy.deepcopy(shots if shots is not None else project.load_storyboard()["shots"])
    report: list[str] = []
    if not rules or not shots:
        return shots, report
    belief = rules.get("belief") or belief_text(shots)
    stamp_belief = belief

    # --- cold open: the first sentence of the video restates the belief
    if rules.get("cold_open") and belief:
        first = _scene_of(shots, _heads(shots)[shots[0]["id"]])
        opening, n = _sentence_from(shots, 0)
        b, o = _words(belief), _words(opening)
        overlap = len(b & o)
        ok = rules.get("force_cold_open") or (overlap >= 2 and overlap >= 0.35 * max(1, len(b)))
        if ok and first[0]["id"] == shots[0]["id"]:
            shown = _cap(_strip(opening)) if len(opening) <= 80 else belief
            stamp_belief = shown
            v = {"comp": "verdict", "label": "BELIEF", "word": "WRONG", "belief": shown}
            vi = find(shots, r"\s*verdict\s*:")
            if vi is not None:
                v["word"] = verdict_word(shots[vi]["text"])
            if n < len(first):
                v["hit_beat"] = n
                after = first[n]
                after["sound"] = {"sfx": [{"id": "stamp", "at": re.findall(r"[A-Za-z']+", after["text"])[0]}]}
            else:
                v["hit_beat"] = len(first)                       # = the end of the scene
                last = first[-1]
                last["sound"] = {"sfx": [{"id": "stamp", "at": re.findall(r"[A-Za-z']+", last["text"])[-1]}]}
            _make_head(shots, 0, v)
            _clear_overlays(first)
            report.append(f"açılış: {shots[0]['id']} BELIEF «{shown}» + {v['word']} damgası")
        else:
            report.append(f"açılış: ilk cümle inanışı söylemiyor ({overlap} ortak kelime), resim kalıyor")

    # --- case file card
    ci = find(shots, r"\s*case file\b", 80)
    if rules.get("case_file") and ci is not None:
        num = case_number(shots[ci]["text"]) or "000"
        fields = []
        si = ci + 1 if ci + 1 < len(shots) and re.match(r"\s*subject\s*:", shots[ci + 1]["text"], re.I) else None
        if si is not None:
            if not (shots[si].get("visual") or {}).get("same"):
                _join(shots, si)
            text, _ = _sentence_from(shots, si)
            fields.append({"label": "SUBJECT", "value": _strip(re.sub(r"^\s*subject\s*:\s*", "", text, flags=re.I))})
            bi = find(shots[si + 1: si + 2], r"\s*belief\s*:")
            if bi is not None and (shots[si + 1].get("visual") or {}).get("same"):
                text, _ = _sentence_from(shots, si + 1)
                fields.append({"label": "BELIEF", "value": _strip(re.sub(r"^\s*belief\s*:\s*", "", text, flags=re.I))})
        org = (rules.get("case_file") or {}).get("org") if isinstance(rules.get("case_file"), dict) else ""
        v = {"comp": "case-file", "number": num, **({"org": org} if org else {}), "fields": fields}
        _make_head(shots, ci, v)
        _clear_overlays(_scene_of(shots, shots[ci]["id"]))
        report.append(f"dosya kartı: {shots[ci]['id']} No. {num} ({', '.join(f['label'] for f in fields) or 'alan yok'})")

    # --- verdict
    vi = find(shots, r"\s*verdict\s*:")
    if rules.get("verdict") and vi is not None:
        v = {"comp": "verdict", "word": verdict_word(shots[vi]["text"])}
        if stamp_belief:
            v["belief"] = stamp_belief
        _make_head(shots, vi, v)
        scene = _scene_of(shots, shots[vi]["id"])
        rest = " ".join(s["text"].strip() for s in scene[1:])
        if (rules.get("verdict") or {}).get("note", True) and rest and len(rest) <= 110:
            v["note"] = rest
        _clear_overlays(scene)
        report.append(f"hüküm: {shots[vi]['id']} {v['word']}" + (f" + not «{rest}»" if "note" in v else ""))
    return shots, report


def apply_signature(project: Project, cfg: Config) -> list[str]:
    """Writes the signature beats into the storyboard (unchanged scenes keep their pictures)."""
    from .images import drop_orphans, forget_image
    sb = project.load_storyboard()
    new, report = signature_plan(project, cfg, sb["shots"])
    if not report:
        return report
    old = {s["id"]: s.get("visual") for s in sb["shots"]}
    for s in new:
        if s.get("visual") != old.get(s["id"]):
            forget_image(project, s["id"])
    drop_orphans(new)
    sb["shots"] = new
    project.save_storyboard(sb)
    return report


# ------------------------------------------------------------------ data scenes: numbers must come from claims
def _numbers(text: str, words: bool = False) -> set[float]:
    out = set()
    t = str(text)
    for m in re.findall(r"\d[\d,]*(?:\.\d+)?", t):
        try:
            out.add(float(m.replace(",", "")))
        except ValueError:
            pass
    if words:
        for w in re.findall(r"[a-z]+", t.lower()):
            if w in _WORDNUM:
                out.add(float(_WORDNUM[w]))
            if w in _ORD:
                out.add(float(_ORD[w]))
    return out


def _prop_numbers(v, key: str = "") -> set[float]:
    if key in NOT_NUMBERS:
        return set()
    if isinstance(v, bool):
        return set()
    if isinstance(v, (int, float)):
        return {float(v)}
    if isinstance(v, str):
        return _numbers(v)
    if isinstance(v, dict):
        return set().union(*[_prop_numbers(x, k) for k, x in v.items()]) if v else set()
    if isinstance(v, list):
        return set().union(*[_prop_numbers(x, key) for x in v]) if v else set()
    return set()


def _norm(t: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (t or "").lower()))


def validate_data(project: Project, plan: dict, shots: list[dict] | None = None) -> dict[str, str]:
    """plan: shot id → entry ({visual: {...}} or a bare visual). Returns {shot id: problem} for data scenes that
    fail: unknown component, missing props, a number not in a claim linked to the scene, a quote that is no
    claim's quote. Signature beats and paintings are not checked here."""
    from .claims import load_claims
    from .remotion import comp_of, validate
    shots = shots if shots is not None else project.load_storyboard()["shots"]
    ids = [s["id"] for s in shots]
    claims = load_claims(project)["claims"]
    problems: dict[str, str] = {}
    entries = {k: (e.get("visual") if isinstance(e, dict) and "visual" in e else e) for k, e in plan.items()}
    for sid, v in entries.items():
        c = comp_of(v)
        if c is None or c in SIGNATURE_COMPS:
            continue
        if c not in DATA_COMPS:
            problems[sid] = f"bilinmeyen rakam sahnesi '{c}'"
            continue
        err = validate(v)
        if err:
            problems[sid] = err
            continue
        if sid not in ids:
            problems[sid] = "böyle bir shot yok"
            continue
        # the scene = this shot + the following shots that continue it (in the plan or already in the storyboard)
        i = ids.index(sid)
        scene = [sid]
        for s in shots[i + 1:]:
            nv = entries.get(s["id"], s.get("visual"))
            if isinstance(nv, dict) and nv.get("same"):
                scene.append(s["id"])
            else:
                break
        # a timeline is a recap: its dates may come from any claim of the video; the rest from the scene's claims
        linked = claims if c == "timeline" else [cl for cl in claims if set(cl.get("shots") or []) & set(scene)]
        if not linked:
            problems[sid] = f"sahnenin shot'larına ({scene[0]}–{scene[-1]}) bağlı iddia yok"
            continue
        have = set().union(*[_numbers(f"{cl.get('text', '')} {cl.get('quote', '')}", words=True) for cl in linked])
        missing = sorted(n for n in _prop_numbers({k: x for k, x in v.items() if k != "comp"}) if n not in have)
        if missing:
            problems[sid] = (f"iddiada olmayan sayı: {', '.join(f'{m:g}' for m in missing)} "
                             f"(bağlı iddialar: {', '.join(cl['id'] for cl in linked)})")
            continue
        if c == "quote":
            q = _norm(v.get("text", ""))
            quoted = [cl.get("quote", "") for cl in linked]          # the quote field, or words quoted in the claim
            quoted += [m for cl in linked for m in re.findall(r"[\"“‘']([^\"”’']{12,})[\"”’']", cl.get("text", ""))]
            if not any(q and q in _norm(x) for x in quoted):
                problems[sid] = "alıntı, bağlı iddiaların hiçbirinde kelimesi kelimesine yok"
    return problems


def data_scenes(shots: list[dict]) -> list[str]:
    from .remotion import comp_of
    return [s["id"] for s in shots if comp_of(s.get("visual")) in DATA_COMPS]


# ------------------------------------------------------------------ data scenes: the prompt
DATA_INSTRUCTIONS = """You plan the DATA motion scenes of one video of the YouTube channel "{channel}": code-drawn,
animated scenes (Remotion) for the moments a painting cannot carry — the key numbers, a document quoted word for word,
a dated sequence. Their words are written onto the channel's paper while the shots are read.

Choose {min}–{max} scenes. Rules:
1. Every number you show must be copied from a claim below whose `shots` include the scene's shots. Never round
   or convert. A quote must be a claim's `quote`, word for word. The factory rejects anything else.
2. The scene starts at the shot where the number (or quote) is first said and runs over the next 1–4 shots, which
   you list as `{{visual: {{same: true}}}}`. `beat` = index of the shot inside the scene (0 = first) on which a bar,
   label or event appears, so it lands when its words are read.
3. Prefer the numbers already shown as on-screen text (`overlay`) or as vector charts; a scene with a data scene
   needs no overlay. Do not touch the case file, the verdict or the opening.
4. Short words: titles ≤ 10 words, labels 1–3 words, timeline notes ≤ 8 words.

Components (props):
- bars: {{title, bars: [{{label, value, display?, beat?}}], of? (the whole, e.g. 100), max?, unit? ("%", " L"), note?}}
- counter: {{value, label?, note?, prefix?, suffix?, decimals?}}   (label on shot 1, note on shot 2 of the scene)
- timeline: {{events: [{{when, text, beat?, highlight?}}], title?}}  (2–5 events)
- quote: {{text, source?, highlight?}}

Reply with ONLY a YAML mapping from shot id to entry, for example:
s065:
  visual: {{comp: bars, title: "Plain water, as a share of all water", of: 100, unit: "%",
           bars: [{{label: Men, value: 30, beat: 1}}, {{label: Women, value: 34, beat: 2}}]}}
s066:
  visual: {{same: true}}
"""


def build_data_prompt(project: Project, cfg: Config) -> str:
    from .claims import load_claims
    from .remotion import comp_of
    rules = rules_for(cfg, project) or DEFAULT_RULES
    d = rules.get("data") or {}
    shots = project.load_storyboard()["shots"]
    lines = [DATA_INSTRUCTIONS.format(channel=cfg.get_path("channel.name", project.channel),
                                      min=d.get("min", 2), max=d.get("max", 5)), "## Claims"]
    for c in load_claims(project)["claims"]:
        q = f' quote: "{c["quote"]}"' if c.get("quote") else ""
        lines.append(f"- {c['id']} shots {','.join(c.get('shots') or [])}: {c.get('text', '')}{q}")
    lines += ["", "## Narration (shot id, what is on screen now)"]
    for s in shots:
        v = s.get("visual") or {}
        kind = ("continues" if v.get("same") else f"motion:{comp_of(v)}" if comp_of(v) else
                "chart" if "props" in v else "painting")
        ov = f" overlay: {s['overlay'].get('text')}" if s.get("overlay") else ""
        lines.append(f"[{s['id']}] ({kind}{ov}) {s['text']}")
    return "\n".join(lines)


def run_data(project: Project, cfg: Config) -> str:
    """Data scenes through planner.provider (gemini/anthropic: planned and applied, invalid entries skipped;
    manual: build/motion_prompt.md for Claude, the answer goes into 'Planı uygula')."""
    provider = cfg.get_path("planner.provider", "gemini")
    prompt = build_data_prompt(project, cfg)
    if provider == "manual":
        out = project.build / "motion_prompt.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(prompt, encoding="utf-8")
        return f"istem hazır: {out} — Claude'a yapıştır, gelen YAML'ı panelde 'Planı uygula' kutusuna yapıştır"
    from .llm import complete
    from .planner import apply_plan, parse_yaml_reply
    model = cfg.get_path(f"planner.{provider}.model")
    reply = parse_yaml_reply(complete(prompt, model, provider=provider))
    n = apply_plan(project, reply)
    return f"{n} giriş uygulandı"
