"""Local control panel: FastAPI backend + static single-page frontend (studio/web/static).

Runs only on this computer (127.0.0.1). Start with:  python -m studio web   (or start.bat / start.sh)
"""
from __future__ import annotations

import os
import re
import webbrowser
from pathlib import Path
from typing import Any

import yaml
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from ..channel import IDEA_STATUSES, Channel, create_channel, list_channels, resolve_channel_id
from ..config import CHANNELS, ROOT, load_config, load_global, secrets_status, set_secret
from ..project import Project, create_project
from .jobs import STEP_LABELS, manager

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="Video Fabrikası", docs_url="/api/docs")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

SAFE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")


def _ch(cid: str) -> Channel:
    if SAFE.match(cid):
        cid = resolve_channel_id(cid)
    if not SAFE.match(cid) or not Channel(cid).exists():
        raise HTTPException(404, f"kanal yok: {cid}")
    return Channel(cid)


def _pr(cid: str, slug: str) -> Project:
    cid = _ch(cid).id
    p = Project(cid, slug)
    if not SAFE.match(slug) or not p.exists():
        raise HTTPException(404, f"proje yok: {slug}")
    return p


def _yaml(text: str) -> Any:
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise HTTPException(400, f"YAML hatası: {e}")


def _file_url(path: Path) -> str | None:
    if not path.exists():
        return None
    rel = path.resolve().relative_to(ROOT.resolve()).as_posix()
    return f"/files/{rel}?v={int(path.stat().st_mtime)}"


# ------------------------------------------------------------------ pages & files
@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/files/{path:path}")
def files(path: str):
    target = (ROOT / path).resolve()
    allowed = [CHANNELS.resolve(), (ROOT / "docs").resolve(), (ROOT / "assets").resolve()]
    if not any(str(target).startswith(str(a) + os.sep) for a in allowed) or not target.is_file():
        raise HTTPException(404)
    if target.name in (".env",) or target.suffix in (".py",):
        raise HTTPException(403)
    return FileResponse(target)


# ------------------------------------------------------------------ overview & settings
def _providers(cfg) -> dict:
    return {"tts": cfg.get_path("tts.provider"), "tts_by_lang": cfg.get_path("tts.provider_by_lang") or {},
            "images": cfg.get_path("images.default_engine"), "gemini_model": cfg.get_path("images.gemini.model"),
            "planner": cfg.get_path("planner.provider")}


@app.get("/api/ping")
def ping() -> dict:
    return {"app": "video-fabrikasi", "pid": os.getpid()}


@app.post("/api/shutdown")
def shutdown() -> dict:
    """Used by a newly started panel to replace an old one still running in another window."""
    import threading
    threading.Timer(0.3, lambda: os._exit(0)).start()
    return {"ok": True}


@app.get("/api/overview")
def overview():
    chans = []
    for ch in list_channels():
        ideas = ch.load_ideas()["ideas"]
        by = {s: 0 for s in IDEA_STATUSES}
        for i in ideas:
            by[i.get("status", "idea")] = by.get(i.get("status", "idea"), 0) + 1
        videos = sum(1 for s in ch.project_slugs() for lg in ch.languages if Project(ch.id, s).video_path(lg).exists())
        d = ch.data
        chans.append({"id": ch.id, "name": d.get("name", ch.id), "tagline": d.get("tagline", ""),
                      "languages": ch.languages, "category": d.get("category", ""), "ideas": len(ideas),
                      "ideas_by_status": by, "projects": len(ch.project_slugs()), "videos": videos})
    cfg = load_global()
    return {"channels": chans, "jobs": manager.list(8), "secrets": secrets_status(), "providers": _providers(cfg)}


@app.get("/api/settings")
def get_settings():
    return {"config_yaml": (ROOT / "config.yaml").read_text(encoding="utf-8"), "secrets": secrets_status(),
            "providers": _providers(load_global())}


@app.put("/api/settings")
def put_settings(body: dict = Body(...)):
    text = body.get("config_yaml", "")
    if not isinstance(_yaml(text), dict):
        raise HTTPException(400, "config.yaml bir sözlük olmalı")
    (ROOT / "config.yaml").write_text(text, encoding="utf-8")
    return {"ok": True}


@app.put("/api/secrets")
def put_secret(body: dict = Body(...)):
    try:
        set_secret(body["name"], body.get("value", ""))
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    return {"secrets": secrets_status()}


