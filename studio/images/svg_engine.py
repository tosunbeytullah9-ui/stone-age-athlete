"""Free engine: scene recipe → SVG → PNG (rasterised by headless Chromium via Playwright)."""
from __future__ import annotations

from pathlib import Path

from ..svgkit import render_svg
from ..svgkit.style import H, W


class SvgEngine:
    def __init__(self, cfg=None):
        self._pw = self._browser = self._page = None

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

    def svg_to_png(self, svg: str, out: Path) -> None:
        self._page.set_content(f'<html><body style="margin:0;overflow:hidden">{svg}</body></html>')
        self._page.screenshot(path=str(out))

    def render(self, shot: dict, out: Path, seed: int = 7) -> None:
        visual = shot["visual"]
        svg = render_svg(visual, seed=seed)
        out.with_suffix(".svg").write_text(svg, encoding="utf-8")
        self.svg_to_png(svg, out)
