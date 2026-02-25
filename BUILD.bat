@echo off
title Build for Hydrological Modeling (viewer3)
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
  echo NOAA export failed. Ensure noaa/noaa_stations_in_domain.csv exists.
  pause
  exit /b 1
)

echo.
echo Fetching VTEC for USGS and NOAA stations...
python scripts/fetch_vtec_by_usgs_and_noaa_locations.py
if errorlevel 1 (
  echo VTEC fetch failed. Ensure usgs_locations.xlsx and noaa/noaa_stations_in_domain.csv exist.
)

echo.
echo Plotting VTEC timelines...
python scripts/plot_vtec_timeline_all_stations.py
if errorlevel 1 (
  echo VTEC plot failed. Ensure docs/vtec_by_usgs_and_noaa/*.csv exist.
)

echo.
echo Plotting NOAA precipitation...
python scripts/plot_precipitation_noaa_stations.py
if errorlevel 1 (
  echo Precipitation plot failed. Ensure pr_extracted/ exists.
)

echo.
echo Plotting NOAA water level...
python scripts/plot_noaa_water_level_with_predictions.py
if errorlevel 1 (
  echo Water level plot failed. Ensure noaa/8454000_water_level.csv and 8454000_predictions.csv exist.
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
