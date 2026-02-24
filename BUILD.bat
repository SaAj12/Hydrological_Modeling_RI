<<<<<<< HEAD
@echo off
title Build for Hydrological Modeling
cd /d "%~dp0"

echo Exporting discharge data...
python scripts/export_discharge_data.py
if errorlevel 1 (
  echo Export failed.
  pause
  exit /b 1
)

echo.
echo Preparing docs for GitHub Pages...
python scripts/prepare_gh_pages.py
if errorlevel 1 (
  echo Prepare failed.
  pause
  exit /b 1
)

echo.
echo Build complete. Frontend data: frontend/data/
echo GitHub Pages files: docs/
pause
=======
@echo off
title Build for Hydrological Modeling (viewer2)
cd /d "%~dp0"

echo Exporting discharge data...
python scripts/export_discharge_data.py
if errorlevel 1 (
  echo Export failed. Copy discharge.xlsx into this folder if needed.
  pause
  exit /b 1
)

echo.
echo Preparing docs for GitHub Pages...
python scripts/prepare_gh_pages.py
if errorlevel 1 (
  echo Prepare failed.
  pause
  exit /b 1
)

echo.
echo Build complete. Frontend data: frontend/data/
echo GitHub Pages files: docs/
pause
>>>>>>> 3a2b943 (Initial commit of Hydrological Modeling project)
