"""Sound design plan: which ambience bed plays under each scene and which effects land on which words.

Automatic by default, overridable per shot in storyboard.yaml:

  sound:
    amb: rain                  # scene head only: bed for the whole scene ("none" = silence, omit = automatic)
    sfx: [gulp]                # effects for this shot ([] = none, omit = automatic)
    sfx: [{id: gulp, at: drinks, db: -3}]    # at = a word of the shot (the effect lands on it) or seconds from
                                             # the start of the shot; db = level trim

The automatic rules read what the viewer SEES (the scene's picture prompt) and what they HEAR (the shot's words):
a man drinking in the picture gets a gulp, a market scene gets a murmuring crowd, a lab gets a quiet hum.
Effects are rationed (minimum gaps, cooldowns per sound) so the result feels like a documentary, not a cartoon.
"""
from __future__ import annotations

import re
import zlib

from . import catalog

# --------------------------------------------------------------- ambience from the picture (first match wins)
AMB_RULES: list[tuple[str, str]] = [
    (r"\b(clerk|archive|ledger|filing cabinet|case folders?|case files?|banker'?s lamp|anatomical|cut-?away|"
     r"museum plate|encyclopedia plate|diagram|atlas|old map|newspaper clipping|chart)\b", "archive"),
    (r"\b(rain|rainy|storm|thunder|downpour)\b", "rain"),
    (r"\b(ship|boat|deck|caravel|warship|sailing|harbou?r)\b", "ship"),
    (r"\b(sea|ocean|beach|coast|shore|waves|surf)\b", "sea"),
    (r"\b(campfire|bonfire|hearth|fireplace|forge|flames)\b", "fire"),
    (r"\b(stadium|arena|colosseum|amphitheat(re|er)|athletics|running track|race ?track|marathon|spectators|"
     r"fun run)\b", "stadium"),
    (r"\b(battle|battlefield|cannons?|artillery|siege|army camp|war camp)\b", "battle"),
    (r"\b(night|moonlight|moonlit|starry)\b", "night"),
    (r"\b(desert|dunes?|sahara)\b", "desert"),
    (r"\b(mountain|alpine|snowy|snow|blizzard|cliff|summit|mountain pass)\b", "wind"),
    (r"\b(forest|jungle|woods|meadow|savann?a|countryside|garden|grove|orchard|farm|field|riverbank|river|park|"
     r"picnic|hillside|grassy|lawn|trail|terrace|outdoors?)\b", "forest"),
    (r"\b(laborator(y|ies)|lab|microscope|scanner|mri|clinic|hospital|test tubes?|beaker)\b", "lab"),
    (r"\b(gym|gymnasts?|gymnastics|weights?|barbell|dumbbells?|leg press|treadmill|training hall|weightlifting|"
     r"squat rack)\b", "gym"),
    (r"\b(tavern|coffee ?house|pub|inn|feast|banquet|restaurant|party|bar counter)\b", "tavern"),
    (r"\b(office|newsroom|typewriters|bureau|committee|meeting|consultation)\b", "office"),
    (r"\b(market|forum|street|square|town|village|city|crowds?|bazaar|camp|pedestrians?|crossing)\b", "street_old"),
    (r"\b(senate|court(room)?|palace|cathedral|church|monastery|temple|museum|gallery|library|"
     r"lecture hall|university|classroom|council|chamber|hall)\b", "hall"),
    (r"\b(kitchen|living[- ]room|bedroom|sofa|home|house|dining|table|counter|bathroom|waiting room|parlou?r)\b",
     "home"),
    (r"\b(study|desk|studio|workshop|room)\b", "room"),
]
MODERN = (r"\b(modern|today|smartphone|television|tv|cars?|traffic|office|subway|train|pedestrian|skyscrapers?|"
          r"buses|taxi|19[0-9]0s|20[0-9]0s|19[0-9][0-9]|20[0-9][0-9])\b")

