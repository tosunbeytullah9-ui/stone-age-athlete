"""Eski giriş noktası: tarama artık fabrikanın içinde (studio/ytscan.py; panel: Kanal → YouTube taraması).

  .venv\\Scripts\\python tools\\yt_tara.py konular --channel ordinary-genius [--only g001,g002]
  = python -m studio scan konular --channel ordinary-genius [--only g001,g002]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.ytscan import MODES, run  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=MODES)
    ap.add_argument("--channel", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    run(a.mode, a.channel, ids=[x for x in a.only.split(",") if x] or None, limit=a.limit)
