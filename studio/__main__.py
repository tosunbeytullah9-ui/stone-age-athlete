"""Command line (the web panel runs these same commands in the background).

  python -m studio web                                   start the control panel (http://127.0.0.1:8765)
  python -m studio <step> <project> [--channel C] [--lang L] [--only s001,s002] [--force]

steps:
  split        script.md → storyboard.yaml (keeps planned visuals)
  plan         plan visuals (manual prompt file, or Anthropic API)
  translate    shot-level translation for --lang (manual prompt, or Anthropic API)
  voice        narration for --lang
  align        timing of every shot for --lang
  images       render shot images (shared by all languages)
  render       final 16:9 video for --lang
  shorts       vertical cut-downs listed in project.yaml → shorts
  describe     description.txt (chapters + sources) for --lang
  sheet        contact sheet of all shot images
  check        quality gate (research, sources, variety)
  all          split → voice → align → images → render (+ describe) for --lang
  status       short summary

other:
  new-channel <id> --name "Name" [--langs en,tr]
  new <title> [--channel C]                               create a project
  apply-plan <project> FILE / apply-translation <project> FILE --lang L
  compile <project,project,...> --title T [--lang L]      long compilation of finished videos
  catalog | refs
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .config import ASSETS, default_channel, load_config
from .project import Project, create_project


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="studio", description="Video factory", add_help=True)
    ap.add_argument("command")
    ap.add_argument("target", nargs="?")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--channel", default=None)
    ap.add_argument("--lang", default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--name", default=None)
    ap.add_argument("--langs", default="en")
    ap.add_argument("--title", default=None)
    a = ap.parse_args(argv)
    t0 = time.time()
    cmd = a.command
    channel = a.channel or default_channel()

    if cmd == "web":
        from .web.app import serve
        serve()
        return
    if cmd == "catalog":
        from .catalog import build_catalog
        for p in build_catalog():
            print(f"  {p}")
        return
    if cmd == "refs":
        from .images.svg_engine import SvgEngine
        from .svgkit import render_svg
        cfg = load_config(channel)
        (ASSETS / "refs").mkdir(parents=True, exist_ok=True)
        mascot = dict(cfg.get_path("channel.mascot") or {"pose": "point"})
        mascot.update({"x": 800, "scale": 1.4})
        with SvgEngine(cfg) as eng:
            eng.svg_to_png(render_svg({"bg": "plain_warm", "figures": [mascot]}), ASSETS / "refs" / "coach.png")
        print("  assets/refs/coach.png hazır")
        return
    if cmd == "new-channel":
        from .channel import create_channel
        ch = create_channel(a.target, a.name or a.target, [x.strip() for x in a.langs.split(",") if x.strip()])
        print(f"  kanal oluşturuldu: channels/{ch.id}")
        return
    if cmd == "new":
        p = create_project(channel, a.title or a.target or "Untitled")
        print(f"  proje oluşturuldu: {p.dir}")
        return
    if cmd == "compile":
        from .render import compile_videos
        cfg = load_config(channel)
        compile_videos(channel, [s for s in (a.target or "").split(",") if s], cfg,
                       a.lang or Project(channel, a.target.split(",")[0]).primary_lang(), a.title or "compilation")
        return

    if not a.target:
        sys.exit(__doc__)
    p = Project(channel, a.target)
    if not p.exists():
        sys.exit(f"Proje bulunamadı: channels/{channel}/projects/{a.target}")
    cfg = load_config(channel)
    lang = a.lang or p.primary_lang()
    only = set(a.only.split(",")) if a.only else None

    def step_split():
        from .storyboard import build_storyboard
        sb = build_storyboard(p, cfg)
        planned = sum(1 for s in sb["shots"] if s.get("visual"))
        print(f"  storyboard: {len(sb['shots'])} shot ({planned} planlı)")

    def step_voice():
        from .voice import make_voice
        make_voice(p, cfg, lang)

    def step_align():
        from .align import align
        align(p, cfg, lang)

    def step_images():
        from .images import render_images
        render_images(p, cfg, only=only, force=a.force)

    def step_render():
        from .render import render_video
        render_video(p, cfg, lang)

    steps = {"split": step_split, "voice": step_voice, "align": step_align, "images": step_images,
             "render": step_render}
    if cmd in steps:
        steps[cmd]()
    elif cmd == "all":
        for name in ("split", "voice", "align", "images", "render"):
            print(f"[{name}]")
            steps[name]()
    elif cmd == "plan":
        from .planner import plan
        plan(p, cfg)
    elif cmd == "translate":
        from .translate import translate
        translate(p, cfg, lang)
    elif cmd == "apply-plan":
        from .planner import apply_plan_file
        print(f"  {apply_plan_file(p, Path(a.file))} shot güncellendi")
    elif cmd == "apply-translation":
        from .planner import parse_yaml_reply
        from .translate import apply_translation
        n = apply_translation(p, lang, parse_yaml_reply(Path(a.file).read_text(encoding="utf-8")))
        print(f"  {n} shot çevrildi [{lang}]")
    elif cmd == "shorts":
        from .render import render_shorts
        render_shorts(p, cfg, lang)
    elif cmd == "describe":
        from .render import describe
        print(f"  {describe(p, cfg, lang)}")
    elif cmd == "sheet":
        from .render import contact_sheet
        print(f"  {contact_sheet(p)}")
    elif cmd == "check":
        from .readiness import check
        r = check(p)
        for c in r["checks"]:
            mark = "✓" if c["ok"] else {"block": "✗", "warn": "!"}.get(c["level"], "·")
            print(f"  {mark} {c['message']}")
        print("  HAZIR" if r["ready"] else "  HAZIR DEĞİL")
    elif cmd == "status":
        from .readiness import check
        print(json.dumps(check(p), ensure_ascii=False, indent=1))
    else:
        sys.exit(__doc__)
    print(f"  ({time.time() - t0:.1f} sn)")


if __name__ == "__main__":
    main()
