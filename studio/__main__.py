"""Command line.  python -m studio <command> <slug>

  new <slug> [--title T]   create projects/<slug>/ with a script template
  split <slug>             script.md → storyboard.yaml (keeps existing visuals)
  plan <slug>              plan visuals (manual prompt file, or Anthropic API)
  apply-plan <slug> FILE   merge a planner YAML answer into the storyboard
  voice <slug>             narration audio (Kokoro / ElevenLabs / estimate)
  align <slug>             timing of every shot
  images <slug> [--only s001,s002] [--force]
  render <slug>            final video → projects/<slug>/build/video.mp4
  sheet <slug>             contact sheet of shot images
  all <slug>               split → voice → align → images → render
  status <slug>            what is done / missing
  catalog                  draw pose / prop / background catalogs into docs/catalog/
  refs                     draw character reference images into assets/refs/ (for Gemini)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import ASSETS, load_config
from .project import Project

TEMPLATE = """# {title}
<!-- Narration. Paragraphs are separated by a blank line. Lines starting with # are ignored. -->

Write the first paragraph of narration here.

Write the second paragraph here.
"""


def _project(slug: str, must_exist: bool = True) -> Project:
    p = Project(slug)
    if must_exist and not p.exists():
        sys.exit(f"Proje bulunamadı: projects/{slug}  (oluşturmak için: python -m studio new {slug})")
    return p


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="studio", description="Stone Age Athlete video studio")
    ap.add_argument("command")
    ap.add_argument("slug", nargs="?")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--title", default=None)
    ap.add_argument("--only", default=None, help="comma separated shot ids")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_config()
    t0 = time.time()
    cmd = a.command

    if cmd == "catalog":
        from .catalog import build_catalog
        for p in build_catalog():
            print(f"  {p}")
        return
    if cmd == "refs":
        from .images.svg_engine import SvgEngine
        from .svgkit import render_svg
        (ASSETS / "refs").mkdir(parents=True, exist_ok=True)
        coach = {"bg": "plain_warm", "figures": [{"pose": "point", "x": 800, "hold": "pointer", "face": "smile",
                                                  "wear": ["headband", "whistle"], "scale": 1.4}]}
        with SvgEngine() as eng:
            eng.svg_to_png(render_svg(coach), ASSETS / "refs" / "coach.png")
        print("  assets/refs/coach.png hazır")
        return
    if not a.slug:
        sys.exit("Proje adı gerekli. Örnek: python -m studio split 001-tougher")

    if cmd == "new":
        p = _project(a.slug, must_exist=False)
        p.dir.mkdir(parents=True, exist_ok=True)
        if not p.script_path.exists():
            p.script_path.write_text(TEMPLATE.format(title=a.title or a.slug), encoding="utf-8")
        print(f"  oluşturuldu: {p.script_path}")
        return

    p = _project(a.slug)
    only = set(a.only.split(",")) if a.only else None

    def step_split():
        from .storyboard import build_storyboard
        sb = build_storyboard(p, cfg)
        planned = sum(1 for s in sb["shots"] if s.get("visual"))
        print(f"  storyboard: {len(sb['shots'])} shot ({planned} planlı)")

    def step_voice():
        from .voice import make_voice
        make_voice(p, cfg)

    def step_align():
        from .align import align
        align(p, cfg)

    def step_images():
        from .images import render_images
        render_images(p, cfg, only=only, force=a.force)

    def step_render():
        from .render import render_video
        render_video(p, cfg)

    steps = {"split": step_split, "voice": step_voice, "align": step_align,
             "images": step_images, "render": step_render}
    if cmd in steps:
        steps[cmd]()
    elif cmd == "all":
        for name in ("split", "voice", "align", "images", "render"):
            print(f"[{name}]")
            steps[name]()
    elif cmd == "plan":
        from .planner import plan
        plan(p, cfg)
    elif cmd == "apply-plan":
        if not a.file:
            sys.exit("Plan dosyası gerekli: python -m studio apply-plan <slug> plan.yaml")
        from .planner import apply_plan_file
        print(f"  {apply_plan_file(p, Path(a.file))} shot güncellendi")
    elif cmd == "sheet":
        from .render import contact_sheet
        print(f"  {contact_sheet(p)}")
    elif cmd == "status":
        sb = p.load_storyboard()
        shots = sb["shots"]
        planned = sum(1 for s in shots if s.get("visual"))
        imgs = sum(1 for s in shots if (p.shots_dir / f"{s['id']}.png").exists())
        gem = sum(1 for s in shots if s.get("engine") == "gemini" or isinstance(s.get("visual"), str)
                  or (isinstance(s.get("visual"), dict) and "prompt" in s["visual"] and "bg" not in s["visual"]))
        print(f"  shot: {len(shots)} | planlı: {planned} | görseli olan: {imgs} | AI (gemini) shot: {gem}")
        print(f"  ses: {'var' if p.audio_manifest_path.exists() else 'yok'} | "
              f"zamanlama: {'var' if p.timing_path.exists() else 'yok'} | "
              f"video: {'var' if (p.build / 'video.mp4').exists() else 'yok'}")
    else:
        sys.exit(__doc__)
    print(f"  ({time.time() - t0:.1f} sn)")


if __name__ == "__main__":
    main()