@app.get("/api/catalog")
def catalog():
    from ..svgkit import catalog as cat
    imgs = {n: _file_url(ROOT / "docs" / "catalog" / f"{n}.png") for n in ("poses", "props", "backgrounds")}
    return {**cat(), "images": imgs}


@app.post("/api/preview-svg", response_class=PlainTextResponse)
def preview_svg(body: dict = Body(...)):
    """Instant scene preview for the shot editor (no rasterising)."""
    from ..svgkit import render_svg
    from ..svgkit.style import use_palette
    visual = body.get("visual")
    if isinstance(visual, str):
        visual = _yaml(visual)
    if not isinstance(visual, dict) or "prompt" in visual and "bg" not in visual:
        raise HTTPException(400, "Önizleme sadece kodla çizilen sahneler (bg/figures/props) için.")
    palette = {}
    if body.get("channel"):
        palette = load_config(body["channel"]).get_path("channel.style.palette") or {}
    try:
        with use_palette(palette):
            return render_svg(visual)
    except Exception as e:
        raise HTTPException(400, f"Sahne çizilemedi: {e}")


# ------------------------------------------------------------------ channels
@app.post("/api/channels")
def new_channel(body: dict = Body(...)):
    try:
        ch = create_channel(body["id"], body.get("name") or body["id"], body.get("languages") or ["en"],
                            tagline=body.get("tagline", ""))
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    return {"id": ch.id}


@app.get("/api/channels/{cid}")
def get_channel(cid: str):
    ch = _ch(cid)
    return {"id": ch.id, "data": ch.data, "yaml": ch.path.read_text(encoding="utf-8"),
            "pillars": ch.load_ideas().get("pillars", {}), "statuses": IDEA_STATUSES}


@app.put("/api/channels/{cid}")
def put_channel(cid: str, body: dict = Body(...)):
    ch = _ch(cid)
    data = _yaml(body.get("yaml", ""))
    if not isinstance(data, dict) or not data.get("languages"):
        raise HTTPException(400, "channel.yaml geçersiz (languages gerekli)")
    ch.path.write_text(body["yaml"], encoding="utf-8")
    return {"ok": True}


# ------------------------------------------------------------------ ideas
@app.get("/api/channels/{cid}/ideas")
def get_ideas(cid: str):
    data = _ch(cid).load_ideas()
    return {"pillars": data.get("pillars", {}), "ideas": data["ideas"], "statuses": IDEA_STATUSES}


@app.post("/api/channels/{cid}/ideas")
def add_idea(cid: str, body: dict = Body(...)):
    ch = _ch(cid)
    data = ch.load_ideas()
    nums = [int(i["id"][1:]) for i in data["ideas"] if str(i.get("id", "")).startswith("i") and i["id"][1:].isdigit()]
    idea = {"id": f"i{(max(nums) + 1) if nums else 1:03d}", "title": body.get("title", "").strip(),
            "pillar": body.get("pillar", ""), "priority": body.get("priority", "B"),
            "angle": body.get("angle", ""), "status": "idea"}
    if not idea["title"]:
        raise HTTPException(400, "başlık gerekli")
    data["ideas"].append(idea)
    ch.save_ideas(data)
    return idea


@app.patch("/api/channels/{cid}/ideas/{iid}")
def patch_idea(cid: str, iid: str, body: dict = Body(...)):
    ch = _ch(cid)
    data = ch.load_ideas()
    for idea in data["ideas"]:
        if idea["id"] == iid:
            for k in ("title", "pillar", "priority", "angle", "status", "notes", "project", "gut", "query"):
                if k in body:
                    idea[k] = body[k]
            ch.save_ideas(data)
            return idea
    raise HTTPException(404, "fikir yok")


@app.post("/api/channels/{cid}/ideas/{iid}/project")
def idea_to_project(cid: str, iid: str):
    ch = _ch(cid)
    data = ch.load_ideas()
    idea = next((i for i in data["ideas"] if i["id"] == iid), None)
    if not idea:
        raise HTTPException(404, "fikir yok")
    if idea.get("project") and Project(cid, idea["project"]).exists():
        return {"slug": idea["project"]}
    p = create_project(cid, idea["title"], idea_id=iid)
    if idea.get("angle"):
        p.script_path.write_text(p.script_path.read_text(encoding="utf-8").replace(
            "<!-- Narration.", f"<!-- Angle: {idea['angle']} -->\n<!-- Narration."), encoding="utf-8")
    idea["status"], idea["project"] = "scripting", p.slug
    ch.save_ideas(data)
    return {"slug": p.slug}


