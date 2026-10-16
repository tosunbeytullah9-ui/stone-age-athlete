"""Depth maps for 2.5D parallax.

Depth Anything V2 Small (Apache-2.0) as ONNX, run on the CPU with onnxruntime. The model is downloaded once
(~100 MB) to the first writable place of: $STILLMOTION_MODEL_DIR, ./models, ~/.cache/stillmotion.
Without onnxruntime or the model, a plain heuristic is used (bottom of the picture = near, top = far), which is
enough for gentle landscape parallax but not for close-ups.

Depth convention everywhere in this package: float32 HxW in [0, 1], 1 = nearest to the camera.
Results are cached next to the work files as 16-bit PNG keyed by the picture's content hash.
"""
from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path

import cv2
import numpy as np

MODEL_NAME = "depth_anything_v2_vits.onnx"
MODEL_URL = "https://github.com/fabio-sim/Depth-Anything-ONNX/releases/download/v2.0.0/" + MODEL_NAME
_SESSION = None


def _model_dirs() -> list[Path]:
    dirs = []
    if os.environ.get("STILLMOTION_MODEL_DIR"):
        dirs.append(Path(os.environ["STILLMOTION_MODEL_DIR"]))
    dirs += [Path.cwd() / "models", Path.home() / ".cache" / "stillmotion"]
    return dirs


def find_model() -> Path | None:
    for d in _model_dirs():
        p = d / MODEL_NAME
        if p.exists() and p.stat().st_size > 50_000_000:
            return p
    return None


def download_model(verbose: bool = True) -> Path:
    """Download the depth model to the first writable model folder."""
    last = None
    for d in _model_dirs():
        try:
            d.mkdir(parents=True, exist_ok=True)
            out = d / MODEL_NAME
            tmp = out.with_suffix(".part")
            if verbose:
                print(f"  derinlik modeli indiriliyor (~100 MB) → {out}")
            urllib.request.urlretrieve(MODEL_URL, tmp)
            tmp.replace(out)
            return out
        except OSError as e:          # read-only folder etc.: try the next one
            last = e
    raise RuntimeError(f"derinlik modeli indirilemedi: {last}")


def _session(download: bool = True):
    global _SESSION
    if _SESSION is not None:
        return _SESSION
    try:
        import onnxruntime as ort
    except ImportError:
        return None
    path = find_model()
    if path is None:
        if not download:
            return None
        try:
            path = download_model()
        except Exception as e:
            print(f"  [!] {e} — sezgisel derinlik kullanılacak")
            return None
    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    # bytes, not a path: onnxruntime/OpenCV can fail on non-ASCII Windows paths (e.g. "Video-Fabrikası")
    _SESSION = ort.InferenceSession(Path(path).read_bytes(), opts, providers=["CPUExecutionProvider"])
    return _SESSION


def heuristic_depth(h: int, w: int) -> np.ndarray:
    """Bottom = near, top = far, with a soft horizon. Good enough for wide landscapes."""
    y = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    d = np.clip((y - 0.25) / 0.75, 0, 1) ** 1.3
    return np.repeat(d, w, axis=1)


def estimate(rgb: np.ndarray, download: bool = True) -> tuple[np.ndarray, str]:
    """rgb uint8 HxWx3 → (depth float32 HxW in [0,1], source name)."""
    h, w = rgb.shape[:2]
    sess = _session(download)
    if sess is None:
        return heuristic_depth(h, w), "heuristic"
    size = 518
    x = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    x = x.transpose(2, 0, 1)[None]
    inp = sess.get_inputs()[0].name
    out = sess.run(None, {inp: x})[0][0].astype(np.float32)   # relative inverse depth: bigger = nearer
    lo, hi = np.percentile(out, 2), np.percentile(out, 98)
    d = np.clip((out - lo) / max(hi - lo, 1e-6), 0, 1)
    d = cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)
    return np.clip(d, 0, 1), "depth-anything-v2-small"


def refine(depth: np.ndarray, smooth: float = 0.006) -> np.ndarray:
    """Make depth friendly for warping: grow near regions a little (the background stretches instead of the
    subject's outline) and blur hard steps so edges bend instead of tearing."""
    h, w = depth.shape
    k = max(3, int(round(w * 0.004)) | 1)
    d = cv2.dilate(depth, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    s = max(1.0, w * smooth)
    return cv2.GaussianBlur(d, (0, 0), s)


def image_hash(path: Path) -> str:
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:16]


def load_depth(image_path: Path, rgb: np.ndarray, cache_dir: Path | None = None, mode: str = "auto",
               download: bool = True) -> tuple[np.ndarray, str]:
    """Depth for a picture, cached. mode: auto (model if available) | model | heuristic."""
    h, w = rgb.shape[:2]
    if mode == "heuristic":
        return refine(heuristic_depth(h, w)), "heuristic"
    cache = None
    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = cache_dir / f"{Path(image_path).stem}.{image_hash(image_path)}.depth.png"
        if cache.exists():
            d = cv2.imdecode(np.fromfile(str(cache), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            if d is not None and d.shape == (h, w):
                return d.astype(np.float32) / 65535.0, "cache"
    d, src = estimate(rgb, download=download)
    d = refine(d)
    if cache is not None and src != "heuristic":
        ok, buf = cv2.imencode(".png", (np.clip(d, 0, 1) * 65535).astype(np.uint16))
        if ok:
            buf.tofile(str(cache))
    return d, src
