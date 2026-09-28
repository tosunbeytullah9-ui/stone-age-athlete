"""Safe update: download the new version from GitHub without losing anything the owner changed locally.

  guncelle.bat / guncelle.sh  →  python -m studio update

1. Local changes (edited settings, idea statuses, new projects, scripts) are put aside with `git stash -u`.
2. The new version is downloaded (fast-forward only; nothing is overwritten by force).
3. Packages are installed if requirements changed.
4. The put-aside changes are merged back file by file (see merge3.py): YAML files value by value, other files
   are restored unless the update changed the same file, in which case the owner's copy is saved next to it as
   <file>.senin-surumun. Files in renamed folders follow the rename. Every original is also copied to backups/.
5. Data migrations run (e.g. projects in a renamed channel folder move to the new folder).

Also recovers a stash the owner made by hand (git stash -u; git pull) before this updater existed.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from .config import ROOT

STATE = ROOT / ".fabrika" / "update_state.json"
STASH_MSG = "fabrika-guncelle"
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".csv", ".srt"}


def git(*args: str, check: bool = True, binary: bool = False):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=not binary)
    if check and r.returncode != 0:
        err = r.stderr if not binary else r.stderr.decode("utf-8", "replace")
        raise RuntimeError(f"git {' '.join(args)}: {err.strip()}")
    return r.stdout if check else r


def _state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"restored": []}


def _save_state(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=1), encoding="utf-8")


def _show(rev: str, path: str) -> bytes | None:
    r = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, capture_output=True)
    return r.stdout if r.returncode == 0 else None


# ------------------------------------------------------------------ phase 1: stash + pull
def update(pip: bool = True) -> int:
    if not (ROOT / ".git").exists():
        print("  [!] Bu klasör bir Git deposu değil. Güncelleme için projeyi 'git clone' ile indirmiş olmalısın.")
        return 1
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    old_head = git("rev-parse", "HEAD").strip()
    req_before = (ROOT / "requirements.txt").read_bytes() if (ROOT / "requirements.txt").exists() else b""

    print("  Yeni sürüm kontrol ediliyor...")
    git("fetch", "origin", branch)
    remote = git("rev-parse", f"origin/{branch}").strip()
    dirty = bool(git("status", "--porcelain").strip())
    stash = None
    if dirty and remote != old_head:
        print("  Yerel değişikliklerin kenara alınıyor (hiçbiri silinmez)...")
        git("stash", "push", "-u", "-m", f"{STASH_MSG} {time.strftime('%Y-%m-%d %H:%M')}")
        stash = git("rev-parse", "stash@{0}").strip()

    if remote != old_head:
        r = git("merge", "--ff-only", f"origin/{branch}", check=False)
        if r.returncode != 0:
            print("  [!] Yeni sürüm otomatik alınamadı (bu klasörde elle commit yapılmış olabilir).")
            print("      " + (r.stderr or "").strip()[:300])
            if stash:
                git("stash", "pop", check=False)
            return 1
        print(f"  Güncellendi: {old_head[:7]} → {remote[:7]}")
        for ln in git("log", "--format=  · %s", f"{old_head}..{remote}").splitlines()[:15]:
            print(ln)
    else:
        print("  Zaten en yeni sürüm.")

    if pip and req_before != ((ROOT / "requirements.txt").read_bytes() if (ROOT / "requirements.txt").exists() else b""):
        print("  Yeni paketler kuruluyor...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"], cwd=ROOT)

    # phase 2 runs in a fresh process so it uses the code that was just downloaded
    cmd = [sys.executable, "-m", "studio", "update-restore"]
    if stash:
        cmd += ["--stash", stash]
    return subprocess.run(cmd, cwd=ROOT).returncode


# ------------------------------------------------------------------ phase 2: merge back + migrate
def restore(stash: str | None = None) -> int:
    st = _state()
    todo = []
    if stash:
        todo.append(stash)
    else:
        todo += _manual_stashes(st)
    report: list[str] = []
    for s in todo:
        report += restore_stash(s)
        st["restored"].append(s)
        _save_state(st)
        _drop(s)
    from .migrate import migrate_renamed_channels
    report += migrate_renamed_channels(verbose=False)
    for ln in report:
        print(f"  · {ln}")
    print("  Güncelleme tamam. Paneli start.bat ile açabilirsin.")
    return 0


def _manual_stashes(st: dict) -> list[str]:
    """Stashes the owner made by hand before an update (bootstrap): not restored yet, based on an older version."""
    out = []
    head = git("rev-parse", "HEAD").strip()
    for ln in git("stash", "list", "--format=%H %gs").splitlines():
        h, _, msg = ln.partition(" ")
        if h in st["restored"]:
            continue
        base = git("rev-parse", f"{h}^1").strip()
        is_ancestor = git("merge-base", "--is-ancestor", base, head, check=False).returncode == 0
        if is_ancestor and base != head:
            out.append(h)
            break                     # only the newest one
    return out


def _drop(stash: str) -> None:
    for ln in git("stash", "list", "--format=%H %gd").splitlines():
        h, _, ref = ln.partition(" ")
        if h == stash:
            git("stash", "drop", ref, check=False)
            return


def _rename_map(base: str) -> dict[str, str]:
    out = {}
    for ln in git("diff", "--name-status", "-M", base, "HEAD").splitlines():
        parts = ln.split("\t")
        if parts[0].startswith("R") and len(parts) == 3:
            out[parts[1]] = parts[2]
    return out


def _alias_map() -> dict[str, str]:
    """channels/<old id>/ → channels/<new id>/ for renamed channels."""
    from .channel import list_channels
    return {f"channels/{a}/": f"channels/{ch.id}/" for ch in list_channels() for a in ch.aliases if a != ch.id}


def _target(path: str, renames: dict[str, str], aliases: dict[str, str]) -> str:
    if path in renames:
        return renames[path]
    for old, new in aliases.items():
        if path.startswith(old):
            return new + path[len(old):]
    return path


def restore_stash(stash: str) -> list[str]:
    from .merge3 import merge_yaml_text
    base = git("rev-parse", f"{stash}^1").strip()
    renames, aliases = _rename_map(base), _alias_map()
    backup = ROOT / "backups" / f"guncelleme-{time.strftime('%Y%m%d-%H%M%S')}"
    report: list[str] = []
    changed = [p for p in git("diff", "--name-only", base, stash).splitlines() if p]
    untracked_rev = f"{stash}^3"
    has_untracked = git("rev-parse", "--verify", "--quiet", untracked_rev, check=False).returncode == 0
    untracked = [p for p in git("ls-tree", "-r", "--name-only", untracked_rev).splitlines()] if has_untracked else []

    def save_backup(path: str, data: bytes) -> None:
        b = backup / path
        b.parent.mkdir(parents=True, exist_ok=True)
        b.write_bytes(data)

    for path in changed:
        ours = _show(stash, path)
        if ours is None:
            continue                                   # the owner deleted a file: keep the new version
        save_backup(path, ours)
        base_b = _show(base, path)
        tgt = _target(path, renames, aliases)
        dst = ROOT / tgt
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(ours)
            report.append(f"geri yüklendi: {tgt}")
            continue
        theirs = dst.read_bytes()
        if theirs == ours:
            continue
        if base_b is not None and theirs == base_b:
            dst.write_bytes(ours)
            report.append(f"değişikliğin korundu: {tgt}")
            continue
        if base_b is not None and ours == base_b:
            continue
        if dst.suffix in (".yaml", ".yml"):
            try:
                merged = merge_yaml_text(base_b.decode("utf-8") if base_b else None, ours.decode("utf-8"),
                                         theirs.decode("utf-8"), ideas_file=dst.name == "ideas.yaml")
                dst.write_text(merged, encoding="utf-8")
                report.append(f"birleştirildi: {tgt}")
                continue
            except (ValueError, UnicodeDecodeError):
                pass
        side = dst.with_name(dst.name + ".senin-surumun")
        side.write_bytes(ours)
        report.append(f"ÇAKIŞMA: {tgt} güncellemede de değişti. Senin sürümün: {side.relative_to(ROOT)}")

    for path in untracked:
        data = _show(untracked_rev, path)
        if data is None:
            continue
        save_backup(path, data)
        tgt = _target(path, renames, aliases)
        dst = ROOT / tgt
        if dst.exists():
            if dst.read_bytes() != data:
                side = dst.with_name(dst.name + ".senin-surumun")
                side.write_bytes(data)
                report.append(f"ÇAKIŞMA: {tgt} yeni sürümde de var. Senin dosyan: {side.relative_to(ROOT)}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    if untracked:
        report.append(f"{len(untracked)} yeni dosyan (projeler, notlar) yerine kondu")
    report.append(f"tüm yerel dosyalarının kopyası: {backup.relative_to(ROOT)}")
    return report