# ------------------------------------------------------------------ projects
def _project_summary(p: Project) -> dict:
    from ..readiness import check
    try:
        r = check(p)
    except SystemExit:
        r = {"ready": False, "checks": []}
    shots = []
    if p.storyboard_path.exists():
        shots = p.load_storyboard().get("shots", [])
    first = next((p.shots_dir / f"{s['id']}.png" for s in shots if (p.shots_dir / f"{s['id']}.png").exists()), None)
    return {"slug": p.slug, "title": p.meta.get("title", p.slug), "status": p.meta.get("status", ""),
            "shots": len(shots), "ready": r["ready"],
            "blocks": [c["message"] for c in r["checks"] if c["level"] == "block" and not c["ok"]],
            "thumb": _file_url(first) if first else None,
            "videos": {lg: _file_url(p.video_path(lg)) for lg in p.ch.languages}}


@app.get("/api/channels/{cid}/projects")
def list_projects(cid: str):
    ch = _ch(cid)
    return [_project_summary(Project(cid, s)) for s in reversed(ch.project_slugs())]


@app.post("/api/channels/{cid}/projects")
def new_project(cid: str, body: dict = Body(...)):
    _ch(cid)
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "başlık gerekli")
    return {"slug": create_project(cid, title).slug}


@app.get("/api/projects/{cid}/{slug}")
def get_project(cid: str, slug: str):
    from ..readiness import check
    p = _pr(cid, slug)
    sb = p.load_storyboard() if p.storyboard_path.exists() else {"shots": []}
    langs = p.ch.languages
    timings = {}
    for lg in langs:
        if p.timing_path(lg).exists():
            timings[lg] = {t["id"]: t for t in p.read_json(p.timing_path(lg))}
    shots = []
    for s in sb.get("shots", []):
        img = p.shots_dir / f"{s['id']}.png"
        t = timings.get(langs[0], {}).get(s["id"])
        shots.append({**s, "image": _file_url(img), "start": t["start"] if t else None,
                      "visual_yaml": yaml.safe_dump(s.get("visual"), allow_unicode=True, sort_keys=False,
                                                    default_flow_style=None, width=100) if s.get("visual") else ""})
    outputs = {}
    for lg in langs:
        d = p.lang_dir(lg)
        shorts = sorted((d / "shorts").glob("short*.mp4")) if (d / "shorts").exists() else []
        desc = d / "description.txt"
        outputs[lg] = {"video": _file_url(p.video_path(lg)), "shorts": [_file_url(x) for x in shorts],
                       "description": desc.read_text(encoding="utf-8") if desc.exists() else "",
                       "narration": _file_url(p.audio_dir(lg) / "narration.wav")}
    from ..claims import library_index, load_claims
    from ..publish import HOOK_TYPES, get_publish
    from ..retention import analyze
    lib = library_index()
    claims = [{**c, "src": lib.get(c.get("source")) or None} for c in load_claims(p)["claims"]]
    thumbs = {lg: [_file_url(x) for x in sorted((p.build / "thumbnails" / lg).glob("thumb[0-9].png"))]
              for lg in langs}
    for lg in langs:
        outputs[lg]["captions"] = _file_url(p.lang_dir(lg) / f"captions.{lg}.srt")
        outputs[lg]["dub"] = _file_url(p.lang_dir(lg) / f"dub_track.{lg}.wav")
        outputs[lg]["thumb_preview"] = _file_url(p.build / "thumbnails" / lg / "preview.png")
    ch_data = p.ch.data
    extra = {"claims": claims, "library_size": len(lib), "publish": get_publish(p), "hook_types": HOOK_TYPES,
             "series": ch_data.get("series") or {}, "thumbs": thumbs,
             "thumbnails_yaml": yaml.safe_dump(p.meta.get("thumbnails") or [], allow_unicode=True, sort_keys=False,
                                               default_flow_style=None, width=110) if p.meta.get("thumbnails") else "",
             "retention": {lg: analyze(p, lg) for lg in langs}}
    return {**extra, "channel": cid, "slug": slug, "meta": p.meta, "meta_yaml": p.meta_path.read_text(encoding="utf-8")
            if p.meta_path.exists() else "", "script": p.script_path.read_text(encoding="utf-8"),
            "sources": p.sources_path.read_text(encoding="utf-8") if p.sources_path.exists() else "",
            "languages": langs, "shots": shots, "readiness": check(p), "outputs": outputs,
            "sheet": _file_url(p.build / "contact_sheet.png"), "jobs": manager.active_for(cid, slug)}


