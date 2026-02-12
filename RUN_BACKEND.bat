<<<<<<< HEAD
@echo off
title SWAT Viewer Backend - keep this window open
cd /d "%~dp0backend"
REM So discharge.xlsx and maps/ are found, set viewer root (parent of backend)
if not defined SWAT_VIEWER_DIR set "SWAT_VIEWER_DIR=%~dp0"
if "%SWAT_VIEWER_DIR:~-1%"=="\" set "SWAT_VIEWER_DIR=%SWAT_VIEWER_DIR:~0,-1%"

echo Installing dependencies if needed...
pip install -r requirements.txt -q
if errorlevel 1 (
  echo Failed to install. Make sure Python is installed and in PATH.
  pause
  exit /b 1
)

echo.
echo Starting backend at http://127.0.0.1:8000
echo Keep this window OPEN while using the viewer.
echo Close this window to stop the backend.
echo.

uvicorn run_server:app --reload
pause
=======
@echo off
title Hydrological Modeling Backend - keep this window open
cd /d "%~dp0backend"
if not defined SWAT_VIEWER_DIR set "SWAT_VIEWER_DIR=%~dp0"
if "%SWAT_VIEWER_DIR:~-1%"=="\" set "SWAT_VIEWER_DIR=%SWAT_VIEWER_DIR:~0,-1%"

echo Installing dependencies if needed...
pip install -r requirements.txt -q
if errorlevel 1 (
  echo Failed to install. Make sure Python is installed and in PATH.
  pause
  exit /b 1
)

echo.
echo Starting backend at http://127.0.0.1:8000
echo Keep this window OPEN while using the viewer.
echo.

uvicorn run_server:app
pause
>>>>>>> 3a2b943 (Initial commit of Hydrological Modeling project)
