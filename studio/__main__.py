"""Command line (the web panel runs these same commands in the background).

  python -m studio web                                   start the control panel (http://127.0.0.1:8765)
  python -m studio <step> <project> [--channel C] [--lang L] [--only s001,s002] [--force]

steps:
  split        script.md → storyboard.yaml (keeps planned visuals)
  plan         plan the scenes' pictures (Gemini or Anthropic API, or a manual prompt file)
  translate    shot-level translation for --lang (Gemini or Anthropic API, or a manual prompt)
  voice        narration for --lang
  align        timing of every shot for --lang
  images       paint the scene pictures (shared by all languages; unchanged scenes are never repainted)
  render       final 16:9 video for --lang
  shorts       vertical cut-downs listed in project.yaml → shorts
  describe     description.txt (chapters + sources) + captions.<lang>.srt for --lang
  package      titles, 3 thumbnail concepts, hooks and Shorts ideas from Gemini, then paints the thumbnails
  thumbnails   thumbnail variants from project.yaml → thumbnails (all languages, or --lang)
  captions     captions.<lang>.srt only
  dub          --lang tr: audio track fitted to the primary video (upload as an extra YouTube audio track)
  sheet        contact sheet: one tile per scene
  motion       living pictures: build/motion_sheet.png (pictures with a 0..1 grid, to plan motion.yaml) + plan status
  motion-preview  --only s020,s107: strip.png, motion.png (red = what moves), preview.mp4 → build/motion_preview/
  motion-plan  signature motion scenes from the channel rules (cold open, case file, verdict; runs after `plan` too)
  motion-prompt  data motion scenes (key numbers, quotes, timelines) via planner.provider or a prompt for Claude
  motion-auto  motion-plan, then motion-prompt when the video has fewer data scenes than the channel asks for
  motion-scenes  --only s004,s179: motion scenes (Remotion) with the real timing → build/remotion_preview/<id>.mp4
  sound        sound plan for --lang (ambience beds + effects; needs voice + align) → build/<lang>/sound_plan.json
  check        quality gate (research, sources, variety)
  upload       publish on YouTube [VIDEO_ID|URL] [--at "YYYY-MM-DD HH:MM" | --at now]: metadata, thumbnail,
               captions, playlist, release time (see studio/youtube.py for the one-time setup)
  all          split → voice → align → images → render (+ describe) for --lang
  status       short summary

other:
  update                                                  safe update from GitHub (keeps local changes)
  signals [--channel C] [--limit N] [--only i001,i002] [--force]   YouTube demand/competition for ideas
  check-links                                             check every URL in library/sources.yaml
  new-channel <id> --name "Name" [--langs en,tr]
  new <title> [--channel C]                               create a project
  apply-plan <project> FILE / apply-translation <project> FILE --lang L
  branding [--channel C] [--force]                        profile picture, banner, watermark (build/branding/)
  knowledge [--channel C]                                 channel bible for any chatbot (build/knowledge.md)
  youtube-login [--channel C]                             connect the channel to the YouTube API (browser consent)
  sounds-demo                                             every sound in one file to listen to (build/sounds_demo.wav)
  sounds-fetch [--only id1,id2]                           download the library's free sound files (library/sounds)
  remotion-setup                                          install the motion-scene packages (needs Node.js)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .config import default_channel, load_config
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
    ap.add_argument("--stash", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--at", default=None)
    a = ap.parse_args(argv)
    t0 = time.time()
    cmd = a.command
    from .channel import resolve_channel_id
    channel = resolve_channel_id(a.channel) if a.channel else default_channel()

    if cmd == "remotion-setup":
        from .remotion import install, status
        ok = install()
        print(f"  {status()[1]}")
        sys.exit(0 if ok else 1)
    if cmd == "update":
        from .updater import update
        sys.exit(update())
    if cmd == "update-restore":
        from .updater import restore
        sys.exit(restore(a.stash))
    if cmd == "web":
        from .web.app import serve
        serve()
        return
    if cmd == "branding":
        from .branding import render_branding
        render_branding(channel, load_config(channel), force=a.force)
        return
    if cmd == "youtube-login":
        from .youtube import YouTubeError, login
        try:
            login(channel)
        except YouTubeError as e:
            sys.exit(f"  {e}")
        return
    if cmd == "knowledge":
        from .knowledge import write_knowledge
        print(f"  {write_knowledge(channel, load_config(channel))}")
        return
    if cmd == "signals":
        from .signals import update_signals
        update_signals(channel, limit=a.limit, ids=[x for x in (a.only or "").split(",") if x] or None, force=a.force)
        return
    if cmd == "check-links":
        from .claims import check_links
        for ln in check_links():
            print(f"  {ln}")
        return
    if cmd == "sounds-demo":
        from .config import ROOT
        from .sound import demo
        out = demo(ROOT / "build" / "sounds_demo.wav")
        print(f"  {out}\n  içindekiler: {out.with_suffix('.txt')}")
        return
    if cmd == "sounds-fetch":
        from .sound.catalog import fetch
        for sid, st in fetch([x for x in (a.only or "").split(",") if x] or None).items():
            print(f"  {sid}: {st}")
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
        from .images import scenes
        groups = scenes(sb["shots"])
        planned = sum(1 for g in groups if g[0].get("visual"))
        print(f"  storyboard: {len(sb['shots'])} cümle parçası, {planned} planlı sahne")

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
        if p.meta.get("shorts"):
            from .render import render_shorts
            print("[shorts]")
            render_shorts(p, cfg, lang)
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
    elif cmd == "thumbnails":
        from .thumbnails import render_thumbnails
        render_thumbnails(p, cfg, a.lang)
    elif cmd == "package":
        from .thumbnails import make_package
        make_package(p, cfg)
    elif cmd == "dub":
        from .dub import make_dub
        make_dub(p, cfg, lang)
    elif cmd == "captions":
        from .render import write_srt
        print(f"  {write_srt(p, lang)}")
    elif cmd == "describe":
        from .render import describe
        print(f"  {describe(p, cfg, lang)}")
    elif cmd == "upload":
        from .youtube import YouTubeError, publish_video
        try:
            publish_video(p, cfg, lang, video=a.file, at=a.at, force=a.force)
        except YouTubeError as e:
            sys.exit(f"  {e}")
    elif cmd == "sound":
        from .images import scenes
        from .sound import make_plan
        timing = p.read_json(p.timing_path(lang))
        shots = {s["id"]: s for s in p.load_storyboard()["shots"]}
        groups = scenes([shots[t["id"]] for t in timing if t["id"] in shots])
        sp = make_plan(p, cfg, lang, groups, timing)
        s = sp["summary"]
        print(f"  ortam sesi: %{s['amb_coverage'] * 100:.0f} kapsama · {', '.join(s['amb_kinds'])}")
        print(f"  efekt: {s['sfx_count']} ({s['sfx_per_min']:.1f}/dk)")
        for e in sp["sfx"]:
            print(f"    {e['t']:7.2f} sn  {e['id']:<10} {e['why']}")
    elif cmd == "motion":
        from .images import scenes
        from .motion import load_plan, motion_sheet, plan_path
        plan = load_plan(p)
        groups = [g for g in scenes(p.load_storyboard()["shots"]) if (p.shots_dir / f"{g[0]['id']}.png").exists()]
        print(f"  {motion_sheet(p)}")
        print(f"  plan: {plan_path(p)} — {sum(1 for g in groups if g[0]['id'] in plan)}/{len(groups)} sahne planlı "
              f"(planı olmayanlar '{cfg.get_path('video.motion_preset', 'painterly')}' ön ayarıyla hareket eder)")
    elif cmd in ("motion-plan", "motion-auto"):
        from .motion_rules import apply_signature, data_scenes, rules_for, run_data
        if not rules_for(cfg, p):
            sys.exit("Bu kanalda hareketli sahne kuralı yok (channel.yaml → remotion.scenes).")
        for ln in apply_signature(p, cfg):
            print(f"  {ln}")
        d = (rules_for(cfg, p).get("data") or {})
        n = len(data_scenes(p.load_storyboard()["shots"]))
        short = n < d.get("min", 2)
        print(f"  rakam sahnesi: {n} (hedef {d.get('min', 2)}–{d.get('max', 5)})"
              + (" → 'motion-prompt' ile ekle" if short and cmd == "motion-plan" else ""))
        if short and cmd == "motion-auto":
            print(f"  {run_data(p, cfg)}")
    elif cmd == "motion-prompt":
        from .motion_rules import run_data
        print(f"  {run_data(p, cfg)}")
    elif cmd == "motion-scenes":
        from .remotion import preview as remotion_preview
        for out in remotion_preview(p, cfg, only, lang):
            print(f"  {out}")
    elif cmd == "motion-preview":
        from .motion import preview_scenes
        for out in preview_scenes(p, cfg, only):
            print(f"  {out}")
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
