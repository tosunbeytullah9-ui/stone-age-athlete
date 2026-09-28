"""Free engine: scene recipe → SVG → PNG (rasterised by headless Chromium via Playwright)."""
from __future__ import annotations

from pathlib import Path

from ..svgkit import render_svg
from ..svgkit.style import H, W, use_palette


class SvgEngine:
    def __init__(self, cfg=None):
        self._pw = self._browser = self._page = None
        self.palette = (cfg.get_path("channel.style.palette") if cfg is not None else None) or {}

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self._page = self._browser.new_page(viewport={"width": W, "height": H})
        return self

    def __exit__(self, *exc):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def svg_to_png(self, svg: str, out: Path, size: tuple[int, int] | None = None) -> None:
        if size:
            self._page.set_viewport_size({"width": size[0], "height": size[1]})
        self._page.set_content(f'<html><body style="margin:0;overflow:hidden">{svg}</body></html>')
        self._page.screenshot(path=str(out))
        if size:
            self._page.set_viewport_size({"width": W, "height": H})

    def render(self, shot: dict, out: Path, seed: int = 7) -> None:
        from ..fx import ANIM_FRAMES, animated_visuals
        visual = shot["visual"]
        with use_palette(self.palette):
            svg = render_svg(visual, seed=seed)
            frames = animated_visuals(visual)
            anim_svgs = [render_svg(v, seed=seed) for v in frames]
        out.with_suffix(".svg").write_text(svg, encoding="utf-8")
        self.svg_to_png(svg, out)
        for old in out.parent.glob(f"{out.stem}_a[0-9][0-9].png"):
            old.unlink()
        for k, a in enumerate(anim_svgs[:ANIM_FRAMES], 1):     # growing charts: a short intro sequence
            self.svg_to_png(a, out.with_name(f"{out.stem}_a{k:02d}.png"))
