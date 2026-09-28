"""Renders visual catalogs of everything the svg engine can draw → docs/catalog/*.png
poses.png = poses (+ wear and hold demos), props.png = every prop, backgrounds.png = every background.
Each sheet is made of 1920×1080 pages stacked vertically."""
from __future__ import annotations

import tempfile
from pathlib import Path

from .config import ROOT
from .images.svg_engine import SvgEngine
from .svgkit import backgrounds, render_svg
from .svgkit.figure import HOLDS, POSES, WEAR, draw_figure
from .svgkit.props import FLOATING, PROPS
from .svgkit.style import document

OUT = ROOT / "docs" / "catalog"

# held item shown with a pose in the catalog
POSE_HOLD = {"throw": "spear", "point": "pointer", "draw_bow": "bow", "guard": ["sword", "shield"],
             "deep_squat": "barbell", "carry_head": "jar", "row": "paddle", "pull": "rope", "club_swing": "indian_club"}
# poses that need a little extra room
POSE_DX = {"crawl": -45, "deep_squat": 15, "guard": -40, "hang": 15, "push_up": -45, "ride": 35, "kneel_grind": -75,
           "pull": -70, "point": -45, "push": -20, "throw": -15, "row": -20}
POSE_SCALE = {"deep_squat": 0.36, "ride": 0.44, "crawl": 0.5, "push_up": 0.5, "kneel_grind": 0.55, "point": 0.5, "throw": 0.5, "leap": 0.55, "jump": 0.55, "hang": 0.55, "dive": 0.55,
              "swim": 0.55, "float": 0.55, "stretch": 0.55, "overhead_lift": 0.55, "celebrate": 0.58, "wave": 0.58,
              "draw_bow": 0.55, "guard": 0.5, "carry_head": 0.58, "row": 0.5, "pull": 0.34, "sit": 0.58,
              "sit_slouch": 0.58, "climb": 0.58, "lie": 0.52}

PROP_SCALE = {
    # original kit
    "board": 0.2, "sofa": 0.22, "mammoth": 0.33, "tree": 0.36, "acacia": 0.4, "hut": 0.45, "window": 0.4, "bone": 0.35,
    "bone_section": 0.5, "desk": 0.35, "tv": 0.4, "dumbbell_rack": 0.45, "treadmill": 0.4, "deer": 0.4, "chair": 0.4,
    "mat": 0.28, "rock": 0.6, "campfire": 0.6, "rain": 0.3, "heart": 0.7, "question": 0.8, "clock": 0.6,
    "calendar": 0.6, "bar_chart": 0.3, "spear_ground": 0.45, "footprints": 0.6, "grain": 0.8, "quern": 0.8,
    "sun": 0.6, "moon": 0.7,
    # animals
    "horse": 0.33, "chimp": 0.58, "gorilla": 0.36, "bear": 0.36, "cheetah": 0.38, "fish": 1.0, "seal": 0.52,
    "calf": 0.6,
    # body
    "heart_organ": 0.55, "lungs": 0.52, "spleen": 0.75, "brain": 0.52, "muscle": 0.45, "muscle_fiber": 0.62,
    "tendon": 0.52, "foot_arch": 0.45, "knee_joint": 0.48, "skull": 0.6, "tooth": 0.72, "dna": 0.55,
    "blood_cells": 0.55, "mitochondria": 0.55, "eye": 0.55, "spine": 0.42, "sweat_gland": 0.5, "fat_cell": 0.52,
    "pulse": 0.45,
    # gear
    "kettlebell": 0.7, "indian_club": 0.8, "meel": 0.52, "barbell": 0.3, "pullup_bar": 0.25, "treadwheel": 0.21,
    "bed": 0.3, "oxygen_tank": 0.52, "microscope": 0.52, "radio": 0.75, "protein_tub": 0.75, "amphora": 0.65,
    "pyramid": 0.26, "column": 0.36, "stone_block": 0.48, "pillar": 0.29, "boat": 0.34, "shield": 0.62, "sword": 0.52,
    "bow": 0.5, "helmet": 0.6, "sandal": 0.7, "shoe": 0.65, "pedometer": 0.6, "stopwatch": 0.62, "thermometer": 0.52,
    "scroll": 0.55, "book": 0.5, "flag": 0.33, "map_pin": 0.6, "bread": 0.7, "wreath": 0.72, "medal": 0.6,
    "dumbbell": 0.7,
    # nature
    "wave": 0.45, "bubbles": 0.6, "snowflake": 1.0, "mountain_icon": 0.55, "sunbeam": 0.5, "cloud": 0.45,
    "heat": 0.7, "wind": 0.6, "splash": 0.6, "palm": 0.36, "pine": 0.36, "reeds": 0.55, "seaweed": 0.55,
    "coral": 0.8, "igloo": 0.4, "yurt": 0.34, "stilt_house": 0.3, "tent": 0.4, "ice_hole": 0.8,
    # charts
    "line_chart": 0.34, "pie": 0.6, "gauge": 0.5, "meter": 0.45, "battery": 0.6, "timeline": 0.19, "people": 0.4,
    "balance": 0.3,
}
# horizontal nudge so off-centre drawings sit in their cell
PROP_DX = {"bear": -45, "horse": -25, "cheetah": 15, "chimp": -20, "gorilla": -30, "palm": -20, "flag": -60}
# props drawn around a baseline / tip rather than their centre
BASELINE_PROPS = {"bar_chart", "line_chart", "map_pin", "timeline"}


