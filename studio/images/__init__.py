"""Renders one PNG per shot. Engine per shot: shot.engine or config images.default_engine.

  svg     free, code-drawn from shot.visual (a scene recipe dict)
  gemini  paid AI image from shot.visual.prompt (or shot.visual as a string)

Results are cached by content hash: a shot is only re-rendered when its recipe/prompt
or the engine settings change, so re-running never re-spends money on unchanged shots.
"""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

from ..config import Config
from ..project import Project
from .style_prompt import build_prompt


def _engine_name(shot: dict, cfg: Config) -> str:
    """Explicit shot.engine wins; otherwise the recipe decides: a scene recipe (bg/figures/props)
    is drawn with svg, a text prompt goes to gemini. A recipe with both uses the config default."""
    if shot.get("engine"):
        return shot["engine"]
    v = shot.get("visual")
    if isinstance(v, str):
        return "gemini"
    has_scene = isinstance(v, dict) and any(k in v for k in ("bg", "figures", "props"))
    has_prompt = isinstance(v, dict) and "prompt" in v
    if has_scene and has_prompt:
        return cfg.get_path("images.default_engine", "svg")
    return "gemini" if has_prompt else "svg"


def _key(shot: dict, engine: str, cfg: Config) -> str:
    payload = {"engine": engine, "visual": shot.get("visual")}
    if engine == "svg":
        payload["palette"] = cfg.get_path("channel.style.palette") or {}
    if engine == "gemini":
        payload["model"] = cfg.get_path("images.gemini.model")
        payload["prompt"] = build_prompt(shot.get("visual"), cfg.get_path("channel.prompt_style", ""))
    return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12]


def render_images(project: Project, cfg: Config, only: set[str] | None = None, force: bool = False) -> dict:
    shots = project.load_storyboard()["shots"]
    out_dir = project.shots_dir
    index_path = out_dir / "index.json"
    index = project.read_json(index_path) if index_path.exists() else {}

    todo: dict[str, list[tuple[dict, str]]] = {"svg": [], "gemini": []}
    missing = []
    for shot in shots:
        if only and shot["id"] not in only:
            continue
        if not shot.get("visual"):
            missing.append(shot["id"])
            continue
        eng = _engine_name(shot, cfg)
        key = _key(shot, eng, cfg)
        png = out_dir / f"{shot['id']}.png"
        if not force and png.exists() and index.get(shot["id"]) == key:
            continue
        todo.setdefault(eng, []).append((shot, key))

    if missing:
        print(f"  uyarı: {len(missing)} shot'un görsel planı yok (ilk: {missing[0]}) → boş kare kullanılacak")

    done = 0
    if todo.get("svg"):
        from .svg_engine import SvgEngine
        with SvgEngine(cfg) as eng:
            for shot, key in todo["svg"]:
                eng.render(shot, out_dir / f"{shot['id']}.png", seed=int(shot["id"][1:]) % 50 + 1)
                index[shot["id"]] = key
                done += 1
                project.write_json(index_path, index)
    if todo.get("gemini"):
        from .gemini_engine import GeminiEngine
        eng = GeminiEngine(cfg)
        workers = int(cfg.get_path("images.concurrency", 4))

        def job(item):
            shot, key = item
            eng.render(shot, out_dir / f"{shot['id']}.png")
            return shot["id"], key

        with ThreadPoolExecutor(max_workers=workers) as ex:
            for sid, key in ex.map(job, todo["gemini"]):
                index[sid] = key
                done += 1
                project.write_json(index_path, index)
                print(f"  gemini: {sid} hazır")
    total = sum(len(v) for v in todo.values())
    print(f"  görseller: {done}/{total} yeni üretildi, {len(shots) - total - len(missing)} önbellekten")
    return index