@app.put("/api/projects/{cid}/{slug}/script")
def put_script(cid: str, slug: str, body: dict = Body(...)):
    _pr(cid, slug).script_path.write_text(body.get("text", ""), encoding="utf-8")
    return {"ok": True}


@app.put("/api/projects/{cid}/{slug}/sources")
def put_sources(cid: str, slug: str, body: dict = Body(...)):
    _pr(cid, slug).sources_path.write_text(body.get("text", ""), encoding="utf-8")
    return {"ok": True}


@app.put("/api/projects/{cid}/{slug}/meta")
def put_meta(cid: str, slug: str, body: dict = Body(...)):
    p = _pr(cid, slug)
    data = _yaml(body.get("yaml", ""))
    if not isinstance(data, dict):
        raise HTTPException(400, "project.yaml bir sözlük olmalı")
    p.meta_path.write_text(body["yaml"], encoding="utf-8")
    return {"ok": True}


@app.put("/api/projects/{cid}/{slug}/shots/{sid}")
def put_shot(cid: str, slug: str, sid: str, body: dict = Body(...)):
    p = _pr(cid, slug)
    sb = p.load_storyboard()
    shot = next((s for s in sb["shots"] if s["id"] == sid), None)
    if not shot:
        raise HTTPException(404, "shot yok")
    if "visual_yaml" in body:
        v = _yaml(body["visual_yaml"]) if body["visual_yaml"].strip() else None
        shot["visual"] = v
    for k in ("engine", "camera"):
        if k in body:
            if body[k]:
                shot[k] = body[k]
            else:
                shot.pop(k, None)
    if "overlay" in body:
        if isinstance(body["overlay"], dict) and body["overlay"].get("text"):
            shot["overlay"] = body["overlay"]
        else:
            shot.pop("overlay", None)
    if "i18n" in body and isinstance(body["i18n"], dict):
        shot.setdefault("i18n", {}).update({k: v for k, v in body["i18n"].items() if v})
    p.save_storyboard(sb)
    job = None
    if body.get("render") and shot.get("visual"):
        job = manager.submit(["images", slug, "--channel", cid, "--only", sid, "--force"],
                             f"Görsel {sid}", cid, slug).id
    return {"ok": True, "job": job}


@app.get("/api/projects/{cid}/{slug}/prompt/{kind}", response_class=PlainTextResponse)
def get_prompt(cid: str, slug: str, kind: str, lang: str = "tr"):
    p = _pr(cid, slug)
    if kind == "plan":
        from ..planner import build_prompt
        return build_prompt(p)
    if kind == "translate":
        from ..translate import build_prompt as tprompt
        return tprompt(p, lang)
    if kind == "claims":
        from ..claims import build_prompt as cprompt
        return cprompt(p)
    if kind == "package":
        from ..thumbnails import build_package_prompt
        return build_package_prompt(p)
    raise HTTPException(404)


@app.post("/api/projects/{cid}/{slug}/apply/{kind}")
def apply(cid: str, slug: str, kind: str, body: dict = Body(...)):
    from ..planner import apply_plan, parse_yaml_reply
    p = _pr(cid, slug)
    try:
        data = parse_yaml_reply(body.get("text", ""))
    except Exception as e:
        raise HTTPException(400, f"YAML okunamadı: {e}")
    if kind == "plan":
        return {"updated": apply_plan(p, data)}
    if kind == "translation":
        from ..translate import apply_translation
        return {"updated": apply_translation(p, body.get("lang", "tr"), data)}
    if kind == "claims":
        from ..claims import apply_reply
        return apply_reply(p, data)
    if kind == "package":
        from ..thumbnails import apply_package
        return apply_package(p, data)
    raise HTTPException(404)


@app.put("/api/projects/{cid}/{slug}/claims")
def put_claims(cid: str, slug: str, body: dict = Body(...)):
    """Toggle verified / edit fields of one claim: {id, verified?, quote?, caveat?, shots?}"""
    from ..claims import load_claims, save_claims
    p = _pr(cid, slug)
    data = load_claims(p)
    for c in data["claims"]:
        if c.get("id") == body.get("id"):
            for k in ("verified", "quote", "caveat", "shots", "text", "source", "on_screen"):
                if k in body:
                    c[k] = body[k]
            save_claims(p, data)
            return c
    raise HTTPException(404, "iddia yok")