def _label(x, y, text, size=26):
    return (f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" '
            f'text-anchor="middle" fill="#333">{text}</text>')


def _pages(items, per_page):
    return [items[i:i + per_page] for i in range(0, len(items), per_page)]


def poses_pages() -> list[str]:
    pages = []
    cols = 8
    for chunk in _pages(sorted(POSES), cols * 3):
        body = []
        for i, name in enumerate(chunk):
            col, row = i % cols, i // cols
            x, ground = 130 + col * 237, 330 + row * 345
            x += POSE_DX.get(name, 0)
            s = POSE_SCALE.get(name, 0.62)
            spec = {"pose": name, "x": x - 20, "ground": ground, "scale": s, "hold": POSE_HOLD.get(name, "none")}
            if name == "ride":
                body.append(PROPS["horse"](x - 20, ground, s))
            if name == "hang":
                body.append(PROPS["pullup_bar"](x - 20, ground, s))
            body.append(draw_figure(spec, ground))
            body.append(_label(x - POSE_DX.get(name, 0), ground + 36, name))
        pages.append(document("".join(body), bg="#f6f1e4", wobble=2))
    return pages + wear_pages()


def wear_pages() -> list[str]:
    """One figure per wear item and per hold item (labelled 'wear: x' / 'hold: x')."""
    extra_wear = [w for w in WEAR]
    holds = [h for h in HOLDS if h != "none"]
    items = [("wear", w) for w in extra_wear] + [("hold", h) for h in holds]
    pages, cols = [], 9
    pose_for = {"jar": "carry_head", "basket": "carry_head", "bundle": "carry_head", "bow": "draw_bow",
                "paddle": "row", "rope": "pull", "barbell": "overhead_lift", "log": "carry", "rock": "carry",
                "bowl": "carry", "baby": "carry", "spear": "throw", "pointer": "point", "shield": "guard",
                "sword": "guard", "scutum": "guard", "indian_club": "club_swing", "meel": "club_swing",
                "gada": "stand", "stick": "walk", "torch": "wave"}
    for chunk in _pages(items, cols * 3):
        body = []
        for i, (kind, name) in enumerate(chunk):
            col, row = i % cols, i // cols
            x, ground = 110 + col * 212, 320 + row * 345
            if kind == "wear":
                pose = {"shoes": "run", "sandals": "walk", "backpack": "walk", "tights": "wrestle",
                        "mawashi": "shiko", "goggles": "stand", "parka": "stand"}.get(name, "stand")
                spec = {"pose": pose, "x": x, "ground": ground, "scale": 0.55, "wear": [name]}
                if name == "goggles":
                    spec["scale"] = 0.62
            else:
                spec = {"pose": pose_for.get(name, "stand"), "x": x - 10, "ground": ground,
                        "scale": 0.36 if name in ("barbell", "rope", "spear", "pointer") else 0.5, "hold": name}
            body.append(draw_figure(spec, ground))
            body.append(_label(x, ground + 36, f"{kind}: {name}", 20))
        pages.append(document("".join(body), bg="#f3eee2", wobble=2))
    return pages


