"""Renders visual catalogs of everything the svg engine can draw → docs/catalog/*.png"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .config import ROOT
from .images.svg_engine import SvgEngine
from .svgkit import backgrounds, render_svg
from .svgkit.figure import POSES
from .svgkit.props import PROPS
from .svgkit.style import document

OUT = ROOT / "docs" / "catalog"


def _label(x, y, text, size=26):
    return (f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" '
            f'text-anchor="middle" fill="#333">{text}</text>')


def poses_sheet() -> str:
    from .svgkit.figure import draw_figure
    body, cols = [], 7
    names = sorted(POSES)
    for i, name in enumerate(names):
        col, row = i % cols, i // cols
        x, ground = 150 + col * 270, 300 + row * 330
        extra = {"hold": "spear"} if name == "throw" else {"hold": "pointer"} if name == "point" else {}
        body.append(draw_figure({"pose": name, "x": x - 20, "ground": ground, "scale": 0.62, **extra}, ground))
        body.append(_label(x, ground + 40, name))
    return document("".join(body), bg="#f6f1e4", wobble=2)


def props_sheet() -> str:
    body, cols = [], 8
    names = [n for n in sorted(PROPS) if n != "stars"]
    for i, name in enumerate(names):
        col, row = i % cols, i // cols
        cx, cy = 125 + col * 238, 120 + row * 205
        floating = name in {"clock", "sun", "moon", "icon_quern", "icon_oar", "check", "cross", "question",
                            "heart", "calendar", "zzz", "sweat", "motion", "effort", "bone", "bone_section",
                            "window", "board", "stars", "arrow", "rain"}
        kw = {}
        if name == "arrow":
            kw = {"to": (cx + 60, cy - 40)}
            x, y = cx - 60, cy + 40
        else:
            x, y = cx, (cy if floating else cy + 70)
        s = {"board": 0.2, "sofa": 0.22, "mammoth": 0.33, "tree": 0.4, "acacia": 0.4, "hut": 0.45,
             "window": 0.4, "bone": 0.35, "bone_section": 0.5, "desk": 0.35, "tv": 0.4,
             "dumbbell_rack": 0.45, "treadmill": 0.4, "deer": 0.4, "chair": 0.4, "mat": 0.3, "rock": 0.6,
             "campfire": 0.6, "rain": 0.3, "heart": 0.7, "question": 0.8, "clock": 0.6, "calendar": 0.6, "bar_chart": 0.3, "spear_ground": 0.45,
             "footprints": 0.6, "grain": 0.8, "quern": 0.8, "sun": 0.6, "moon": 0.7}.get(name, 0.8)
        if name == "footprints":
            x -= 110
        body.append(PROPS[name](x, y, s, **kw))
        body.append(_label(cx, cy + 95, name, 22))
    return document("".join(body), bg="#f6f1e4", wobble=2)


def build_catalog() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    with SvgEngine() as eng:
        for name, svg in (("poses", poses_sheet()), ("props", props_sheet())):
            p = OUT / f"{name}.png"
            eng.svg_to_png(svg, p)
            made.append(p)
        with tempfile.TemporaryDirectory() as tmp:
            thumbs = []
            for name in sorted(backgrounds.BACKGROUNDS):
                p = Path(tmp) / f"{name}.png"
                eng.svg_to_png(render_svg({"bg": name}), p)
                thumbs.append(p)
            # 3-column grid with labels (Pillow: works the same on Windows, Mac and Linux)
            from PIL import Image, ImageDraw, ImageFont
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", 26)
            except OSError:
                try:
                    font = ImageFont.truetype("arial.ttf", 26)
                except OSError:
                    font = ImageFont.load_default()
            rows = (len(thumbs) + 2) // 3
            sheet = Image.new("RGB", (3 * 640, rows * 360), "white")
            d = ImageDraw.Draw(sheet)
            for i, p in enumerate(thumbs):
                x, y = (i % 3) * 640, (i // 3) * 360
                sheet.paste(Image.open(p).convert("RGB").resize((640, 360)), (x, y))
                d.rectangle([x, y, x + 639, y + 40], fill="white")
                d.text((x + 12, y + 6), p.stem, fill="black", font=font)
            out = OUT / "backgrounds.png"
            sheet.save(out)
            made.append(out)
    return made
