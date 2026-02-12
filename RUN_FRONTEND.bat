@echo off
title SWAT Viewer Frontend
cd /d "%~dp0frontend"

echo.
echo Serving frontend at:  http://localhost:8080
echo Open that URL in your browser (backend must be running at http://127.0.0.1:8000).
echo Press Ctrl+C to stop.
echo.

python -m http.server 8080

pause
