"""Thumbnails + titles ("packaging"). Rules and the three kinds: docs/THUMBNAILS.md.

project.yaml (the three kinds, look from channel.yaml → thumbnails, drawn by studio/thumbkit.py):
  thumbnails:
    - kind: correction              # the belief struck through + a handwritten note
      visual: {prompt: "...", characters: []}
      myth: {en: "8 GLASSES"}       # ≤ 3 short words or one number
      note: {en: "half a sentence?"}   # ≤ 3 words
      pos: top-left                 # top-left | top | top-right | left | right | bottom-left | bottom
      claim: c03                    # the claim a number/fact on the thumbnail rests on
    - kind: stamp                   # one object + a rubber stamp (channel default word, or stamp: {en: "MYTH"})
    - kind: scene                   # a moment from the video + text ≤ 3 words

Older entries without `kind` keep the classic look:
  thumbnails:                       # up to 3 variants → YouTube "Test & Compare" (winner by watch time)
    - visual: {prompt: "...", characters: [coach]}   # same format as a scene (docs/STORYBOARD.md)
      frame: {x: 900, y: 560, zoom: 1.3}   # optional extra close-up (1920×1080 coordinates)
      text: {en: "BIGGER SPLEENS", tr: "DEV DALAK"}   # ≤ 4 words; thumbnails MAY contain text (shots may not)
      text_pos: left                # left | right | top | bottom
      text_color: "#ffd84d"         # default yellow; white also works
      highlight: {x: 1100, y: 520, r: 140}   # optional red circle around the key detail (drawing coordinates)

Renders build/thumbnails/<lang>/thumb1.png … (1280×720 JPEG-safe PNG) and preview.png that shows every variant at
YouTube's desktop and phone sizes, because a thumbnail is judged at ~168 px wide on a phone.
The paintings are cached in build/thumbnails/raw/ by prompt, so changing only the text costs nothing.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import Config
from .project import Project

TW, TH = 1280, 720
FONT_CANDIDATES = [
    "ariblk.ttf", "Arial Black.ttf", "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/impact.ttf",
    "/System/Library/Fonts/Supplemental/Arial Black.ttf", "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/Library/Fonts/Arial Black.ttf", "impact.ttf", "Impact.ttf",
    "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arialbd.ttf",
    str(Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Anton-Regular.ttf"),
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _text_for(v: dict, lang: str, primary: str) -> str:
    t = v.get("text") or ""
    if isinstance(t, dict):
        t = t.get(lang) or (t.get(primary) if lang == primary else "") or ""
    return str(t).strip()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for w in words:
        test = f"{line} {w}".strip()
        if draw.textlength(test, font=font) > max_w and line:
            lines.append(line)
            line = w
        else:
            line = test
    if line:
        lines.append(line)
    return lines


def compose(base: Image.Image, text: str, pos: str = "left", color: str = "#ffd84d",
            highlight: dict | None = None, frame: dict | None = None) -> Image.Image:
    img = base.convert("RGB").resize((TW, TH), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    if highlight:
        zoom = float((frame or {}).get("zoom", 1) or 1)
        vw, vh = 1920 / zoom, 1080 / zoom
        fx, fy = float((frame or {}).get("x", 960)), float((frame or {}).get("y", 540))
        x0 = min(max(fx - vw / 2, 0), 1920 - vw) if zoom > 1 else 0
        y0 = min(max(fy - vh / 2, 0), 1080 - vh) if zoom > 1 else 0
        sx, sy = TW / vw, TH / vh
        cx, cy = (float(highlight["x"]) - x0) * sx, (float(highlight["y"]) - y0) * sy
        r = float(highlight.get("r", 120)) * sx
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#e0302a", width=14)
    if not text:
        return img
    text = text.upper()
    horizontal = pos in ("left", "right")
    box_w = int(TW * (0.48 if horizontal else 0.9))
    size = 150
    while size > 48:
        font = _font(size)
        lines = _wrap(d, text, font, box_w)
        line_h = int(size * 1.05)
        if len(lines) <= 3 and max(d.textlength(ln, font=font) for ln in lines) <= box_w and len(lines) * line_h <= TH * 0.8:
            break
        size -= 8
    block_h = len(lines) * line_h
    if pos == "right":
        x, anchor, y = TW - 40, "ra", (TH - block_h) // 2
    elif pos == "top":
        x, anchor, y = TW // 2, "ma", 30
    elif pos == "bottom":
        x, anchor, y = TW // 2, "ma", TH - block_h - 40
    else:
        x, anchor, y = 40, "la", (TH - block_h) // 2
    stroke = max(6, size // 11)
    for ln in lines:
        d.text((x + 6, y + 8), ln, font=font, fill="#000000", anchor=anchor, stroke_width=stroke, stroke_fill="#000000")
        d.text((x, y), ln, font=font, fill=color, anchor=anchor, stroke_width=stroke, stroke_fill="#111111")
        y += line_h
    return img


THUMB_DIRECTION = ("YouTube thumbnail painting: one bold subject, close and large, strong contrast and saturated "
                   "light, an expressive face if a person is shown, simple uncluttered background, and clear empty "
                   "space on the {side} side of the frame for a big title.")
KIND_SPACE = {        # what the picture must leave free for the words the factory prints on it
    "correction": "Leave the {area} of the frame completely empty (plain background, nothing drawn there) for a "
                  "big handwritten line.",
    "stamp": "Leave a large completely empty area in the {area} of the frame (plain background, nothing drawn there) "
             "for a rubber stamp.",
    "scene": "Leave the {area} of the frame completely empty (plain background) for three handwritten words.",
}
AREA = {"top-left": "upper left", "top": "top third", "top-right": "upper right", "left": "left half",
        "right": "right half", "bottom-left": "lower left", "bottom": "bottom third"}
KIND_DIRECTION = ("Thumbnail picture: one subject drawn large and close, filling about half of the frame, bold clear "
                  "shapes that still read when the picture is shown very small, nothing else competing with it.")


def _direction(v: dict, ch: dict) -> str:
    kind = v.get("kind")
    custom = ((ch or {}).get("thumbnails") or {}).get("direction")
    if kind in KIND_SPACE:
        pos = v.get("pos") or ("top" if kind == "scene" else "top-left")
        return f"{custom or KIND_DIRECTION} {KIND_SPACE[kind].format(area=AREA.get(pos, 'upper left'))}"
    side = {"left": "left", "right": "right", "top": "top", "bottom": "bottom"}.get(v.get("text_pos", "left"), "left")
    return custom.format(side=side) if custom and "{side}" in custom else THUMB_DIRECTION.format(side=side)


def _field(v: dict, key: str, lang: str, primary: str) -> str:
    t = v.get(key) or ""
    if isinstance(t, dict):
        t = t.get(lang) or (t.get(primary) if lang == primary else "") or ""
    return str(t).strip()


def _frame_crop(img: Image.Image, frame: dict | None) -> Image.Image:
    zoom = float((frame or {}).get("zoom", 1) or 1)
    if zoom <= 1:
        return img
    W, H = img.size
    vw, vh = W / zoom, H / zoom
    fx, fy = float(frame.get("x", W / 2)) * W / 1920, float(frame.get("y", H / 2)) * H / 1080
    x0, y0 = min(max(fx - vw / 2, 0), W - vw), min(max(fy - vh / 2, 0), H - vh)
    return img.crop((round(x0), round(y0), round(x0 + vw), round(y0 + vh))).resize((W, H), Image.LANCZOS)


def _series_color(project: Project) -> str | None:
    from .publish import get_publish
    sid = get_publish(project).get("series") or ""
    return ((project.ch.data.get("series") or {}).get(sid) or {}).get("color")


def render_thumbnails(project: Project, cfg: Config, lang: str | None = None) -> list[Path]:
    from . import thumbkit
    from .images.gemini_engine import GeminiEngine
    from .images.style_prompt import build_prompt
    variants = project.meta.get("thumbnails") or []
    if not variants:
        raise SystemExit("project.yaml → thumbnails boş. Panel: Kapak & başlık → 'Paket istemini kopyala'.")
    primary = project.primary_lang()
    langs = [lang] if lang else project.ch.languages
    ch = project.ch.data
    theme = thumbkit.theme_of(ch)
    color = _series_color(project)
    out_dir = project.build / "thumbnails"
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    made: list[Path] = []
    eng = None
    for n, v in enumerate(variants[:3], 1):
        visual = v.get("visual")
        if isinstance(visual, str):
            visual = {"prompt": visual}
        from . import remotion
        if isinstance(visual, dict) and remotion.comp_of(visual):
            # drawn by code (Remotion), e.g. `comp: mech`: free, exact, the same look as the video
            raw = raw_dir / f"thumb{n}_code_{remotion.still_key(visual, cfg)}.png"
            if not raw.exists() and not remotion.render_still(project, cfg, visual, raw):
                print(f"  kapak {n}: kodla çizilen resim üretilemedi, atlandı")
                continue
        elif not isinstance(visual, dict) or not visual.get("prompt"):
            print(f"  kapak {n}: visual.prompt yok, atlandı")
            continue
        else:
            scene = {**visual, "prompt": f"{_direction(v, ch)} {visual['prompt']}"}
            eng = eng or GeminiEngine(cfg)
            prompt = build_prompt(scene, eng.style, eng.characters)
            key = hashlib.sha1(json.dumps([prompt, eng.model], ensure_ascii=False).encode()).hexdigest()[:10]
            raw = raw_dir / f"thumb{n}_{key}.png"
            if not raw.exists():
                eng.generate(prompt, raw, eng.char_refs(visual.get("characters")))
        base = _frame_crop(Image.open(raw).convert("RGB"), v.get("frame"))
        for lg in langs:
            if v.get("kind") in thumbkit.KINDS:
                texts = {k: _field(v, k, lg, primary) for k in ("myth", "note", "stamp", "text")}
                for w in thumbkit.lint(v, texts):
                    print(f"  uyarı kapak {n} ({v['kind']}): {w}")
                img = thumbkit.compose_kind(base, v, texts, theme, color)
            else:
                img = compose(base, _text_for(v, lg, primary), v.get("text_pos", "left"),
                              v.get("text_color", "#ffd84d"), v.get("highlight"), None)
            d = out_dir / lg
            d.mkdir(parents=True, exist_ok=True)
            out = d / f"thumb{n}.png"
            img.save(out, optimize=True)
            made.append(out)
    for lg in langs:
        preview(project, lg)
    print(f"  {len(made)} kapak görseli hazır: {out_dir}")
    return made


def preview(project: Project, lang: str) -> Path | None:
    """Every variant as the feed shows it: phone home feed (full width) and sidebar/search (168 px), light and dark."""
    d = project.build / "thumbnails" / lang
    thumbs = sorted(d.glob("thumb[0-9].png"))
    if not thumbs:
        return None
    from .render import _font as small_font
    variants = project.meta.get("thumbnails") or []
    kinds = [(variants[i] if i < len(variants) and isinstance(variants[i], dict) else {}).get("kind", "")
             for i in range(len(thumbs))]
    names = {"correction": "Düzeltme", "stamp": "Damga", "scene": "Sahne"}
    title = project.meta.get("title", project.slug)
    channel = project.ch.data.get("name", project.channel)
    col_w, half = 470, 490
    W, H = 40 + len(thumbs) * col_w, 2 * half
    sheet = Image.new("RGB", (W, H), "#ffffff")
    dr = ImageDraw.Draw(sheet)
    dr.rectangle([0, half, W, H], fill="#0f0f0f")
    lf, tf = small_font(18), small_font(16)
    for i, t in enumerate(thumbs):
        img = Image.open(t).convert("RGB")
        x = 40 + i * col_w
        label = f"{chr(65 + i)}" + (f" · {names.get(kinds[i], kinds[i])}" if kinds[i] else "")
        for k, (fg, mode) in enumerate((("#0f0f0f", "açık tema"), ("#f1f1f1", "koyu tema"))):
            y0 = k * half + 18
            dr.text((x, y0), f"{label} · {mode}", fill="#888888", font=lf)
            sheet.paste(img.resize((420, 236), Image.LANCZOS), (x, y0 + 30))
            for j, ln in enumerate(_wrap(dr, title, tf, 420)[:2]):
                dr.text((x, y0 + 274 + j * 20), ln, fill=fg, font=tf)
            sheet.paste(img.resize((168, 94), Image.LANCZOS), (x, y0 + 330))
            for j, ln in enumerate(_wrap(dr, title, tf, 240)[:2]):
                dr.text((x + 180, y0 + 332 + j * 20), ln, fill=fg, font=tf)
            dr.text((x + 180, y0 + 376), f"{channel} · 168 px", fill="#888888", font=tf)
    out = d / "preview.png"
    sheet.save(out)
    return out


PACKAGE_PROMPT = """You are the packaging strategist of the YouTube channel "{name}" ({tagline}).
Positioning: {positioning}
Visual style: {style}
Recurring characters: {characters}

