"""Living pictures: small animation inside each scene's painting (studio/stillmotion, free, local, CPU).

The painting stays the painting. Its parts move: a depth-based 2.5D camera, grass that sways, fire that flickers,
embers, snow, dust in a sunbeam, a glowing joint, a breathing chest, ink lines that "boil" on a ledger page.

Settings (config.yaml → video, overridable per channel in channel.yaml → overrides.video):
  motion: off         auto = every picture moves (its plan from motion.yaml, else the channel preset)
                      off  = the classic FFmpeg zoompan camera (default)
  motion_preset: painterly | ledger | flat
  motion_workers: 3   scenes rendered at the same time

Plan per project: channels/<c>/projects/<slug>/motion.yaml — scene id (first shot of the scene) → spec:
  s107:
    camera: {move: in, parallax: 0.6, focus: [0.62, 0.42]}
    fx:
      - {type: flicker, box: [0.28, 0.62, 0.47, 0.9], amount: 0.35}
      - {type: embers,  box: [0.3, 0.42, 0.44, 0.84]}
Omitted camera keys come from the preset; `move` defaults to the scene's camera (storyboard `camera` or the
rotation in → right → out → left). See docs/STORYBOARD.md (Motion) and `python -m stillmotion effects`.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from .config import Config
from .project import Project

ENGINE_VERSION = "sm1"


def enabled(cfg: Config) -> bool:
    return str(cfg.get_path("video.motion", "off") or "off").lower() not in ("off", "false", "0", "none")


def plan_path(project: Project) -> Path:
    return project.dir / "motion.yaml"


def load_plan(project: Project) -> dict:
    p = plan_path(project)
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {str(k): (v or {}) for k, v in data.items()}


def scene_spec(head: dict, index: int, mode: str, cfg: Config, plan: dict) -> dict:
    """The motion spec of one scene: preset ← plan; move from the scene's camera unless the plan sets it."""
    from .stillmotion.presets import PRESETS
    preset = str(cfg.get_path("video.motion_preset", "painterly"))
    base = copy.deepcopy(PRESETS.get(preset, PRESETS["painterly"]))
    cam = {**(base.get("camera") or {}), "move": mode,
           "amount": float(cfg.get_path("video.zoom", 0.08))}          # the owner's zoom setting stays the size
    mine = plan.get(head["id"])
    fx = list(base.get("fx") or [])
    if mine:
        c = mine.get("camera")
        cam.update({"move": c} if isinstance(c, str) else (c or {}))
        fx = (fx if mine.get("inherit_fx", True) else []) + list(mine.get("fx") or [])
    return {"camera": cam, "fx": fx, "seed": int((mine or {}).get("seed", index + 1))}


def _key(img: Path, spec: dict, frames, fps: int, size: tuple[int, int]) -> str:
    h = hashlib.sha1(img.read_bytes()).hexdigest()[:12]
    blob = json.dumps({"s": spec, "f": frames, "fps": fps, "size": size, "v": ENGINE_VERSION}, sort_keys=True)
    return f"{h}-{hashlib.sha1(blob.encode()).hexdigest()[:10]}"