@app.put("/api/projects/{cid}/{slug}/thumbnails")
def put_thumbnails(cid: str, slug: str, body: dict = Body(...)):
    p = _pr(cid, slug)
    data = _yaml(body.get("yaml", "")) if body.get("yaml", "").strip() else []
    if not isinstance(data, list):
        raise HTTPException(400, "kapaklar bir liste olmalı (- visual: ...)")
    meta = p.meta
    meta["thumbnails"] = data[:3]
    p.save_meta(meta)
    job = manager.submit(["thumbnails", slug, "--channel", p.channel], "Kapak görselleri", p.channel, slug).id \
        if body.get("render") else None
    return {"ok": True, "job": job}


@app.get("/api/projects/{cid}/{slug}/publish")
def get_pub(cid: str, slug: str):
    from ..publish import get_publish
    return get_publish(_pr(cid, slug))


@app.put("/api/projects/{cid}/{slug}/publish")
def put_pub(cid: str, slug: str, body: dict = Body(...)):
    from ..publish import save_publish
    return save_publish(_pr(cid, slug), body)


@app.post("/api/projects/{cid}/{slug}/metrics")
def post_metrics(cid: str, slug: str, body: dict = Body(...)):
    from ..publish import add_metrics
    return add_metrics(_pr(cid, slug), body)


@app.post("/api/projects/{cid}/{slug}/retention")
def post_retention(cid: str, slug: str, body: dict = Body(...)):
    from ..retention import import_retention
    p = _pr(cid, slug)
    lang = body.get("lang") or p.primary_lang()
    if not p.timing_path(lang).exists():
        raise HTTPException(400, f"[{lang}] zamanlama yok: önce videoyu üret (zamanlama adımı)")
    try:
        return import_retention(p, lang, body.get("text", ""))
    except ValueError as e:
        raise HTTPException(400, f"Veri okunamadı: {e}")


# ------------------------------------------------------------------ calendar & library
@app.get("/api/channels/{cid}/calendar")
def get_calendar(cid: str, weeks: int = 8, offset: int = 0):
    from datetime import date, timedelta

    from ..schedule import calendar
    ch = _ch(cid)
    return calendar(ch.id, weeks=max(1, min(weeks, 26)), start=date.today() + timedelta(weeks=offset))


@app.post("/api/channels/{cid}/calendar/assign")
def assign_slot(cid: str, body: dict = Body(...)):
    from ..schedule import assign
    ch = _ch(cid)
    slug = body.get("slug", "")
    if not SAFE.match(slug) or not Project(ch.id, slug).exists():
        raise HTTPException(404, "proje yok")
    assign(ch.id, slug, body.get("date") or None)
    return {"ok": True}


@app.post("/api/channels/{cid}/signals")
def run_signals(cid: str, body: dict = Body(default={})):
    ch = _ch(cid)
    args = ["signals", "--channel", ch.id]
    if body.get("limit"):
        args += ["--limit", str(int(body["limit"]))]
    if body.get("ids"):
        args += ["--only", ",".join(i for i in body["ids"] if re.match(r"^i\d+$", i))]
    if body.get("force"):
        args.append("--force")
    return {"job": manager.submit(args, STEP_LABELS["signals"], ch.id, None).id}


@app.get("/api/library")
def get_library():
    from ..claims import load_library
    used: dict[str, list[str]] = {}
    from ..claims import load_claims
    for ch in list_channels():
        for s in ch.project_slugs():
            for c in load_claims(Project(ch.id, s))["claims"]:
                used.setdefault(c.get("source") or "", []).append(f"{ch.id}/{s}")
    lib = load_library()
    return {"sources": [{**s, "used_by": sorted(set(used.get(s.get("id"), [])))} for s in lib["sources"]],
            "yaml": (ROOT / "library" / "sources.yaml").read_text(encoding="utf-8") if (ROOT / "library" / "sources.yaml").exists() else ""}