Video: "{title}"
Series: {series}

Create packaging. Rules:
- Titles: ≤ 60 characters, curiosity without lying: the title must stay true to the claims listed below (no bigger
  numbers, no "all humans" if the study is one group). Mix styles: question, surprising fact, "why", contrast.
- Thumbnails: exactly 3, one of each kind, so YouTube's Test & Compare can tell which kind works for this channel.
  The factory prints every word itself; the picture never contains text.
  1. kind: correction. `myth`: the belief the video overturns, at most 3 short words or one number, printed big
     and struck through by hand. `note`: at most 3 handwritten words under it that open a curiosity gap without giving the
     answer away. Picture: the object of the belief, large.
  2. kind: stamp. One iconic object of the belief drawn large; a rubber stamp goes on the empty side. `stamp` only if
     a word other than "{stamp}" fits much better. No other words.
  3. kind: scene. A funny or tense moment that really happens in the video; `text`: at most 3 words.
  For each: `visual: {{prompt, characters}}` (one subject filling about half of the frame, what it is and does,
  emotion, framing; no text in the picture), `pos` = where the words go and the picture stays empty (top-left | top |
  top-right | left | right | bottom-left | bottom; never bottom-right, where YouTube shows the duration), and `claim`
  = the id of the claim that any number or fact on the thumbnail rests on. The words add to the title, never repeat it.
{thumb_rules}- Hooks: 3 alternative first 8 seconds (≤ 25 words) that put the most surprising sourced fact or stake up front.
- Shorts: 2 ideas for purpose-written Shorts from this research (hook line + what it shows + loop ending).

