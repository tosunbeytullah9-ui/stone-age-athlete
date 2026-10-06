"""Background job queue for the panel. Each job runs `python -m studio ...` in a subprocess, so a crash in
one step never takes the panel down, and its output streams into the job log shown live in the UI.
Jobs run one at a time (rendering is CPU-heavy); the rest wait in the queue."""
from __future__ import annotations

import itertools
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field

from ..config import ROOT

STEP_LABELS = {
    "split": "Böl", "plan": "Sahne planı", "translate": "Çeviri", "voice": "Seslendirme", "align": "Zamanlama",
    "images": "Resimler", "render": "Video", "shorts": "Shorts", "describe": "Açıklama", "sheet": "Kontak sayfası", "captions": "Altyazı", "dub": "Dublaj izi",
    "check": "Kalite kontrol", "all": "Tümünü üret",
    "thumbnails": "Kapak görselleri", "signals": "Fikir sinyalleri", "check-links": "Bağlantı kontrolü",
    "branding": "Marka görselleri", "knowledge": "Bilgi paketi",
}


@dataclass
class Job:
    id: int
    args: list[str]
    label: str
    channel: str | None = None
    project: str | None = None
    status: str = "queued"          # queued | running | done | failed | cancelled
    log: list[str] = field(default_factory=list)
    created: float = field(default_factory=time.time)
    started: float | None = None
    finished: float | None = None
    returncode: int | None = None
    proc: subprocess.Popen | None = None

    def public(self, since: int = 0) -> dict:
        return {"id": self.id, "label": self.label, "channel": self.channel, "project": self.project,
                "status": self.status, "created": self.created, "started": self.started, "finished": self.finished,
                "returncode": self.returncode, "log_len": len(self.log), "log": self.log[since:],
                "args": self.args}


class JobManager:
    def __init__(self):
        self.jobs: dict[int, Job] = {}
        self._ids = itertools.count(1)
        self._q: queue.Queue[Job] = queue.Queue()
        self._lock = threading.Lock()
        threading.Thread(target=self._worker, daemon=True).start()

    def submit(self, args: list[str], label: str, channel: str | None = None, project: str | None = None) -> Job:
        job = Job(next(self._ids), args, label, channel, project)
        with self._lock:
            self.jobs[job.id] = job
        self._q.put(job)
        return job

    def cancel(self, job_id: int) -> bool:
        job = self.jobs.get(job_id)
        if not job:
            return False
        if job.status == "queued":
            job.status = "cancelled"
            return True
        if job.status == "running" and job.proc:
            job.proc.terminate()
            job.status = "cancelled"
            return True
        return False

    def list(self, limit: int = 30) -> list[dict]:
        jobs = sorted(self.jobs.values(), key=lambda j: j.id, reverse=True)[:limit]
        return [j.public(since=max(0, len(j.log) - 3)) for j in jobs]

    def active_for(self, channel: str, project: str) -> list[dict]:
        return [j.public(since=len(j.log)) for j in self.jobs.values()
                if j.channel == channel and j.project == project and j.status in ("queued", "running")]

    def _worker(self):
        while True:
            job = self._q.get()
            if job.status == "cancelled":
                continue
            job.status, job.started = "running", time.time()
            env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
            try:
                job.proc = subprocess.Popen([sys.executable, "-m", "studio", *job.args], cwd=ROOT, env=env,
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                            encoding="utf-8", errors="replace", bufsize=1)
                for line in job.proc.stdout:
                    job.log.append(line.rstrip("\n"))
                    if len(job.log) > 4000:
                        del job.log[:1000]
                job.returncode = job.proc.wait()
                if job.status != "cancelled":
                    job.status = "done" if job.returncode == 0 else "failed"
            except Exception as e:  # pragma: no cover
                job.log.append(f"HATA: {e}")
                job.status = "failed"
            job.finished = time.time()
            job.proc = None


manager = JobManager()
