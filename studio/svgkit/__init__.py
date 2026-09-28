"""Code-drawn scenes: a small YAML/dict recipe → full-frame SVG.

visual:
  bg: savanna                 # see backgrounds.BACKGROUNDS
  bg_opts: {sun: low, hut: true}
  figures:                    # see figure.POSES
    - {pose: kneel_grind, x: 800, wear: [hair_bun, hide], face: focused, sweat: true}
  props:                      # see props.PROPS
    - {type: quern, x: 1120, y: 790}
    - {type: motion, x: 1120, y: 700}
  order: props_first          # props_first (default) | figures_first
"""
from __future__ import annotations

from . import backgrounds
from .figure import POSES, draw_figure
from .props import PROPS
from .style import document


def render_svg(visual: dict, seed: int = 7) -> str:
    bg_fill, bg_body, ground = backgrounds.get(visual.get("bg", "plain_warm"), **(visual.get("bg_opts") or {}))
    props_svg = []
    for p in visual.get("props", []) or []:
        p = dict(p)
        kind = p.pop("type")
        fn = PROPS.get(kind)
        if fn is None:
            raise ValueError(f"unknown prop: {kind} (options: {', '.join(PROPS)})")
        x = p.pop("x", 960)
        y = p.pop("y", ground)
        s = p.pop("scale", 1.0)
        props_svg.append(fn(x, y, s, **p))
    figs_svg = [draw_figure(f, ground) for f in visual.get("figures", []) or []]
    layers = props_svg + figs_svg if visual.get("order", "props_first") == "props_first" else figs_svg + props_svg
    return document(bg_body + "".join(layers), bg=bg_fill, seed=seed)


def catalog() -> dict:
    return {"backgrounds": sorted(backgrounds.BACKGROUNDS), "poses": sorted(POSES), "props": sorted(PROPS)}
