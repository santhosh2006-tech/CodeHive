@echo off
setlocal

REM Always run from the folder this .bat file lives in, regardless of where it's launched from
cd /d "%~dp0"

echo ============================================
echo   CodeHive - Local Web UI Launcher
echo ============================================
echo.

echo Opening browser to http://localhost:8000 ...
start http://localhost:8000

echo Starting FastAPI web server...
echo.

python -m uvicorn server:app --port 8000

pause
