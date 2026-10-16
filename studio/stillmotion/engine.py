"""Render a still picture into a moving clip.

Per frame:  source = picture + light effects + particles  (picture space)
            coords = camera (zoom/pan + depth parallax) ∘ local warps
            frame  = remap(source, coords)                 → output size
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import cv2
import numpy as np

from .depth import load_depth
from .effects import REGISTRY
from .spec import Spec, ease, parse


def _read_rgb(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)              # works with non-ASCII Windows paths
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"resim okunamadı: {path}")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


class Clip:
    """A still picture animated by a Spec. frame(i) returns uint8 RGB at the output size."""

    def __init__(self, image, spec: Spec | dict | None = None, seconds: float = 6.0, fps: int = 30,
                 size: tuple[int, int] | None = None, depth: str = "auto", cache_dir: Path | None = None,
                 defaults: dict | None = None):
        self.path = Path(image) if not isinstance(image, np.ndarray) else None
        self.img = _read_rgb(self.path) if self.path else image
        self.ih, self.iw = self.img.shape[:2]
        self.spec = spec if isinstance(spec, Spec) else parse(spec, defaults)
        self.fps = int(fps)
        self.seconds = float(seconds)
        self.n = max(1, int(round(self.seconds * self.fps)))
        self.W, self.H = size or (self.iw, self.ih)
        cam = self.spec.camera
        uses_depth = cam.parallax > 0 or any(e.get("depth") is not None for e in self.spec.fx)
        self.depth = None
        self.depth_source = "none"
        if uses_depth:
            if depth == "off":
                cam.parallax = 0.0
            else:
                self.depth, self.depth_source = load_depth(self.path or Path("array.png"), self.img, cache_dir,
                                                           mode=depth)
        self.fx = [REGISTRY[e["type"]](dict(e), self.ih, self.iw, self.depth, self.fps, self.seconds,
                                       self.spec.seed + 101 * k) for k, e in enumerate(self.spec.fx)]
        self.warps = [f for f in self.fx if f.family == "warp"]
        self.paints = [f for f in self.fx if f.family != "warp"]
        # base view: cover the output aspect inside the picture
        ar = self.W / self.H
        if self.iw / self.ih > ar:
            self.vh0, self.vw0 = float(self.ih), float(self.ih * ar)
        else:
            self.vw0, self.vh0 = float(self.iw), float(self.iw / ar)
        # coordinates are smooth, so they are computed on a half-size grid and upscaled (≈3× faster)
        self.gw, self.gh = max(2, self.W // 2), max(2, self.H // 2)
        u = (np.arange(self.gw, dtype=np.float32) + 0.5) / self.gw - 0.5
        v = (np.arange(self.gh, dtype=np.float32) + 0.5) / self.gh - 0.5
        self.U, self.V = np.meshgrid(u, v)

    # ------------------------------------------------------------------ camera
    def camera(self, i: int) -> dict:
        c = self.spec.camera
        p = ease(i / max(self.n - 1, 1), c.ease)
        a = c.amount if c.move != "none" else 0.0
        par = c.parallax
        over = 1.0 + (0.6 * par * max(c.amount, 0.04) if par > 0 else 0.0)   # hides edges revealed by parallax
        fx, fy = c.focus
        z, cx, cy, sx, sy, k = over, 0.5, 0.5, 0.0, 0.0, 0.0
        if c.move == "in":
            z = over * (1 + a * p)
            cx, cy = 0.5 + (fx - 0.5) * p, 0.5 + (fy - 0.5) * p
            k = par * a * 1.4 * p
        elif c.move == "out":
            z = over * (1 + a * (1 - p))
            cx, cy = fx + (0.5 - fx) * p, fy + (0.5 - fy) * p
            k = par * a * 1.4 * (1 - p)
        elif c.move in ("left", "right", "up", "down"):
            z = over * (1 + a)
            q = p if c.move in ("right", "down") else 1 - p
            if c.move in ("left", "right"):
                cx, cy = q, fy
                sx = par * a * 0.9 * (q - 0.5)
            else:
                cx, cy = fx, q
                sy = par * a * 0.9 * (q - 0.5)
        elif c.move == "drift":
            z = over * (1 + a * 0.35 * p)
            cx, cy = 0.5 + a * 0.4 * (p - 0.5), fy
            sx = par * a * 1.2 * (p - 0.5)
        elif c.move == "orbit":
            z = over * (1 + a * 0.4)
            cx, cy = fx, fy
            sx, sy = par * a * 0.7 * math.sin(2 * math.pi * p), par * a * 0.25 * (math.cos(2 * math.pi * p) - 1)
        vw, vh = self.vw0 / z, self.vh0 / z
        # keep the view inside the picture: cx/cy are fractions of the free range for pans, points for zooms
        if c.move in ("left", "right", "up", "down", "drift"):
            X = vw / 2 + (self.iw - vw) * cx
            Y = vh / 2 + (self.ih - vh) * cy
        else:
            X = min(max(cx * self.iw, vw / 2), self.iw - vw / 2)
            Y = min(max(cy * self.ih, vh / 2), self.ih - vh / 2)
        return dict(vw=vw, vh=vh, X=X, Y=Y, sx=sx, sy=sy, k=k)

    def coords(self, i: int, t: float) -> tuple[np.ndarray, np.ndarray]:
        cam = self.camera(i)
        mx = cam["X"] + self.U * cam["vw"]
        my = cam["Y"] + self.V * cam["vh"]
        if self.depth is not None and (cam["sx"] or cam["sy"] or cam["k"]):
            d = cv2.remap(self.depth, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            ref = 0.35                                    # depth that stays put: the background moves the least
            dd = d - ref
            # lateral: near things slide further than the background; zoom: near things grow faster
            mx = mx + cam["sx"] * self.iw * dd - (mx - cam["X"]) * cam["k"] * dd
            my = my + cam["sy"] * self.ih * dd - (my - cam["Y"]) * cam["k"] * dd
        if self.warps:
            dx = dy = None
            for w in self.warps:
                ax, ay = w.disp(t)
                if isinstance(ax, np.ndarray):
                    dx = ax if dx is None else dx + ax
                if isinstance(ay, np.ndarray):
                    dy = ay if dy is None else dy + ay
                elif isinstance(ax, np.ndarray) and dy is None:
                    pass
            low = self.warps[0].low
            sx, sy = mx / low - 0.5, my / low - 0.5
            if dx is not None:
                mx = mx + cv2.remap(dx.astype(np.float32), sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            if dy is not None:
                my = my + cv2.remap(dy.astype(np.float32), sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        mx = cv2.resize(mx.astype(np.float32), (self.W, self.H), interpolation=cv2.INTER_LINEAR)
        my = cv2.resize(my.astype(np.float32), (self.W, self.H), interpolation=cv2.INTER_LINEAR)
        return mx, my

    # ------------------------------------------------------------------ frames
    def frame(self, i: int) -> np.ndarray:
        t = i / self.fps
        if self.paints:
            src = self.img.copy()
            for p in self.paints:                     # each effect works on its own box only
                y0, y1, x0, x1 = p.y0, p.y1, p.x0, p.x1
                reg = src[y0:y1, x0:x1].astype(np.float32)
                p.apply_region(reg, t)
                src[y0:y1, x0:x1] = np.clip(reg, 0, 255).astype(np.uint8)
        else:
            src = self.img
        mx, my = self.coords(i, t)
        interp = cv2.INTER_CUBIC if self.spec.camera.move != "none" or self.warps else cv2.INTER_LINEAR
        return cv2.remap(src, mx, my, interp, borderMode=cv2.BORDER_REFLECT)

    def frames(self, start: int = 0, count: int | None = None):
        """Frames start..start+count. Past the clip length the camera holds its end and effects keep moving
        (useful for a cross-fade tail into the next scene)."""
        end = self.n if count is None else start + count
        for i in range(start, end):
            yield self.frame(i)


def encode(frames, out: Path, size: tuple[int, int], fps: int, crf: int = 18, preset: str = "veryfast") -> Path:
    """Pipe RGB frames into ffmpeg (H.264, yuv420p)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    W, H = size
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for f in frames:
            p.stdin.write(np.ascontiguousarray(f).tobytes())
        p.stdin.close()
    except BrokenPipeError:
        pass
    err = p.stderr.read().decode("utf-8", "replace")
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg: {err[-600:]}")
    return out


def render(image, out, seconds: float, spec=None, fps: int = 30, size=None, depth: str = "auto",
           cache_dir=None, defaults=None, crf: int = 18) -> Path:
    """One call: picture → mp4 of `seconds` with the spec's motion."""
    clip = Clip(image, spec, seconds, fps, size, depth, cache_dir, defaults)
    return encode(clip.frames(), Path(out), (clip.W, clip.H), clip.fps, crf)