def props_pages() -> list[str]:
    cols, rows = 8, 5
    names = [n for n in sorted(PROPS) if n != "stars"]
    pages = []
    for chunk in _pages(names, cols * rows):
        body = []
        for i, name in enumerate(chunk):
            col, row = i % cols, i // cols
            cx, cy = 120 + col * 240, 112 + row * 212
            floating = name in FLOATING
            kw = {}
            if name == "arrow":
                kw = {"to": (cx + 60, cy - 40)}
                x, y = cx - 60, cy + 40
            elif name in BASELINE_PROPS:
                x, y = cx, cy + 62
            else:
                x, y = cx, (cy if floating else cy + 70)
            if name == "footprints":
                x -= 110
            if name == "ice_hole":
                y -= 45
            x += PROP_DX.get(name, 0)
            if name == "timeline":
                kw = {"highlight": 2}
            s = PROP_SCALE.get(name, 0.8)
            body.append(PROPS[name](x, y, s, **kw))
            body.append(_label(cx, cy + 98, name, 21))
        pages.append(document("".join(body), bg="#f6f1e4", wobble=2))
    return pages


def poses_sheet() -> str:
    """First page only (kept for callers of the old API)."""
    return poses_pages()[0]


def props_sheet() -> str:
    return props_pages()[0]


def _font(size=26):
    from PIL import ImageFont
    for name in ("DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _stack(pngs: list[Path], out: Path) -> None:
    from PIL import Image
    ims = [Image.open(p).convert("RGB") for p in pngs]
    sheet = Image.new("RGB", (ims[0].width, sum(i.height for i in ims)), "white")
    y = 0
    for im in ims:
        sheet.paste(im, (0, y))
        y += im.height
    sheet.save(out)


def build_catalog() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    with SvgEngine() as eng, tempfile.TemporaryDirectory() as tmp:
        for name, pages in (("poses", poses_pages()), ("props", props_pages())):
            pngs = []
            for i, svg in enumerate(pages):
                p = Path(tmp) / f"{name}_{i}.png"
                eng.svg_to_png(svg, p)
                pngs.append(p)
            out = OUT / f"{name}.png"
            _stack(pngs, out)
            made.append(out)
        thumbs = []
        for name in sorted(backgrounds.BACKGROUNDS):
            p = Path(tmp) / f"bg_{name}.png"
            eng.svg_to_png(render_svg({"bg": name}), p)
            thumbs.append((name, p))
        # 3-column grid with labels (Pillow: works the same on Windows, Mac and Linux)
        from PIL import Image, ImageDraw
        font = _font(26)
        rows = (len(thumbs) + 2) // 3
        sheet = Image.new("RGB", (3 * 640, rows * 360), "white")
        d = ImageDraw.Draw(sheet)
        for i, (name, p) in enumerate(thumbs):
            x, y = (i % 3) * 640, (i // 3) * 360
            sheet.paste(Image.open(p).convert("RGB").resize((640, 360)), (x, y))
            d.rectangle([x, y, x + 639, y + 40], fill="white")
            d.text((x + 12, y + 6), name, fill="black", font=font)
        out = OUT / "backgrounds.png"
        sheet.save(out)
        made.append(out)
    return made