# --------------------------------------------------------------- effects: (pattern, sound, source, gap seconds)
# source: "pic" = the scene's picture (lands ~1 s into the scene), "words" = the shot's words (lands on the word)
SFX_RULES: list[tuple[str, str, str, float]] = [
    (r"\b(drinks?|drinking|drank|sipping|gulping|gulps?|swallow(s|ing)?)\b", "gulp", "pic", 25),
    (r"\b(drinks?|drank|gulps?|swallows?)\b", "gulp", "words", 60),
    (r"\b(pour(s|ing|ed)?)\b", "pour", "pic", 25),
    (r"\b(stamp(s|ing|ed)?)\b", "stamp", "pic", 8),
    (r"\b(writing|writes|quill|signing|ink pen|nib)\b", "pen", "pic", 20),
    (r"\b(turning (a |the )?pages?|leafing|flipping through|opening (a |the )?(book|folder|file))\b", "page_turn", "pic", 15),
    (r"\b(coins?|purse|counting money|silver|sesterces)\b", "coins", "pic", 25),
    (r"\b(coins?|paid|pay|fee|dollars?)\b", "coins", "words", 40),
    (r"\b(bells?|ringing)\b", "bell", "pic", 40),
    (r"\b(whistle)\b", "whistle", "pic", 40),
    (r"\b(knock(s|ing)?)\b", "knock", "pic", 30),
    (r"\b(running|sprint(s|ing|er)?|jogging|marathon|racing|runners)\b", "footsteps", "pic", 30),
    (r"\b(cheer(s|ing)?|applause|applauding|roaring crowd)\b", "cheer", "pic", 40),
    (r"\b(cannon(s)? (firing|fire)|explosion|exploding|firing)\b", "boom", "pic", 30),
    (r"\b(swords?|fencing|clash(ing)?|trident|gladiators? (fight|fighting|locked))\b", "sword", "pic", 20),
    (r"\b(splash(ing)?|diving|dives|swimming)\b", "splash", "pic", 30),
    (r"\b(typewriter|typing)\b", "typewriter", "pic", 30),
    (r"\b(camera flash|photograph(ing|er)|taking a photo)\b", "camera", "pic", 30),
    (r"\b(chalk|blackboard)\b", "chalk", "pic", 30),
    (r"\b(gallop(ing)?|horses?|rides past|on horseback)\b", "gallop", "pic", 40),
    (r"\b(heartbeat|beating heart|pulse)\b", "heartbeat", "pic", 40),
    (r"\b(clinking glasses|toast(ing)?|glass(es)? clink)\b", "glass", "pic", 30),
    (r"\b(drip(ping|s)?|droplet|drop of water)\b", "drip", "pic", 20),
    (r"\b(door (opens|opening|slams)|opening a door)\b", "door", "pic", 30),
    (r"\b(drawer)\b", "drawer", "pic", 30),
    (r"\b(clock|stopwatch|ticking)\b", "tick", "pic", 30),
]

# brand cues: the factory's own sound language (overridable in channel.yaml → sound)
DEFAULT_BRAND = {
    "transition": "whoosh",        # a new paragraph opens on a new picture (at most every `transition_gap` s)
    "transition_gap": 20.0,
    "chart": "pop",                # a chart grows in
    "case_file": "paper",          # the shot that says "case file ..."
    "verdict": "stamp",            # the shot that starts with "Verdict"
    "default_amb": "room",         # scenes no rule matches
    "clerk_amb": "archive",
}
MIN_GAP = 1.2                       # seconds between any two effects
FIRST_EFFECT_AFTER = 0.6            # into a scene, for picture-based effects


def _text_of(visual) -> str:
    if isinstance(visual, dict):
        return str(visual.get("prompt") or "")
    return str(visual or "")


