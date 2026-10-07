"""Publish a finished video on YouTube through the official YouTube Data API v3 (OAuth; no browser automation).

One-time setup (once per machine; the panel shows the same steps under Kanal → YouTube):
  1. console.cloud.google.com → new project → APIs & Services → Library → enable "YouTube Data API v3".
  2. OAuth consent screen: External; app name "Video Fabrikasi"; add the channel's Google account as a test user,
     then "Publish app" (In production). In "Testing" Google expires the login every 7 days.
  3. Credentials → Create credentials → OAuth client ID → Desktop app → Download JSON
     → save it as .fabrika/youtube/client_secret.json
  4. python -m studio youtube-login --channel C     a browser opens: pick the CHANNEL (the Brand Account), allow.

Then, after `all` + `describe` + `thumbnails`:
  python -m studio upload <slug> [VIDEO_ID|URL] [--at "2026-10-12 22:00" | --at now] [--force]

What upload does: title (publish.title_used or title), description.txt, tags, category, language, made-for-kids:
no, AI disclosure flag, the chosen thumbnail, captions.<lang>.srt, the series playlist (created on first use), and
the release: --at (local time of this computer), or publish.planned_date + youtube.publish_time, or else private.
The video id goes into project.yaml → publish.youtube_id.

Google locks videos uploaded through the API by an unaudited Cloud project as private. Until the project passes
Google's API audit (youtube.api_audited: true in channel.yaml), drag video.mp4 into YouTube Studio yourself, leave it
as a draft and give its id (or link) to `upload`: everything else is still filled in by the API.

State: token in .fabrika/youtube/<channel>.token.json (never committed); channel id + playlist ids in
channels/<channel>/youtube.yaml.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import time
import webbrowser
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import requests
import yaml

from .channel import Channel
from .config import ROOT, Config
from .project import Project

SECRETS_DIR = ROOT / ".fabrika" / "youtube"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl"
CHUNK = 8 * 1024 * 1024                 # resumable upload chunk (multiple of 256 KiB)
THUMB_MAX = 2 * 1024 * 1024             # YouTube thumbnail limit
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
AUDIT_FORM = "https://support.google.com/youtube/contact/yt_api_form"


class YouTubeError(RuntimeError):
    pass


# ------------------------------------------------------------------ settings
def settings(cfg: Config) -> dict[str, Any]:
    """channel.yaml → youtube, with defaults."""
    yt = {"category": 27, "language": "en", "made_for_kids": False, "synthetic_media": False, "tags": [],
          "publish_time": "22:00", "privacy": "private", "api_audited": False, "license": "youtube"}
    yt.update(cfg.get_path("channel.youtube") or {})
    return yt


def state_path(channel: str) -> Path:
    return Channel(channel).dir / "youtube.yaml"


def load_state(channel: str) -> dict[str, Any]:
    p = state_path(channel)
    data = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}
    data.setdefault("playlists", {})
    return data


def save_state(channel: str, data: dict[str, Any]) -> None:
    head = "# Written by `studio youtube-login` / `studio upload`: the channel this folder publishes to and its playlists.\n"
    state_path(channel).write_text(head + yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def parse_video_id(text: str | None) -> str | None:
    """A bare id or any youtube.com / youtu.be / Studio link → the 11-character id."""
    if not text:
        return None
    text = text.strip()
    if VIDEO_ID.match(text):
        return text
    u = urlparse(text if "://" in text else "https://" + text)
    if u.hostname and u.hostname.endswith("youtu.be"):
        cand = u.path.strip("/").split("/")[0]
    elif "v" in parse_qs(u.query):
        cand = parse_qs(u.query)["v"][0]
    else:
        parts = [x for x in u.path.split("/") if x]
        cand = next((parts[i + 1] for i, x in enumerate(parts[:-1]) if x in ("video", "shorts", "embed", "live")), "")
    if VIDEO_ID.match(cand or ""):
        return cand
    raise YouTubeError(f"YouTube video kimliği okunamadı: {text}")


# ------------------------------------------------------------------ OAuth
def _client() -> dict[str, str]:
    p = SECRETS_DIR / "client_secret.json"
    if not p.exists():
        raise YouTubeError(f"OAuth istemci dosyası yok: {p}\n  Kurulum adımları: python -m studio youtube-login --help "
                           "ya da studio/youtube.py dosyasının başı.")
    data = json.loads(p.read_text(encoding="utf-8"))
    c = data.get("installed") or data.get("web") or {}
    if not c.get("client_id"):
        raise YouTubeError("client_secret.json beklenen biçimde değil (Masaüstü uygulaması türünde oluştur).")
    return c


def _token_path(channel: str) -> Path:
    return SECRETS_DIR / f"{channel}.token.json"


def _save_token(channel: str, tok: dict[str, Any]) -> None:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    _token_path(channel).write_text(json.dumps(tok, indent=1), encoding="utf-8")


def login(channel: str, timeout: int = 300) -> dict[str, Any]:
    """Browser consent (loopback + PKCE). Stores the refresh token and the chosen channel's id."""
    c = _client()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    got: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = parse_qs(urlparse(self.path).query)
            if "code" in q or "error" in q:
                got.update({k: v[0] for k, v in q.items()})
                msg = "Video Fabrikasi: YouTube baglandi. Bu sekmeyi kapatabilirsin." if "code" in q else \
                      f"Video Fabrikasi: izin verilmedi ({q['error'][0]})."
            else:
                msg = ""
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(msg.encode())

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 5
    redirect = f"http://127.0.0.1:{server.server_port}/"
    url = AUTH_URL + "?" + urlencode({
        "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent select_account", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    print("  Tarayıcıda Google izin sayfası açılıyor. Hesap seçerken KANALI (Homo Athleticus marka hesabını) seç.")
    print(f"  Açılmazsa bu adresi kopyala:\n  {url}")
    webbrowser.open(url)
    end = time.time() + timeout
    while not got and time.time() < end:
        server.handle_request()
    server.server_close()
    if "code" not in got:
        raise YouTubeError(f"Google izni alınamadı: {got.get('error', 'zaman aşımı')}")
    if got.get("state") != state:
        raise YouTubeError("Güvenlik kontrolü tutmadı (state). Tekrar dene.")
    r = requests.post(TOKEN_URL, data={
        "code": got["code"], "client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
        "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier}, timeout=30)
    if r.status_code != 200:
        raise YouTubeError(f"Token alınamadı: {r.text[:300]}")
    tok = r.json()
    tok["expires_at"] = time.time() + tok.get("expires_in", 3600) - 60
    _save_token(channel, tok)
    yt = Client(channel)
    me = yt.my_channel()
    st = load_state(channel)
    st.update({"channel_id": me["id"], "channel_title": me["snippet"]["title"]})
    save_state(channel, st)
    print(f"  Bağlandı: {me['snippet']['title']} ({me['id']})")
    return me


class Client:
    """Tiny YouTube Data API client on requests: refreshes the access token, retries 5xx."""

    def __init__(self, channel: str, session: requests.Session | None = None):
        self.channel = channel
        self.s = session or requests.Session()
        p = _token_path(channel)
        if not p.exists():
            raise YouTubeError(f"YouTube bağlantısı yok. Önce: python -m studio youtube-login --channel {channel}")
        self.tok = json.loads(p.read_text(encoding="utf-8"))

    def _access(self, force: bool = False) -> str:
        if force or time.time() >= self.tok.get("expires_at", 0):
            c = _client()
            r = requests.post(TOKEN_URL, data={"client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
                                               "refresh_token": self.tok.get("refresh_token", ""),
                                               "grant_type": "refresh_token"}, timeout=30)
            if r.status_code != 200:
                raise YouTubeError("YouTube oturumu düştü (Google izni geri alınmış ya da uygulama 'Testing' "
                                   f"modunda). Tekrar bağlan: python -m studio youtube-login --channel {self.channel}")
            new = r.json()
            self.tok.update({"access_token": new["access_token"],
                             "expires_at": time.time() + new.get("expires_in", 3600) - 60})
            _save_token(self.channel, self.tok)
        return self.tok["access_token"]

    def call(self, method: str, url: str, ok=(200, 201, 204), **kw) -> requests.Response:
        headers, timeout, r = kw.pop("headers", {}), kw.pop("timeout", 120), None
        for attempt in range(4):
            token = self._access(force=r is not None and r.status_code == 401)
            r = self.s.request(method, url, headers={**headers, "Authorization": f"Bearer {token}"},
                               timeout=timeout, **kw)
            if r.status_code in ok:
                return r
            if r.status_code not in (401, 500, 502, 503, 504):
                break
            time.sleep(2 ** attempt)
        raise YouTubeError(f"YouTube API {method} {url.split('?')[0].rsplit('/', 1)[-1]}: {r.status_code} {_reason(r)}")

    def get(self, path: str, **params) -> dict:
        return self.call("GET", f"{API}/{path}", params=params).json()

    def my_channel(self) -> dict:
        items = self.get("channels", part="snippet,status", mine="true").get("items") or []
        if not items:
            raise YouTubeError("Bu Google hesabında YouTube kanalı yok. Girişte kanalın marka hesabını seç.")
        return items[0]


def _reason(r: requests.Response) -> str:
    try:
        err = r.json().get("error", {})
        reasons = ", ".join(e.get("reason", "") for e in err.get("errors", []))
        return f"{err.get('message', '')} [{reasons}]".strip()
    except Exception:
        return r.text[:300]


# ------------------------------------------------------------------ metadata
def release(yt: dict, pub: dict, at: str | None, now: datetime | None = None) -> tuple[str, str | None]:
    """(privacyStatus, publishAt UTC ISO or None). at: "now", "YYYY-MM-DD HH:MM" (local time) or None."""
    now = now or datetime.now().astimezone()
    if at == "now":
        return "public", None
    when = None
    if at:
        when = datetime.strptime(at.strip().replace("T", " "), "%Y-%m-%d %H:%M").astimezone()
    elif pub.get("planned_date"):
        when = datetime.strptime(f"{pub['planned_date']} {yt.get('publish_time') or '22:00'}", "%Y-%m-%d %H:%M").astimezone()
        if when <= now:
            when = None
    if when:
        if when <= now:
            raise YouTubeError(f"Yayın zamanı geçmişte: {when:%Y-%m-%d %H:%M}")
        return "private", when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return yt.get("privacy") or "private", None


def _clean(text: str) -> str:
    return (text or "").replace("<", "").replace(">", "").strip()


def video_body(project: Project, cfg: Config, lang: str, privacy: str, publish_at: str | None) -> dict:
    from .publish import get_publish
    yt = settings(cfg)
    meta, pub = project.meta, get_publish(project)
    title = _clean(pub.get("title_used") or meta.get("title") or project.slug)
    if len(title) > 100:
        raise YouTubeError(f"Başlık 100 karakterden uzun ({len(title)}): {title}")
    desc_path = project.lang_dir(lang) / "description.txt"
    if not desc_path.exists():
        raise YouTubeError("description.txt yok: önce `describe` adımını çalıştır.")
    tags, total = [], 0
    for t in [*(meta.get("tags") or []), *(yt.get("tags") or [])]:
        t = _clean(str(t)).replace(",", " ")
        cost = len(t) + (2 if " " in t else 0) + 1
        if t and t.lower() not in {x.lower() for x in tags} and total + cost <= 480:
            tags.append(t)
            total += cost
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": bool(yt.get("made_for_kids")),
              "containsSyntheticMedia": bool(yt.get("synthetic_media")), "embeddable": True,
              "license": yt.get("license") or "youtube", "publicStatsViewable": True}
    if publish_at:
        status["publishAt"] = publish_at
    return {"snippet": {"title": title, "description": desc_path.read_text(encoding="utf-8").strip(), "tags": tags,
                        "categoryId": str(yt.get("category") or 27), "defaultLanguage": yt.get("language") or lang,
                        "defaultAudioLanguage": lang},
            "status": status}


def thumbnail_file(project: Project, lang: str, n: int) -> Path | None:
    d = project.build / "thumbnails" / lang
    p = d / f"thumb{n}.png"
    if not p.exists():
        return None
    if p.stat().st_size <= THUMB_MAX:
        return p
    from PIL import Image
    out = d / f"thumb{n}.upload.jpg"
    img = Image.open(p).convert("RGB")
    if img.width > 1280:
        img = img.resize((1280, round(img.height * 1280 / img.width)), Image.LANCZOS)
    for q in (92, 85, 75):
        img.save(out, "JPEG", quality=q, optimize=True)
        if out.stat().st_size <= THUMB_MAX:
            break
    return out


# ------------------------------------------------------------------ API steps
def upload_file(yt: Client, path: Path, body: dict) -> str:
    size = path.stat().st_size
    r = yt.call("POST", f"{UPLOAD}/videos", params={"uploadType": "resumable", "part": "snippet,status"},
                json=body, headers={"X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
    session_url = r.headers["Location"]
    pos, fails = 0, 0
    with open(path, "rb") as f:
        while True:
            f.seek(pos)
            chunk = f.read(CHUNK)
            try:
                r = yt.s.put(session_url, data=chunk, timeout=300, headers={
                    "Authorization": f"Bearer {yt._access()}",
                    "Content-Range": f"bytes {pos}-{pos + len(chunk) - 1}/{size}"})
            except requests.RequestException:
                r = None
            if r is not None and r.status_code in (200, 201):
                print(f"  yüklendi: {size / 1e6:.0f} MB")
                return r.json()["id"]
            if r is not None and r.status_code == 308:
                rng = r.headers.get("Range")
                pos = int(rng.rsplit("-", 1)[1]) + 1 if rng else 0
                fails = 0
                print(f"  yükleniyor: %{100 * pos // size}")
                continue
            if r is not None and r.status_code not in (500, 502, 503, 504):
                raise YouTubeError(f"Video yüklenemedi: {r.status_code} {_reason(r)}")
            fails += 1
            if fails > 6:
                raise YouTubeError("Video yüklenemedi: bağlantı tekrar tekrar koptu. Komutu yeniden çalıştır.")
            time.sleep(2 ** fails)
            q = yt.s.put(session_url, timeout=60, headers={"Authorization": f"Bearer {yt._access()}",
                                                           "Content-Range": f"bytes */{size}"})
            if q.status_code in (200, 201):
                return q.json()["id"]
            rng = q.headers.get("Range") if q.status_code == 308 else None
            pos = int(rng.rsplit("-", 1)[1]) + 1 if rng else 0


def set_thumbnail(yt: Client, video_id: str, path: Path) -> None:
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    yt.call("POST", f"{UPLOAD}/thumbnails/set", params={"videoId": video_id, "uploadType": "media"},
            data=path.read_bytes(), headers={"Content-Type": mime})


def set_captions(yt: Client, video_id: str, srt: Path, lang: str) -> None:
    """Replaces our own caption track in `lang` (YouTube's automatic track is left alone)."""
    for c in yt.get("captions", part="snippet", videoId=video_id).get("items", []):
        sn = c["snippet"]
        if sn.get("language") == lang and sn.get("trackKind") != "asr":
            yt.call("DELETE", f"{API}/captions", params={"id": c["id"]})
    boundary = "vf" + secrets.token_hex(8)
    meta = json.dumps({"snippet": {"videoId": video_id, "language": lang, "name": "", "isDraft": False}})
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
            f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n").encode() + srt.read_bytes() + \
        f"\r\n--{boundary}--\r\n".encode()
    yt.call("POST", f"{UPLOAD}/captions", params={"uploadType": "multipart", "part": "snippet"}, data=body,
            headers={"Content-Type": f"multipart/related; boundary={boundary}"})


def ensure_playlist(yt: Client, channel: str, series_id: str, series: dict, state: dict) -> str:
    pid = state["playlists"].get(series_id)
    if pid:
        found = yt.get("playlists", part="id", id=pid).get("items")
        if found:
            return pid
    body = {"snippet": {"title": series.get("name") or series_id, "description": series.get("promise", ""),
                        "defaultLanguage": "en"}, "status": {"privacyStatus": "public"}}
    pid = yt.call("POST", f"{API}/playlists", params={"part": "snippet,status"}, json=body).json()["id"]
    state["playlists"][series_id] = pid
    save_state(channel, state)
    print(f"  oynatma listesi oluşturuldu: {body['snippet']['title']}")
    return pid


def add_to_playlist(yt: Client, playlist_id: str, video_id: str) -> bool:
    if yt.get("playlistItems", part="id", playlistId=playlist_id, videoId=video_id).get("items"):
        return False
    yt.call("POST", f"{API}/playlistItems", params={"part": "snippet"},
            json={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}})
    return True


# ------------------------------------------------------------------ the command
def publish_video(project: Project, cfg: Config, lang: str, video: str | None = None, at: str | None = None,
                  force: bool = False, client: Client | None = None) -> str:
    from .publish import get_publish, save_publish
    from .readiness import check
    yt_cfg = settings(cfg)
    pub = get_publish(project)
    video_id = parse_video_id(video) or pub.get("youtube_id") or None
    mp4 = project.lang_dir(lang) / "video.mp4"
    if not video_id and not mp4.exists():
        raise YouTubeError("video.mp4 yok: önce videoyu üret.")
    if not force and not check(project)["ready"]:
        raise YouTubeError("Kalite kapısında engel var (python -m studio check). Yine de yüklemek için --force.")
    if not video_id and not yt_cfg.get("api_audited"):
        raise YouTubeError(
            "Google, denetlenmemiş bir API projesinden yüklenen videoları kalıcı olarak 'özel' kilitler.\n"
            f"  Şimdilik: YouTube Studio → Oluştur → Video yükle → {mp4}\n"
            "  Taslak olarak bırak (bir şey doldurma), linkini kopyala ve şunu çalıştır:\n"
            f"    python -m studio upload {project.slug} <video linki>\n"
            "  Başlık, açıklama, kapak, altyazı, liste ve yayın zamanını API doldurur.\n"
            f"  Denetim başvurusu (onaylanınca channel.yaml → youtube.api_audited: true): {AUDIT_FORM}")
    from .render import describe
    describe(project, cfg, lang)
    privacy, publish_at = release(yt_cfg, pub, at)
    body = video_body(project, cfg, lang, privacy, publish_at)

    yt = client or Client(project.channel)
    state = load_state(project.channel)
    me = yt.my_channel()
    if state.get("channel_id") and me["id"] != state["channel_id"]:
        raise YouTubeError(f"Bağlı hesap başka bir kanal: {me['snippet']['title']}. "
                           f"Tekrar bağlan: python -m studio youtube-login --channel {project.channel}")

    if video_id:
        found = yt.get("videos", part="snippet,status", id=video_id).get("items") or []
        if not found:
            raise YouTubeError(f"Video bulunamadı ya da bu kanalın değil: {video_id}")
        if found[0]["status"].get("privacyStatus") == "public" and privacy != "public":
            body["status"]["privacyStatus"] = "public"      # never pull a live video back to private
            body["status"].pop("publishAt", None)
        yt.call("PUT", f"{API}/videos", params={"part": "snippet,status"}, json={"id": video_id, **body})
        print(f"  bilgiler güncellendi: {video_id}")
    else:
        print(f"  yükleniyor: {mp4.name} ({mp4.stat().st_size / 1e6:.0f} MB)")
        video_id = upload_file(yt, mp4, body)
    save_publish(project, {"youtube_id": video_id, "title_used": body["snippet"]["title"]})

    n = int(pub.get("thumbnail_used") or 1)
    thumb = thumbnail_file(project, lang, n)
    if thumb:
        set_thumbnail(yt, video_id, thumb)
        print(f"  kapak: thumb{n}")
    else:
        print(f"  uyarı: kapak yok (build/thumbnails/{lang}/thumb{n}.png). `thumbnails` adımını çalıştır.")
    srt = project.lang_dir(lang) / f"captions.{lang}.srt"
    if srt.exists():
        set_captions(yt, video_id, srt, lang)
        print(f"  altyazı: {srt.name}")
    series_id = pub.get("series")
    series = (cfg.get_path("channel.series") or {}).get(series_id) if series_id else None
    if series:
        pid = ensure_playlist(yt, project.channel, series_id, series, state)
        if add_to_playlist(yt, pid, video_id):
            print(f"  listeye eklendi: {series.get('name', series_id)}")

    status = body["status"]
    rec: dict[str, Any] = {"youtube_id": video_id}
    if status.get("publishAt"):
        local = datetime.fromisoformat(status["publishAt"].replace("Z", "+00:00")).astimezone()
        rec.update({"planned_date": local.date().isoformat(), "published_at": local.date().isoformat()})
        print(f"  yayın planlandı: {local:%Y-%m-%d %H:%M} (bu bilgisayarın saati)")
    elif status["privacyStatus"] == "public":
        rec["published_at"] = pub.get("published_at") or date.today().isoformat()
        print("  yayında")
    else:
        print(f"  durum: {status['privacyStatus']} (yayın zamanı yok; --at ile ver ya da Studio'dan yayınla)")
    save_publish(project, rec)
    print(f"  https://youtu.be/{video_id}")
    return video_id