Reply with ONLY this YAML:

titles: ["...", "..."]            # 10
thumbnails:
  - kind: correction
    visual: {{prompt: "...", characters: []}}
    myth: {{en: "..."}}
    note: {{en: "..."}}
    pos: top-left
    claim: c03
  - kind: stamp
    visual: {{prompt: "...", characters: []}}
    pos: top-left
  - kind: scene
    visual: {{prompt: "...", characters: []}}
    text: {{en: "..."}}
    pos: top
hooks:
  - {{type: cold_open_stat, text: "..."}}    # types: {hook_types}
description: "first two lines of the YouTube description (≤ 200 chars), no hashtags"
shorts_ideas:
  - {{hook: "...", shows: "...", loop: "..."}}

## Claims the packaging must stay true to
{claims}

## Script
{script}
"""


def build_package_prompt(project: Project) -> str:
    from . import thumbkit
    from .claims import load_claims
    from .publish import HOOK_TYPES, get_publish
    ch = project.ch.data
    pub = get_publish(project)
    series = (ch.get("series") or {}).get(pub.get("series") or "", {})
    claims = "\n".join(f"- {c.get('id', '')}: {c.get('text')}" + (f" (caveat: {c['caveat']})" if c.get("caveat") else "")
                       for c in load_claims(project)["claims"]) or "(no claims.yaml yet: use only what the script says)"
    script = project.script_path.read_text(encoding="utf-8")
    pkg = ch.get("package") or {}
    rules = pkg.get("thumbnail_rules") or ((ch.get("thumbnails") or {}).get("rules")) or []
    if isinstance(rules, str):
        rules = [rules]
    thumb_rules = "".join(f"- {r}\n" for r in rules)
    return PACKAGE_PROMPT.format(
        name=ch.get("name", project.channel), tagline=ch.get("tagline", ""),
        positioning=" ".join(str(pkg.get("positioning") or ch.get("description") or "").split()),
        style=ch.get("visual_style") or "painterly documentary illustration",
        characters="; ".join(f"{k}: {(v or {}).get('description', '')}" for k, v in (ch.get("characters") or {}).items())
        or "none", title=project.meta.get("title", project.slug),
        series=f"{series.get('name', '—')}: {series.get('promise', '')}", hook_types=", ".join(HOOK_TYPES),
        stamp=thumbkit.theme_of(ch).get("stamp", "WRONG"), thumb_rules=thumb_rules, claims=claims, script=script)


def apply_package(project: Project, data: dict) -> dict:
    from .publish import get_publish, save_publish
    meta = project.meta
    n = {"titles": 0, "thumbnails": 0}
    if isinstance(data.get("thumbnails"), list) and data["thumbnails"]:
        meta["thumbnails"] = [t for t in data["thumbnails"] if isinstance(t, dict)][:3]
        n["thumbnails"] = len(meta["thumbnails"])
    if data.get("description") and not (meta.get("description") or "").strip():
        meta["description"] = str(data["description"]).strip()
    project.save_meta(meta)
    pub = get_publish(project)
    upd = {}
    if isinstance(data.get("titles"), list):
        upd["title_variants"] = [str(t) for t in data["titles"]][:12]
        n["titles"] = len(upd["title_variants"])
    if isinstance(data.get("hooks"), list):
        upd["hook_options"] = data["hooks"][:5]
    if isinstance(data.get("shorts_ideas"), list):
        upd["shorts_ideas"] = data["shorts_ideas"][:4]
    if upd:
        save_publish(project, {**{k: pub.get(k) for k in ()}, **upd})
    return n


def make_package(project: Project, cfg: Config, render: bool = True) -> dict:
    """One click: the package prompt goes to the planner model (Gemini by default), its YAML answer is applied
    (titles, thumbnail concepts, hooks, Shorts ideas) and the thumbnails are painted.
    planner.provider: manual only writes the prompt for claude.ai, as before."""
    import yaml

    from .llm import complete
    from .planner import parse_yaml_reply
    provider = cfg.get_path("planner.provider", "gemini")
    if provider == "manual":
        out = project.build / "package_prompt.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(build_package_prompt(project), encoding="utf-8")
        print(f"  paket istemi hazır: {out}\n  Panelde 'Paket istemini kopyala' → Claude → 'Cevabı uygula'.")
        return {"titles": 0, "thumbnails": 0}
    model = cfg.get_path(f"planner.{provider}.model", {"gemini": "gemini-3.8-flash"}.get(provider, "claude-sonnet-5"))
    print(f"  paket hazırlanıyor ({provider}: {model})...")
    data = None
    for attempt in (1, 2):                 # a reply that is not valid YAML gets one more try
        try:
            data = parse_yaml_reply(complete(build_package_prompt(project), model, provider=provider))
            break
        except (ValueError, yaml.YAMLError) as e:
            if attempt == 2:
                raise SystemExit(f"Paket cevabı okunamadı ({e}). Tekrar dene.")
            print("  cevap YAML değildi, tekrar deneniyor...")
    n = apply_package(project, data)
    print(f"  {n['titles']} başlık, {n['thumbnails']} kapak fikri, "
          f"{len(data.get('hooks') or [])} açılış, {len(data.get('shorts_ideas') or [])} Shorts fikri kaydedildi")
    if render and n["thumbnails"]:
        render_thumbnails(project, cfg)
    return n


if __name__ == "__main__":  # pragma: no cover
    sys.exit("use: python -m studio thumbnails <project>")
