"""Where sounds come from: built-in synthesis (studio/sound/synth.py) or audio files listed in the shared
library/sounds/catalog.yaml. Every sound has an id; storyboards and rules only use ids.

library/sounds/catalog.yaml
  sounds:
    - id: crowd_subway            # unique id (a file may also replace a built-in id, e.g. `door`)
      kind: amb | sfx             # amb = loopable bed under a whole scene, sfx = one-shot effect
      file: adafruit/busy_subway.wav          # under library/sounds/files/ (not in git)
      url: https://raw.githubusercontent.com/...   # where `python -m studio sounds-fetch` downloads it
      license: CC0                 # required. Allowed for monetised videos: CC0, CC-BY (credit goes to the
      credit: ""                   #   description automatically), own recording, generated
      tags: [crowd, city]
      gain_db: 0                   # level trim
      fallback: murmur             # built-in id used while the file is missing

Files are never committed (they live in library/sounds/files/, git-ignored); the catalog with urls and licences is.
Synthesised sounds are rendered once and cached in .fabrika/sound_cache/.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import yaml

from ..config import ROOT
from . import synth

LIB = ROOT / "library" / "sounds"
CATALOG = LIB / "catalog.yaml"
FILES = LIB / "files"
CACHE = ROOT / ".fabrika" / "sound_cache"
SR = synth.SR
VARIANTS = 4                       # spot effects come in a few takes so repeats never sound identical
OK_LICENSES = {"CC0", "PUBLIC DOMAIN", "CC-BY", "CC BY", "CC-BY-4.0", "CC BY 4.0", "GENERATED", "OWN",
               "PIXABAY", "YOUTUBE AUDIO LIBRARY"}


def load_catalog() -> dict[str, dict]:
    if not CATALOG.exists():
        return {}
    data = yaml.safe_load(CATALOG.read_text(encoding="utf-8")) or {}
    return {s["id"]: s for s in data.get("sounds") or [] if isinstance(s, dict) and s.get("id")}


def license_ok(entry: dict) -> bool:
    return str(entry.get("license", "")).strip().upper() in OK_LICENSES


def kind(sid: str, cat: dict | None = None) -> str | None:
    cat = load_catalog() if cat is None else cat
    if sid in cat:
        return cat[sid].get("kind", "sfx")
    if sid in synth.AMBIENCE:
        return "amb"
    if sid in synth.EFFECTS:
        return "sfx"
    return None


def known(sid: str, cat: dict | None = None) -> bool:
    return kind(sid, cat) is not None


def all_ids(cat: dict | None = None) -> dict[str, list[str]]:
    cat = load_catalog() if cat is None else cat
    amb = sorted(set(synth.AMBIENCE) | {k for k, v in cat.items() if v.get("kind") == "amb"})
    sfx = sorted(set(synth.EFFECTS) | {k for k, v in cat.items() if v.get("kind", "sfx") == "sfx"})
    return {"amb": amb, "sfx": sfx}


# ------------------------------------------------------------------ audio io
def _read(path: Path) -> np.ndarray:
    import soundfile as sf
    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    x = x[:, :2]
    if sr != SR:
        n = int(len(x) * SR / sr)
        idx = np.linspace(0, len(x) - 1, n)
        x = np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1).astype("float32")
    return x


def write_wav(path: Path, x: np.ndarray, subtype: str = "PCM_16") -> Path:
    import soundfile as sf
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.clip(x, -1, 1), SR, subtype=subtype)
    return path


def _synth_cached(name: str, seed: int) -> np.ndarray:
    code = Path(synth.__file__).read_bytes()
    tag = hashlib.sha1(code + f"{name}:{seed}".encode()).hexdigest()[:12]
    f = CACHE / f"{name}-{seed}-{tag}.wav"
    if f.exists():
        try:
            return _read(f)
        except Exception:
            pass
    x = synth.generate(name, seed)
    try:
        write_wav(f, x)
    except Exception:
        pass
    return x


def get(sid: str, variant: int = 0, cat: dict | None = None) -> np.ndarray:
    """Stereo float32 audio at 48 kHz for a sound id. Files win over synthesis when present and licensed."""
    cat = load_catalog() if cat is None else cat
    e = cat.get(sid)
    if e:
        f = FILES / e.get("file", "")
        if e.get("file") and f.exists() and license_ok(e):
            x = _read(f)
            g = float(e.get("gain_db", 0) or 0)
            return (x * 10 ** (g / 20)).astype("float32")
        fb = e.get("fallback")
        if fb and fb != sid:
            return get(fb, variant, cat)
    if sid in synth.AMBIENCE:
        return _synth_cached(sid, 0)
    if sid in synth.EFFECTS:
        return _synth_cached(sid, variant % VARIANTS)
    raise KeyError(f"bilinmeyen ses: {sid}")


def credits(ids: set[str], cat: dict | None = None) -> list[str]:
    """Attribution lines for CC-BY sounds actually used (goes into the description)."""
    cat = load_catalog() if cat is None else cat
    out = []
    for sid in sorted(ids):
        e = cat.get(sid)
        if e and (FILES / e.get("file", "")).exists() and "BY" in str(e.get("license", "")).upper():
            out.append(e.get("credit") or f"{sid}: {e.get('url', '')} ({e.get('license')})")
    return out


def fetch(only: list[str] | None = None, timeout: int = 60) -> dict[str, str]:
    """Download catalog files that have a url (python -m studio sounds-fetch)."""
    import requests
    res = {}
    for sid, e in load_catalog().items():
        if only and sid not in only:
            continue
        if not e.get("url") or not e.get("file"):
            continue
        if not license_ok(e):
            res[sid] = f"atlandı: lisans '{e.get('license')}' ticari kullanım için onaylı listede değil"
            continue
        dst = FILES / e["file"]
        if dst.exists():
            res[sid] = "var"
            continue
        try:
            r = requests.get(e["url"], timeout=timeout)
            r.raise_for_status()
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(r.content)
            res[sid] = "indirildi"
        except Exception as ex:                             # noqa: BLE001
            res[sid] = f"hata: {ex}"
    return res
