@echo off
REM Video Fabrikasi - guvenli guncelleme. Yerel degisikliklerini (fikir durumlari, projeler, ayarlar) korur.
setlocal
cd /d "%~dp0"
where git >nul 2>nul || (echo [!] Git bulunamadi. Kur: winget install Git.Git & pause & exit /b 1)
if exist .venv\Scripts\python.exe (set "PY=.venv\Scripts\python") else (set "PY=py -3.12")
%PY% -m studio update
echo.
pause
