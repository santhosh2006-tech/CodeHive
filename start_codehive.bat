@echo off
setlocal

REM Always run from the folder this .bat file lives in, regardless of where it's launched from
cd /d "%~dp0"

echo ============================================
echo   CodeHive - Multi-Agent Coding CLI
echo ============================================
echo.
echo Starting CodeHive...
echo.

python main.py

echo.
echo CodeHive exited. Press any key to close this window.
pause >nul
