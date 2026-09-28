#!/usr/bin/env bash
# Video Fabrikası — güvenli güncelleme: ./guncelle.sh (yerel değişikliklerini korur)
cd "$(dirname "$0")"
PY=.venv/bin/python; [ -x "$PY" ] || PY=python3
exec "$PY" -m studio update
