"""Command line.

  python -m stillmotion render  IMG -o OUT.mp4 --seconds 7 [--spec spec.yaml | --json '{...}'] [--preset painterly]
  python -m stillmotion preview IMG [--spec ...] [-o DIR] [--seconds 7]   → strip.png, motion.png, preview.mp4
  python -m stillmotion grid    IMG [-o grid.png]      picture with a labelled 0..1 grid (to choose effect boxes)
  python -m stillmotion depth   IMG [-o depth.png]     depth map (white = near)
  python -m stillmotion batch   plan.yaml            {items: [{image, out, seconds, spec}], fps, size, preset}
  python -m stillmotion effects                         list effects and their parameters
  python -m stillmotion fetch-model                     download the depth model now
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from .engine import Clip, _read_rgb, encode
from .presets import PRESETS


def _load_spec(a) -> dict | None:
    if getattr(a, "json", None):
        return json.loads(a.json)
    if getattr(a, "spec", None):
        import yaml
        return yaml.safe_load(Path(a.spec).read_text(encoding="utf-8"))
    return None


def _size(s):
    if not s:
        return None
    w, h = s.lower().split("x")
    return int(w), int(h)


def _write(path: Path, rgb: np.ndarray) -> None:
    ok, buf = cv2.imencode(path.suffix or ".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not ok:
        raise RuntimeError(f"yazılamadı: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    buf.tofile(str(path))


def grid_image(rgb: np.ndarray) -> np.ndarray:
    img = rgb.copy()
    h, w = img.shape[:2]
    for k in range(1, 10):
        x, y = int(w * k / 10), int(h * k / 10)
        col = (255, 255, 255) if k != 5 else (255, 230, 0)
        cv2.line(img, (x, 0), (x, h), (0, 0, 0), 3, cv2.LINE_AA)
        cv2.line(img, (x, 0), (x, h), col, 1, cv2.LINE_AA)
        cv2.line(img, (0, y), (w, y), (0, 0, 0), 3, cv2.LINE_AA)
        cv2.line(img, (0, y), (w, y), col, 1, cv2.LINE_AA)
        for txt, pos in ((f"{k / 10:.1f}", (x + 6, 40)), (f"{k / 10:.1f}", (4, y - 6))):
            cv2.putText(img, txt, pos, cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 6, cv2.LINE_AA)
            cv2.putText(img, txt, pos, cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def motion_map(frames: list[np.ndarray], base: np.ndarray) -> np.ndarray:
    """Where things move: per-pixel spread over the sampled frames, painted red over a dimmed frame."""
    st = np.stack([cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).astype(np.float32) for f in frames])
    spread = st.max(0) - st.min(0)
    spread = cv2.GaussianBlur(spread, (0, 0), 2)
    norm = np.clip(spread / max(np.percentile(spread, 99.5), 8.0), 0, 1)[..., None]
    dim = (base.astype(np.float32) * 0.45)
    red = np.array([255, 40, 30], np.float32)
    return np.clip(dim * (1 - norm) + red * norm, 0, 255).astype(np.uint8)


def preview(img_path: Path, spec, out_dir: Path, seconds: float, fps: int, size, preset: str, still_cam: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    defaults = PRESETS.get(preset) if preset else None
    t0 = time.time()
    clip = Clip(img_path, spec, seconds, fps, size, cache_dir=out_dir / ".cache", defaults=defaults)
    if still_cam:                          # look at the local effects alone
        clip.spec.camera.move = "none"
        clip.spec.camera.parallax = 0.0
    idx = sorted(set(int(round(x)) for x in np.linspace(0, clip.n - 1, 4)))
    strip = [clip.frame(i) for i in idx]
    th = 360
    tw = int(clip.W * th / clip.H)
    row = np.concatenate([cv2.resize(f, (tw, th), interpolation=cv2.INTER_AREA) for f in strip], 1)
    for k, i in enumerate(idx):
        cv2.putText(row, f"{i / fps:.1f}s", (k * tw + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(row, f"{i / fps:.1f}s", (k * tw + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    _write(out_dir / "strip.png", row)
    # motion map with a still camera, so it shows the local effects (what moves inside the picture)
    mclip = Clip(img_path, spec, seconds, fps, size, cache_dir=out_dir / ".cache", defaults=defaults)
    mclip.spec.camera.move, mclip.spec.camera.parallax = "none", 0.0
    sample = [mclip.frame(int(i)) for i in np.linspace(0, mclip.n - 1, 12)]
    _write(out_dir / "motion.png", motion_map(sample, sample[0]))
    small = (clip.W // 2 // 2 * 2, clip.H // 2 // 2 * 2)
    encode((cv2.resize(f, small, interpolation=cv2.INTER_AREA) for f in clip.frames()), out_dir / "preview.mp4",
           small, fps, crf=23)
    print(json.dumps({"strip": str(out_dir / "strip.png"), "motion": str(out_dir / "motion.png"),
                      "preview": str(out_dir / "preview.mp4"), "depth": clip.depth_source,
                      "seconds": round(time.time() - t0, 1)}, ensure_ascii=False))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="stillmotion")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, spec=True):
        p.add_argument("image")
        if spec:
            p.add_argument("--spec")
            p.add_argument("--json")
            p.add_argument("--preset", default="")
            p.add_argument("--seconds", type=float, default=7.0)
            p.add_argument("--fps", type=int, default=30)
            p.add_argument("--size")
            p.add_argument("--depth", default="auto", choices=["auto", "model", "heuristic", "off"])

    r = sub.add_parser("render"); common(r); r.add_argument("-o", "--out", required=True)
    r.add_argument("--crf", type=int, default=18)
    p = sub.add_parser("preview"); common(p); p.add_argument("-o", "--out", default="")
    p.add_argument("--still-camera", action="store_true")
    g = sub.add_parser("grid"); common(g, False); g.add_argument("-o", "--out", default="")
    d = sub.add_parser("depth"); common(d, False); d.add_argument("-o", "--out", default="")
    b = sub.add_parser("batch"); b.add_argument("plan")
    sub.add_parser("effects")
    sub.add_parser("fetch-model")
    a = ap.parse_args(argv)

    if a.cmd == "effects":
        from .effects import REGISTRY
        for name, cls in sorted(REGISTRY.items(), key=lambda x: (x[1].family, x[0])):
            doc = " ".join((cls.__doc__ or "").split())
            print(f"{cls.family:9s} {name:9s} {doc}")
        return 0
    if a.cmd == "fetch-model":
        from .depth import download_model, find_model
        print(find_model() or download_model())
        return 0
    if a.cmd == "grid":
        src = Path(a.image)
        _write(Path(a.out or src.with_name(src.stem + ".grid.png")), grid_image(_read_rgb(src)))
        return 0
    if a.cmd == "depth":
        from .depth import load_depth
        src = Path(a.image)
        dmap, how = load_depth(src, _read_rgb(src), None)
        out = Path(a.out or src.with_name(src.stem + ".depth.png"))
        _write(out, cv2.cvtColor((dmap * 255).astype(np.uint8), cv2.COLOR_GRAY2RGB))
        print(f"{out} ({how})")
        return 0
    if a.cmd == "batch":
        import yaml
        plan = yaml.safe_load(Path(a.plan).read_text(encoding="utf-8"))
        base = Path(a.plan).parent
        defaults = PRESETS.get(plan.get("preset", "")) if plan.get("preset") else None
        for it in plan["items"]:
            t0 = time.time()
            clip = Clip(base / it["image"], it.get("spec"), float(it["seconds"]), int(plan.get("fps", 30)),
                        _size(plan.get("size")), cache_dir=base / ".stillmotion", defaults=defaults)
            encode(clip.frames(), base / it["out"], (clip.W, clip.H), clip.fps)
            print(f"  {it['out']}  {clip.n} kare  {time.time() - t0:.1f} sn")
        return 0

    spec = _load_spec(a)
    defaults = PRESETS.get(a.preset) if a.preset else None
    src = Path(a.image)
    if a.cmd == "render":
        t0 = time.time()
        clip = Clip(src, spec, a.seconds, a.fps, _size(a.size), a.depth, src.parent / ".stillmotion", defaults)
        encode(clip.frames(), Path(a.out), (clip.W, clip.H), clip.fps, a.crf)
        print(json.dumps({"out": a.out, "frames": clip.n, "depth": clip.depth_source,
                          "seconds": round(time.time() - t0, 1)}))
        return 0
    if a.cmd == "preview":
        out = Path(a.out or src.with_name(src.stem + "_preview"))
        preview(src, spec, out, a.seconds, a.fps, _size(a.size), a.preset, a.still_camera)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