@app.put("/api/library")
def put_library(body: dict = Body(...)):
    data = _yaml(body.get("yaml", ""))
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise HTTPException(400, "sources: listesi gerekli")
    ids = [s.get("id") for s in data["sources"] if isinstance(s, dict)]
    if len(ids) != len(set(ids)) or not all(ids):
        raise HTTPException(400, "her kaynağın benzersiz bir id'si olmalı")
    (ROOT / "library").mkdir(exist_ok=True)
    (ROOT / "library" / "sources.yaml").write_text(body["yaml"], encoding="utf-8")
    return {"ok": True}


@app.post("/api/projects/{cid}/{slug}/run")
def run_step(cid: str, slug: str, body: dict = Body(...)):
    _pr(cid, slug)
    step = body.get("step")
    if step not in STEP_LABELS:
        raise HTTPException(400, f"bilinmeyen adım: {step}")
    args = [step, slug, "--channel", cid]
    if body.get("lang"):
        args += ["--lang", body["lang"]]
    if body.get("only"):
        args += ["--only", body["only"]]
    if body.get("force"):
        args.append("--force")
    label = STEP_LABELS[step] + (f" [{body['lang']}]" if body.get("lang") else "")
    return {"job": manager.submit(args, label, cid, slug).id}


@app.post("/api/compile")
def compile_(body: dict = Body(...)):
    cid = body["channel"]
    _ch(cid)
    slugs = [s for s in body.get("slugs", []) if SAFE.match(s)]
    if len(slugs) < 2:
        raise HTTPException(400, "en az 2 video seç")
    args = ["compile", ",".join(slugs), "--channel", cid, "--title", body.get("title") or "compilation"]
    if body.get("lang"):
        args += ["--lang", body["lang"]]
    return {"job": manager.submit(args, "Derleme", cid, None).id}


@app.post("/api/tools/{tool}")
def tools(tool: str, body: dict = Body(default={})):
    if tool not in ("catalog", "refs", "check-links"):
        raise HTTPException(404)
    args = [tool] + (["--channel", body["channel"]] if body.get("channel") else [])
    return {"job": manager.submit(args, STEP_LABELS[tool]).id}


# ------------------------------------------------------------------ jobs
@app.get("/api/jobs")
def jobs():
    return manager.list(40)


@app.get("/api/jobs/{jid}")
def job(jid: int, since: int = 0):
    j = manager.jobs.get(jid)
    if not j:
        raise HTTPException(404)
    return j.public(since)


@app.post("/api/jobs/{jid}/cancel")
def cancel(jid: int):
    return {"ok": manager.cancel(jid)}


def _port_free(host: str, port: int) -> bool:
    """True when nothing is listening on host:port (connect test; immune to TIME_WAIT leftovers)."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) != 0


def _replace_running_panel(host: str, port: int) -> bool:
    """If an older panel already holds the port (e.g. start.bat opened twice), shut it down. True = port now free."""
    import json
    import time
    import urllib.request
    base = f"http://{host}:{port}"
    try:
        with urllib.request.urlopen(base + "/api/ping", timeout=2) as r:
            if json.loads(r.read()).get("app") != "video-fabrikasi":
                return False
        print("  Açık kalmış eski bir panel bulundu, kapatılıp yenisi başlatılıyor...")
        urllib.request.urlopen(urllib.request.Request(base + "/api/shutdown", method="POST"), timeout=2).read()
    except Exception:
        return False
    for _ in range(30):
        time.sleep(0.2)
        if _port_free(host, port):
            return True
    return False


def serve() -> None:
    import uvicorn
    cfg = load_global()
    host, port = cfg.get_path("factory.host", "127.0.0.1"), int(cfg.get_path("factory.port", 8765))
    url = f"http://{host}:{port}"
    try:
        from ..migrate import migrate_renamed_channels
        migrate_renamed_channels()
    except Exception as e:  # never block the panel
        print(f"  [taşıma] atlandı: {e}")
    if not _port_free(host, port) and not _replace_running_panel(host, port):
        print(f"\n  [!] {port} numaralı bağlantı noktası başka bir program tarafından kullanılıyor.\n"
              f"      Açık kalmış bir panel penceresi varsa kapat ya da config.yaml → factory.port değerini değiştir.\n")
        raise SystemExit(1)
    print(f"\n  Video Fabrikası çalışıyor → {url}\n  (kapatmak için bu pencerede Ctrl+C)\n")
    if os.environ.get("STUDIO_NO_BROWSER") != "1":
        try:
            webbrowser.open(url)
        except Exception:
            pass
    uvicorn.run(app, host=host, port=port, log_level="warning")