def render_scene_clips(project: Project, cfg: Config, jobs: list[dict], fps: int, size: tuple[int, int],
                       crf: int) -> dict[str, Path]:
    """jobs: [{id, img, spec, frames, tail}] → {id: mp4}. The camera move spans `frames` (the scene); `tail` more
    frames keep the effects going for the cross-fade into the next scene. Cached by picture + spec + length."""
    from .stillmotion import Clip, encode
    out_dir = project.build / "motion"
    depth_dir = out_dir / "depth"
    out_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("STILLMOTION_MODEL_DIR", str(Path(__file__).resolve().parent.parent / "models"))
    todo, result = [], {}
    for j in jobs:
        path = out_dir / f"{j['id']}-{_key(j['img'], j['spec'], (j['frames'], j.get('tail', 0)), fps, size)}.mp4"
        result[j["id"]] = path
        if not path.exists():
            todo.append((j, path))
    if not todo:
        return result
    # depth maps first, one at a time (shared model, cached on disk)
    from .stillmotion.depth import load_depth
    from .stillmotion.engine import _read_rgb
    for j, _ in todo:
        if float((j["spec"].get("camera") or {}).get("parallax", 0) or 0) > 0:
            load_depth(j["img"], _read_rgb(j["img"]), depth_dir)
    workers = max(1, int(cfg.get_path("video.motion_workers", 3)))
    print(f"  canlı resim: {len(todo)} sahne hareketlendiriliyor ({len(jobs) - len(todo)} önbellekte)...")

    def one(item):
        j, path = item
        clip = Clip(j["img"], j["spec"], j["frames"] / fps, fps, size, cache_dir=depth_dir)
        tmp = path.with_suffix(".part.mp4")
        encode(clip.frames(0, j["frames"] + j.get("tail", 0)), tmp, size, fps, crf=max(12, crf - 2))
        tmp.replace(path)
        return path

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for _ in ex.map(one, todo):
            done += 1
            if done % 10 == 0 or done == len(todo):
                print(f"  sahne {done}/{len(todo)}")
    # old clips of the same scenes (other spec/length) are left for the cache to reuse when switching back
    return result


# ------------------------------------------------------------------ planning helpers
def motion_sheet(project: Project, cols: int = 3) -> Path:
    """Scene pictures with a labelled 0..1 grid, to choose effect boxes (build/motion_sheet.png)."""
    import cv2
    import numpy as np
    from .images import scenes
    from .stillmotion.__main__ import grid_image
    from .stillmotion.engine import _read_rgb
    shots = project.load_storyboard()["shots"]
    groups = [g for g in scenes(shots) if (project.shots_dir / f"{g[0]['id']}.png").exists()]
    tw, th = 960, 540
    tiles = []
    for g in groups:
        img = cv2.resize(grid_image(_read_rgb(project.shots_dir / f"{g[0]['id']}.png")), (tw, th),
                         interpolation=cv2.INTER_AREA)
        band = np.full((70, tw, 3), 255, np.uint8)
        text = " ".join(s["text"] for s in g)
        cv2.putText(band, g[0]["id"], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(band, text[:95], (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 60, 60), 1, cv2.LINE_AA)
        tiles.append(np.vstack([img, band]))
    if not tiles:
        raise SystemExit("Henüz resim yok (önce 'images').")
    while len(tiles) % cols:
        tiles.append(np.full_like(tiles[0], 255))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    out = project.build / "motion_sheet.png"
    sheet = cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(".png", sheet)
    buf.tofile(str(out))
    return out


def preview_scenes(project: Project, cfg: Config, only: set[str] | None, seconds: float = 7.0) -> list[Path]:
    """Strip + motion map + small mp4 per scene → build/motion_preview/<id>/ (look at strip.png and motion.png)."""
    from .images import scenes
    from .render import _scene_modes
    from .stillmotion.__main__ import preview
    shots = project.load_storyboard()["shots"]
    groups = scenes(shots)
    modes = _scene_modes(groups)
    plan = load_plan(project)
    outs = []
    for gi, (g, mode) in enumerate(zip(groups, modes)):
        head = g[0]
        if only and head["id"] not in only:
            continue
        img = project.shots_dir / f"{head['id']}.png"
        if not img.exists():
            continue
        out = project.build / "motion_preview" / head["id"]
        spec = scene_spec(head, gi, mode, cfg, plan)
        os.environ.setdefault("STILLMOTION_MODEL_DIR", str(Path(__file__).resolve().parent.parent / "models"))
        preview(img, spec, out, seconds, int(cfg.get_path("video.fps", 30)), None, "", False)
        outs.append(out)
    return outs
