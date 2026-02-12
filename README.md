<<<<<<< HEAD
# Hydrological Modeling — Discharge Data Viewer

A web platform to view discharge values at monitoring stations. Anyone with the link can access the data, click on any station, and see the discharge time-series trend (1950–2025). Y-axis units: m³/s (cubic meters per second).

- **Map:** World Topographic Map (Esri GIS style)
- **Data source:** `discharge.xlsx` (coordinates sheet: STAID, LAT, LON, STANAME; data sheet: first row = station IDs)
- **Deployment:** Static frontend + JSON → works on **GitHub Pages** with no backend required

---

## Quick start (local)

### 1. Export discharge data to JSON

```powershell
cd D:\Brown\SWAT\viewer1
python scripts/export_discharge_data.py
```

This creates `frontend/data/discharge_data.json` from `discharge.xlsx`.

### 2. Serve the frontend

**Option A — Use the batch file**

1. Double-click **`RUN_FRONTEND.bat`**
2. Open **http://localhost:8080** in your browser

**Option B — From command line**

```powershell
cd D:\Brown\SWAT\viewer1\frontend
python -m http.server 8080
```

Then open **http://localhost:8080**.

### 3. Optional: run backend (for Watershed & DEM layers)

If you want the Watershed and DEM map layers:

1. Double-click **`RUN_BACKEND.bat`**
2. Keep that window open
3. Use the Watershed and DEM checkboxes on the map

---

## Deploy to GitHub Pages (online, public access)

1. **Export data** (run once before pushing):

   ```powershell
   python scripts/export_discharge_data.py
   ```

2. **Create a GitHub repository** (e.g. `Hydrological-Modeling` or `viewer`).

3. **Build and push** to GitHub:

   ```powershell
   cd D:\Brown\SWAT\viewer1
   REM Build: export data + prepare docs folder
   python scripts/export_discharge_data.py
   python scripts/prepare_gh_pages.py

   git init
   git add docs/ scripts/ discharge.xlsx README.md BUILD.bat
   git add frontend/ backend/main.py backend/requirements.txt backend/run_server.py
   git add RUN_BACKEND.bat RUN_FRONTEND.bat .gitignore
   git commit -m "Hydrological Modeling - Discharge viewer"
   git remote add origin https://github.com/SaAj12/Hydrological-Modeling.git
   git branch -M main
   git push -u origin main
   ```

4. **Enable GitHub Pages:**
   - Repo → **Settings** → **Pages**
   - **Source:** Deploy from branch
   - **Branch:** `main`, **Folder:** `/docs`
   - Save

Your site will be at: **https://saaj12.github.io/Hydrological-Modeling/**

---

## Data format (discharge.xlsx)

- **Sheet `coordinates`:** STAID, LAT, LON, STANAME (or Stations_Names)
- **Sheet `data`:** First row = station IDs (matching STAID), first column = Date, cells = discharge values

---

## Files

| Path | Purpose |
|------|---------|
| `scripts/export_discharge_data.py` | Exports discharge.xlsx → frontend/data/discharge_data.json |
| `frontend/index.html` | Main page |
| `frontend/js/app.js` | Map, stations, discharge chart |
| `frontend/data/discharge_data.json` | Pre-exported data (run export script to generate) |
| `backend/main.py` | Optional API for watershed/DEM layers |

---

## License

Use and adapt as needed. Data sources have their own terms.
=======
# Hydrological Modeling (viewer2)

Discharge data viewer for GitHub deployment. Station names show as text with 8-digit IDs (e.g. **TAUNTON RIVER NEAR BRIDGEWATER, MA (01108000)**). Chart: cfs (cubic feet per second), thinner line. No DEM or Watershed layers.

## Changes from viewer1

- **Station IDs** displayed as 8-digit text (e.g. `01108000` not `1108000`)
- **Chart title:** "Discharge (cfs, Cubic feet per second)"
- **Chart:** Thinner line (`borderWidth: 1`)
- **DEM and Watershed** removed from map and dataset

## Quick start

1. Copy `discharge.xlsx` into `D:\Brown\SWAT\viewer2` (same file as in viewer1).
2. Export data: `python scripts/export_discharge_data.py`
3. Double-click **RUN_FRONTEND.bat** and open **http://localhost:8080**

Optional: run **RUN_BACKEND.bat** for API-served data; the app works fully from static JSON without the backend.

## Deploy to GitHub Pages

1. Run `python scripts/export_discharge_data.py` then `python scripts/prepare_gh_pages.py` (or double-click **BUILD.bat**).
2. Push the repo including the `docs/` folder.
3. In GitHub: **Settings** → **Pages** → Source: branch `main`, folder **/docs**.

Site URL: **https://saaj12.github.io/YourRepoName/**
>>>>>>> 3a2b943 (Initial commit of Hydrological Modeling project)