def _pick_amb(head: dict, brand: dict) -> str:
    v = head.get("visual")
    pic = _text_of(v).lower()
    if isinstance(v, dict) and "clerk" in (v.get("characters") or []):
        return brand["clerk_amb"]
    best = None                                # the setting named first in the prompt wins ("A newsroom ... park")
    for k, (pat, sid) in enumerate(AMB_RULES):
        m = re.search(pat, pic)
        if m and (best is None or (m.start(), k) < best[0]):
            best = ((m.start(), k), sid)
    if best:
        sid = best[1]
        if sid == "street_old" and re.search(MODERN, pic):
            return "city"
        return sid
    if isinstance(v, dict) and ("props" in v or "bg" in v) and "prompt" not in v:
        return brand["clerk_amb"]             # charts are drawn on Mortimer's desk / paper
    return brand["default_amb"]


def _seed(*parts) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode()) % catalog.VARIANTS


def _word_time(shot: dict, t0: float, t1: float, word: str) -> float | None:
    text = shot.get("text") or ""
    m = re.search(rf"\b{re.escape(word)}", text, re.I) if word else None
    if not m:
        return None
    return t0 + (t1 - t0) * (m.start() / max(1, len(text)))


def plan(groups: list[list[dict]], timing: list[dict], brand: dict | None = None,
         amb_on: bool = True, sfx_on: bool = True, end: float | None = None) -> dict:
    """→ {"amb": [{t0, t1, id}], "sfx": [{t, id, db, variant, why}]} for a whole video."""
    brand = {**DEFAULT_BRAND, **(brand or {})}
    cat = catalog.load_catalog()
    tm = {t["id"]: t for t in timing}
    amb, events = [], []
    last_by_id: dict[str, float] = {}
    last_any = -99.0
    last_transition = -brand["transition_gap"]

    def add(t: float, sid: str, why: str, db: float = 0.0, gap: float = 0.0, force: bool = False) -> bool:
        nonlocal last_any
        if not sid or sid == "none" or not catalog.known(sid, cat):
            return False
        if not force:
            if t - last_any < MIN_GAP or t - last_by_id.get(sid, -1e9) < gap:
                return False
        events.append({"t": round(max(0.0, t), 3), "id": sid, "db": db, "variant": _seed(sid, round(t, 1)),
                       "why": why})
        last_any, last_by_id[sid] = t, t
        return True

    prev_para = None
    for gi, g in enumerate(groups):
        head = g[0]
        if head["id"] not in tm:
            continue
        t0 = tm[head["id"]]["start"]
        t1 = tm[g[-1]["id"]]["end"] if g[-1]["id"] in tm else t0
        snd = head.get("sound") or {}
        # ---- ambience bed
        if amb_on:
            sid = snd.get("amb") if isinstance(snd, dict) and "amb" in snd else _pick_amb(head, brand)
            if amb and amb[-1]["id"] == sid and abs(amb[-1]["t1"] - t0) < 0.5:
                amb[-1]["t1"] = t1
            else:
                amb.append({"t0": t0, "t1": t1, "id": sid or "none"})
        if not sfx_on:
            continue
        # ---- brand cues at the scene start
        v = head.get("visual")
        is_chart = isinstance(v, dict) and "props" in v and "prompt" not in v
        if is_chart:
            add(t0 + 0.04, brand["chart"], "chart", -2, 0, force=True)
        elif (gi and head.get("para") != prev_para and t0 - last_transition >= brand["transition_gap"]
              and not re.search(r"\bcase file\b|^\s*verdict\b", head.get("text") or "", re.I)):
            if add(t0 - 0.2, brand["transition"], "paragraph", -4):
                last_transition = t0
        prev_para = head.get("para")
        # ---- picture-based effects (once per scene)
        pic = _text_of(v).lower()
        explicit_head = isinstance(snd, dict) and "sfx" in snd
        brand_head = re.search(r"\bcase file\b|^\s*verdict\b", head.get("text") or "", re.I)
        if pic and not explicit_head and not brand_head:
            for pat, sid, src, gap in SFX_RULES:
                if src == "pic" and re.search(pat, pic):
                    if add(t0 + FIRST_EFFECT_AFTER, sid, f"picture: {sid}", 0, gap):
                        break
        # ---- shot-level: explicit lists, brand words, word rules
        for s in g:
            if s["id"] not in tm:
                continue
            s0, s1 = tm[s["id"]]["start"], tm[s["id"]]["end"]
            ss = s.get("sound") or {}
            if isinstance(ss, dict) and "sfx" in ss:
                for item in ss.get("sfx") or []:
                    item = {"id": item} if isinstance(item, str) else dict(item)
                    at = item.get("at", 0)
                    t = _word_time(s, s0, s1, at) if isinstance(at, str) else s0 + float(at or 0)
                    add(t if t is not None else s0, item.get("id"), "storyboard", float(item.get("db", 0)), force=True)
                continue
            text = s.get("text") or ""
            if re.match(r"\s*verdict\b", text, re.I):
                t = _word_time(s, s0, s1, "wrong") or _word_time(s, s0, s1, "right") or (s0 + s1) / 2
                add(t, brand["verdict"], "verdict", 2, force=True)
                continue
            if re.search(r"\bcase file\b", text, re.I):
                add(s0 + 0.1, brand["case_file"], "case file", -2, force=True)
                continue
            for pat, sid, src, gap in SFX_RULES:
                if src != "words":
                    continue
                m = re.search(pat, text, re.I)
                if m:
                    t = s0 + (s1 - s0) * (m.start() / max(1, len(text)))
                    if add(t, sid, f"word: {m.group(0)}", -2, gap):
                        break
    if amb and end and end > amb[-1]["t1"]:
        amb[-1]["t1"] = end
    events.sort(key=lambda e: e["t"])
    return {"amb": amb, "sfx": events}


