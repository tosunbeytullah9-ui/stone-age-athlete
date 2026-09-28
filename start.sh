#!/usr/bin/env bash
# Video Fabrikası — Mac/Linux: ./start.sh   (ilk çalıştırmada kurulum yapar)
set -e
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo "[!] FFmpeg yok. Mac: brew install ffmpeg"; exit 1; }
if [ ! -x .venv/bin/python ]; then
  echo "İlk kurulum yapılıyor..."
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt -r requirements-voice.txt
  .venv/bin/python -m playwright install chromium
fi
[ -f .env ] || cp .env.example .env
exec .venv/bin/python -m studio web
