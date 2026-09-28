"""Thumbnails + titles ("packaging").

project.yaml:
  thumbnails:                       # up to 3 variants → YouTube "Test & Compare" (winner by watch time)
    - visual: {bg: underwater, figures: [...], props: [...]}   # same recipe format as shots (docs/STORYBOARD.md)
      frame: {x: 900, y: 560, zoom: 1.7}   # close-up: faces must read at phone size
      text: {en: "BIGGER SPLEENS", tr: "DEV DALAK"}   # ≤ 4 words; thumbnails MAY contain text (shots may not)
      text_pos: left                # left | right | top | bottom
      text_color: "#ffd84d"         # default yellow; white also works
      highlight: {x: 1100, y: 520, r: 140}   # optional red circle around the key detail (drawing coordinates)

Renders build/thumbnails/<lang>/thumb1.png … (1280×720 JPEG-safe PNG) and preview.png that shows every variant at
YouTube's desktop and phone sizes, because a thumbnail is judged at ~168 px wide on a phone.
"""
from __future__ import annotations

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


def render_thumbnails(project: Project, cfg: Config, lang: str | None = None) -> list[Path]:
    from .images.svg_engine import SvgEngine
    from .svgkit import render_svg
    from .svgkit.style import use_palette
    variants = project.meta.get("thumbnails") or []
    if not variants:
        raise SystemExit("project.yaml → thumbnails boş. Panel: Kapak & başlık → 'Paket istemini kopyala'.")
    primary = project.primary_lang()
    langs = [lang] if lang else project.ch.languages
    out_dir = project.build / "thumbnails"
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    made: list[Path] = []
    palette = cfg.get_path("channel.style.palette") or {}
    with SvgEngine(cfg) as eng:
        for n, v in enumerate(variants[:3], 1):
            visual = dict(v.get("visual") or {})
            if not visual:
                print(f"  kapak {n}: visual yok, atlandı")
                continue
            if v.get("frame"):
                visual["frame"] = v["frame"]
            with use_palette(palette):
                svg = render_svg(visual, seed=n * 7)
            raw = raw_dir / f"thumb{n}.png"
            eng.svg_to_png(svg, raw)
            for lg in langs:
                img = compose(Image.open(raw), _text_for(v, lg, primary), v.get("text_pos", "left"),
                              v.get("text_color", "#ffd84d"), v.get("highlight"), v.get("frame"))
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
    """All variants side by side at desktop (360 px) and phone (168 px) size, next to a fake title line."""
    d = project.build / "thumbnails" / lang
    thumbs = sorted(d.glob("thumb[0-9].png"))
    if not thumbs:
        return None
    from .render import _font as small_font
    W = 40 + len(thumbs) * 420
    sheet = Image.new("RGB", (W, 470), "#0f0f0f")
    dr = ImageDraw.Draw(sheet)
    title = project.meta.get("title", project.slug)
    for i, t in enumerate(thumbs):
        x = 40 + i * 420
        big = Image.open(t).resize((360, 202), Image.LANCZOS)
        sheet.paste(big, (x, 30))
        dr.text((x, 244), f"{chr(65 + i)} — masaüstü", fill="#aaaaaa", font=small_font(16))
        small = Image.open(t).resize((168, 94), Image.LANCZOS)
        sheet.paste(small, (x, 290))
        tf = small_font(15)
        for k, ln in enumerate(_wrap(dr, title, tf, 220)[:3]):
            dr.text((x + 180, 292 + k * 20), ln, fill="#f1f1f1", font=tf)
        dr.text((x, 400), f"{chr(65 + i)} — telefon (168 px)", fill="#aaaaaa", font=small_font(16))
    out = d / "preview.png"
    sheet.save(out)
    return out


PACKAGE_PROMPT = """You are the packaging strategist of the YouTube channel "{name}" ({tagline}).
Positioning: education, not fitness-influencer. A strength & conditioning coach tells the story of the human body;
every claim is sourced; each video ends with a practical "coach's lesson". Visual style: hand-drawn stick figures
(the mascot "{mascot_name}": {mascot}).

Video: "{title}"
Series: {series}

Create packaging. Rules:
- Titles: ≤ 60 characters, curiosity without lying: the title must stay true to the claims listed below (no bigger
  numbers, no "all humans" if the study is one group). Mix styles: question, surprising fact, "why", contrast.
- Thumbnails: 3 clearly DIFFERENT concepts (not the same picture with other words). Each is a scene recipe in the
  exact format of the spec below, plus `frame` for a close-up (zoom 1.5–2.2 so faces/objects read on a phone),
  `text` of at most 4 words in English and Turkish, `text_pos` on the empty side of the picture, and optionally
  `highlight` (red circle) on the one detail that matters. One big idea per thumbnail; the text must not repeat the
  title, it adds to it.
- Hooks: 3 alternative first 8 seconds (≤ 25 words) that put the most surprising sourced fact or stake up front.
- Shorts: 2 ideas for purpose-written Shorts from this research (hook line + what it shows + loop ending).

Reply with ONLY this YAML:

titles: ["...", "..."]            # 10
thumbnails:
  - visual: {{bg: ..., figures: [...], props: [...]}}
    frame: {{x: 900, y: 560, zoom: 1.8}}
    text: {{en: "...", tr: "..."}}
    text_pos: left
    highlight: {{x: 1100, y: 500, r: 130}}
hooks:
  - {{type: cold_open_stat, text: "..."}}    # types: {hook_types}
description: "first two lines of the YouTube description (≤ 200 chars), no hashtags"
shorts_ideas:
  - {{hook: "...", shows: "...", loop: "..."}}

## Claims the packaging must stay true to
{claims}

## Script
{script}

## Drawing spec
{spec}
"""


def build_package_prompt(project: Project) -> str:
    from .claims import load_claims
    from .planner import SPEC
    from .publish import HOOK_TYPES, get_publish
    ch = project.ch.data
    pub = get_publish(project)
    series = (ch.get("series") or {}).get(pub.get("series") or "", {})
    claims = "\n".join(f"- {c.get('text')}" + (f" (caveat: {c['caveat']})" if c.get("caveat") else "")
                       for c in load_claims(project)["claims"]) or "(no claims.yaml yet: use only what the script says)"
    script = project.script_path.read_text(encoding="utf-8")
    return PACKAGE_PROMPT.format(
        name=ch.get("name", project.channel), tagline=ch.get("tagline", ""), mascot_name=ch.get("mascot_name", "the Coach"),
        mascot=ch.get("mascot", {}), title=project.meta.get("title", project.slug),
        series=f"{series.get('name', '—')}: {series.get('promise', '')}", hook_types=", ".join(HOOK_TYPES),
        claims=claims, script=script, spec=SPEC.read_text(encoding="utf-8"))


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


if __name__ == "__main__":  # pragma: no cover
    sys.exit("use: python -m studio thumbnails <project>")
