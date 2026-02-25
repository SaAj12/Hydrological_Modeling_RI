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
echo Exporting NOAA stations...
python scripts/export_noaa_stations.py
if errorlevel 1 (
  echo NOAA export failed. Ensure D:\go\pr\noaa\noaa_stations_in_domain.csv exists.
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
