@echo off
REM Video Fabrikasi - Windows'ta cift tikla. Ilk calistirmada kurulum yapar (birkac dakika).
cd /d "%~dp0"
where ffmpeg >nul 2>nul || (echo [!] FFmpeg bulunamadi. Kur: winget install Gyan.FFmpeg  ^(sonra bu pencereyi kapatip tekrar ac^) & pause & exit /b 1)
if not exist .venv\Scripts\python.exe (
  echo Ilk kurulum yapiliyor...
  python -m venv .venv || (echo [!] Python bulunamadi. Kur: winget install Python.Python.3.12 & pause & exit /b 1)
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -r requirements.txt -r requirements-voice.txt
  .venv\Scripts\python -m playwright install chromium
)
if not exist .env copy .env.example .env >nul
.venv\Scripts\python -m studio web
pause