def music_plan(groups: list[list[dict]], timing: list[dict], tracks: list[str], chapters: dict | None = None,
               end: float | None = None, min_len: float = 60.0) -> list[dict]:
    """Music changes with the story: a new track at chapter starts (project.yaml chapters, paragraph index → label),
    never sooner than `min_len` seconds, and a moment of silence before the verdict lands."""
    if not tracks or not timing:
        return []
    tm = {t["id"]: t for t in timing}
    para_start: dict[int, float] = {}
    verdicts = []
    for g in groups:
        for s in g:
            if s["id"] in tm:
                para_start.setdefault(int(s.get("para", 0)), tm[s["id"]]["start"])
                if re.match(r"\s*verdict\b", s.get("text") or "", re.I):
                    verdicts.append((tm[s["id"]]["start"], tm[s["id"]]["end"]))
    cuts = sorted({para_start[int(k)] for k in (chapters or {}) if int(k) in para_start} | {0.0})
    starts = []
    for c in cuts:
        if not starts or c - starts[-1] >= min_len:
            starts.append(c)
    stop = end or max(t["end"] for t in timing)
    segs = [{"t0": a, "t1": (starts[i + 1] if i + 1 < len(starts) else stop), "track": tracks[i % len(tracks)]}
            for i, a in enumerate(starts)]
    out = []
    for sg in segs:                               # carve out the silence before each verdict
        pieces = [sg]
        for v0, v1 in verdicts:
            nxt = []
            for pc in pieces:
                a, b = v0 - 1.5, v1 + 0.6
                if b <= pc["t0"] or a >= pc["t1"]:
                    nxt.append(pc)
                    continue
                if a > pc["t0"]:
                    nxt.append({**pc, "t1": a})
                if b < pc["t1"]:
                    nxt.append({**pc, "t0": b})
            pieces = nxt
        out += [pc for pc in pieces if pc["t1"] - pc["t0"] > 1.0]
    return out


def summary(p: dict, scenes: int) -> dict:
    beds = [a for a in p["amb"] if a["id"] != "none"]
    covered = sum(a["t1"] - a["t0"] for a in beds)
    total = (p["amb"][-1]["t1"] - p["amb"][0]["t0"]) if p["amb"] else 0.0
    minutes = max(total / 60, 1e-9)
    return {"amb_coverage": covered / total if total else 0.0, "amb_kinds": sorted({a["id"] for a in beds}),
            "sfx_count": len(p["sfx"]), "sfx_per_min": len(p["sfx"]) / minutes, "scenes": scenes}
