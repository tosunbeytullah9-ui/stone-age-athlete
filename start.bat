@echo off
REM Video Fabrikasi - Windows'ta cift tikla. Ilk calistirmada kurulum yapar (birkac dakika).
setlocal
cd /d "%~dp0"

where ffmpeg >nul 2>nul || (echo [!] FFmpeg bulunamadi. Kur: winget install Gyan.FFmpeg  ^(sonra bu pencereyi kapatip tekrar ac^) & pause & exit /b 1)

REM Uyumlu Python (3.10 - 3.13) bul. Daha yeni surumler (3.14+) ses paketleriyle henuz calismiyor.
set "PY="
for %%v in (3.12 3.11 3.13 3.10) do (
  if not defined PY (
    py -%%v -c "import sys" >nul 2>nul && set "PY=py -%%v"
  )
)
if not defined PY (
  python -c "import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,13) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [!] Uyumlu Python bulunamadi. Bu fabrika Python 3.10 - 3.13 ister.
  echo     Kur:  winget install Python.Python.3.12
  echo     Sonra bu pencereyi kapatip start.bat'i tekrar calistir. ^(Diger Python surumunu silmen gerekmez.^)
  pause & exit /b 1
)

REM Eski/yarim kalmis ya da uyumsuz sanal ortami temizle
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python -c "import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,13) else 1)" >nul 2>nul || (echo Uyumsuz sanal ortam siliniyor... & rmdir /s /q .venv)
)
if exist .venv\Scripts\python.exe if not exist .venv\kurulum.ok (echo Yarim kalmis kurulum siliniyor... & rmdir /s /q .venv)

if not exist .venv\Scripts\python.exe (
  echo Ilk kurulum yapiliyor ^(%PY%^)...
  %PY% -m venv .venv || (echo [!] Sanal ortam olusturulamadi. & pause & exit /b 1)
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -r requirements.txt -r requirements-voice.txt || (echo [!] Paket kurulumu basarisiz. Hata mesajini Claude'a gonder. & pause & exit /b 1)
  .venv\Scripts\python -m playwright install chromium || (echo [!] Chromium kurulamadi. & pause & exit /b 1)
  echo ok> .venv\kurulum.ok
)
if not exist .env copy .env.example .env >nul
.venv\Scripts\python -m studio web
pause
