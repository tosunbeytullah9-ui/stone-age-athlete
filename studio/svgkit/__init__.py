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
  frame: {x: 900, y: 600, zoom: 1.8}   # optional close-up: centre of interest + zoom (1 = full frame)
"""
from __future__ import annotations

from . import backgrounds
from .figure import POSES, draw_figure
from .props import PROPS
from .style import H, W, document


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
    svg = document(bg_body + "".join(layers), bg=bg_fill, seed=seed)
    fr = visual.get("frame")
    if isinstance(fr, dict) and float(fr.get("zoom", 1)) > 1:
        svg = crop_svg(svg, float(fr.get("x", W / 2)), float(fr.get("y", H / 2)), float(fr["zoom"]))
    return svg


def crop_svg(svg: str, cx: float, cy: float, zoom: float, out_w: int = W, out_h: int = H) -> str:
    """Close-up without quality loss: the drawing is vector, so only the viewBox changes."""
    zoom = max(1.0, min(zoom, 4.0))
    vw, vh = W / zoom, H / zoom
    x0 = min(max(cx - vw / 2, 0), W - vw)
    y0 = min(max(cy - vh / 2, 0), H - vh)
    head = f'width="{W}" height="{H}" viewBox="0 0 {W} {H}"'
    return svg.replace(head, f'width="{out_w}" height="{out_h}" viewBox="{x0:.1f} {y0:.1f} {vw:.1f} {vh:.1f}"', 1)


def crop_vertical(svg: str, cx: float, out_w: int = 1080, out_h: int = 1920) -> str:
    """9:16 window of the full-height drawing around x = cx (for Shorts): still vector, so sharp at 1080×1920."""
    vh = H
    vw = H * out_w / out_h
    x0 = min(max(cx - vw / 2, 0), W - vw)
    head = f'width="{W}" height="{H}" viewBox="0 0 {W} {H}"'
    return svg.replace(head, f'width="{out_w}" height="{out_h}" viewBox="{x0:.1f} 0 {vw:.1f} {vh:.1f}"', 1)


def catalog() -> dict:
    return {"backgrounds": sorted(backgrounds.BACKGROUNDS), "poses": sorted(POSES), "props": sorted(PROPS)}
