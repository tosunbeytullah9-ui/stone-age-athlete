#!/usr/bin/env bash
# Video Fabrikası — Mac/Linux: ./start.sh   (ilk çalıştırmada kurulum yapar)
set -e
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo "[!] FFmpeg yok. Mac: brew install ffmpeg"; exit 1; }
ok() { "$1" -c 'import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,13) else 1)' 2>/dev/null; }
PY=""
for c in python3.12 python3.11 python3.13 python3.10 python3; do
  if command -v "$c" >/dev/null && ok "$c"; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "[!] Python 3.10–3.13 gerekli. Mac: brew install python@3.12"; exit 1; }
if [ -x .venv/bin/python ] && { ! ok .venv/bin/python || [ ! -f .venv/kurulum.ok ]; }; then rm -rf .venv; fi
if [ ! -x .venv/bin/python ]; then
  echo "İlk kurulum yapılıyor ($PY)..."
  "$PY" -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt -r requirements-voice.txt
  .venv/bin/python -m playwright install chromium
  echo ok > .venv/kurulum.ok
fi
[ -f .env ] || cp .env.example .env
exec .venv/bin/python -m studio web
