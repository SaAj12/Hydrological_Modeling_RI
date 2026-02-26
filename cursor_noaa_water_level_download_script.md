# NOAA water level download script
_Exported on 2/26/2026 at 14:11:54 GMT+3 from Cursor (2.5.25)_

---

**User**

look inside folder and find script that download noaa water level for one station

---

**Cursor**


The script is:

**`scripts/download_noaa_water_level.py`**

It fetches water level and predictions from the NOAA CO-OPS API.

- **Default:** Uses all station IDs from `noaa/noaa_stations_in_domain.csv`
- **Single station:** Use `--stations` / `-s` with a comma-separated list

Example for station 8454000:

```bash
python scripts/download_noaa_water_level.py --stations 8454000
```

Output files (in the `noaa/` folder):

- `{station}_water_level.csv`
- `{station}_predictions.csv`

Run from the project root. Requires `requests` and `pandas`. Use `--test` to check the API.

---

**User**

the script is "D:\Brown\SWAT\viewer3\scripts\download_noaa_one_station.py". edit it so i download data for station 8444069. https://tidesandcurrents.noaa.gov/stationhome.html?id=8444069&name=Castle%20Island,%20North%20of&state=MA 


---

**Cursor**


Updating the script to use station 8444069 (Castle Island, North of, MA) as the default.



Updated `download_noaa_one_station.py` to use station **8444069** (Castle Island, North of, MA):

1. **`DEFAULT_STATION`** set from `"8454000"` to `"8444069"`.
2. **Docstring** updated with the new [station page URL](https://tidesandcurrents.noaa.gov/stationhome.html?id=8444069&name=Castle%20Island,%20North%20of&state=MA).
3. **Help text** updated so it shows Castle Island, North of, MA instead of Providence, RI.

Running the script without `--station` will download data for 8444069:

```bash
python scripts/download_noaa_one_station.py
```

---

**User**

outputs should be saved at D:\Brown\SWAT\viewer3\noaa

---

**Cursor**


Confirming the script already uses that path: `PROJECT_ROOT` is `viewer3` and `DEFAULT_OUTPUT_DIR` is `os.path.join(PROJECT_ROOT, "noaa")` → `D:\Brown\SWAT\viewer3\noaa`. Hardcoding it to be explicit.



Updated. `DEFAULT_OUTPUT_DIR` is set to `D:\Brown\SWAT\viewer3\noaa`, so outputs will be saved there. You can override it with `--output-dir` if needed.

---

**User**

script takes a long time. make it faster

---

**Cursor**


Parallelizing chunk downloads (like `download_noaa_water_level.py`) and reducing the request delay.



Summary of changes:

1. **Parallel downloads** – Chunks are fetched in parallel using `ThreadPoolExecutor` (8 workers by default).
2. **Shorter delay** – `REQUEST_DELAY` reduced from 0.5 s to 0.05 s between requests.
3. **`--workers` option** – Use `-w` or `--workers` to control concurrency, e.g. `--workers 12`.

This speeds up runs a lot (often several times faster), especially for long date ranges such as 1990–2025. For example, ~180 water_level chunks that were done sequentially can now be fetched concurrently.

---

**User**

what does script: "D:\Brown\SWAT\viewer3\scripts\download_noaa_station.py" do? is it the same?

---

**Cursor**


They are **not** the same. Differences:

| | `download_noaa_station.py` | `download_noaa_one_station.py` |
|---|---|---|
| **Stations** | Several (11 RI/MA stations by default: Providence, Newport, Fall River, etc.) | One station (default: Castle Island 8444069) |
| **Products** | Daily tide/level data: `high_low`, `daily_max_min`, `daily_mean` | 6‑minute data: `water_level`, `predictions`, `air_temperature`, `water_temperature`, `wind`, `air_pressure` |
| **Temporal resolution** | Daily (high/low tides, daily min/max/mean) | 6‑minute |
| **Downloads** | Sequential (0.5 s delay between requests) | Parallel (8 workers) |
| **Use case** | Overview of daily tides/levels across many stations | Detailed sub‑hourly observations and predictions for a single station |

**Summary:** `download_noaa_station.py` fetches daily tide/level summaries for many stations; `download_noaa_one_station.py` fetches high‑resolution 6‑minute water level, predictions, and met data for one station.

---

**User**

edit the download_noaa_station.py so it run and save results at D:\Brown\SWAT\viewer3\noaa

---

**Cursor**


Updated `download_noaa_station.py` so `DEFAULT_OUTPUT_DIR` is set to `D:\Brown\SWAT\viewer3\noaa`. Outputs will be saved there by default.

---

**User**

does it skip already downloaded files. i want it work for all 14 noaa stations

---

**Cursor**


Updating the script to (1) add skip logic for already-downloaded files and (2) include all 14 stations from the domain.



Summary of updates:

1. **Skip existing files** – If `{station}_{product}.csv` exists, that product is skipped. Use `--force` / `-f` to re-download.

2. **All 14 NOAA stations** – `DEFAULT_STATIONS` now includes:
   - 8444069 Castle Island (MA)
   - 8447386 Fall River (MA)
   - 8447387 Borden Flats Light (MA)
   - 8447412 Fall River Visibility (MA)
   - 8447627 New Bedford Barrier Gate (MA)
   - 8447636 New Bedford Harbor (MA)
   - 8452314 Sandy Point Visibility (RI)
   - 8452660 Newport (RI)
   - 8452944 Conimicut Light (RI)
   - 8452951 Potter Cove (RI)
   - 8453662 Providence Visibility (RI)
   - 8454000 Providence (RI)
   - 8454123 Port of Davisville (RI)
   - 8461490 New London (CT)

---

**User**

script download_noaa_one_station.py found no data. script download_noaa_station.py found some data. look at the folder: D:\Brown\SWAT\viewer3\noaa, create a new script with new name (include final in the name). script should get all water_level and predictions for all remaining stations.  

---

**Cursor**


Identifying stations that already have `water_level` and `predictions`:

- water_level: 8447386, 8447636, 8452660, 8452944, 8454000
- predictions: 8447636, 8454000

Creating a script to download water_level and predictions for the remaining stations.



`download_noaa_water_level_final.py` is in place. It:

- **Source stations**: 14 stations from `noaa/noaa_stations_in_domain.csv`
- **Products**: `water_level` (6‑min observed) and `predictions` (6‑min tide)
- **Skip behavior**: Skips a station/product if the output file already exists
- **Output**: `D:\Brown\SWAT\viewer3\noaa\{station}_water_level.csv` and `{station}_predictions.csv`
- **Parallel**: 8 workers (configurable via `--workers`)
- **Defaults**: 2010-01-01 to today

Run it with:
```bash
python scripts/download_noaa_water_level_final.py
```

Use `--force` to re-download existing files. It will attempt all 14 stations; some (e.g. visibility-only) may have no water_level or predictions, and those are skipped.

---

**User**

i receive a message: No Predictions data was found. Please make sure the Datum input is valid.


---

**Cursor**


Checking NOAA API handling for predictions and datum requirements:



Adding datum fallback for predictions: trying MSL when MLLW returns a datum error.



Adding a `--datum-predictions` option so we can force MSL for predictions.



Updates to `download_noaa_water_level_final.py`:

1. **Automatic datum fallback for predictions** – If MLLW returns the datum error, predictions are retried using MSL.
2. **`--datum-predictions` option** – You can force MSL for predictions:
   ```bash
   python scripts/download_noaa_water_level_final.py --datum-predictions MSL
   ```

For stations where MLLW predictions fail, the script will switch to MSL automatically or you can pass `--datum-predictions MSL` directly.

---

**User**

i received the same: No Predictions data was found. Please make sure the Datum input is valid.


---

**Cursor**


Checking the API docs:



Updating the script: subordinate stations only support `interval=hilo` (high/low), not `interval=6`. The datum error can be misleading. Retrying predictions with `interval=hilo` when `interval=6` fails.



Adding a fallback to `interval=hilo` (high/low) — subordinate stations support only high/low predictions, not 6-minute.



Adding an option to use `interval=hilo` from the start:



The script is updated. The NOAA API error can occur when the station is a **subordinate** station and only supports `interval=hilo` (high/low tides), not 6‑minute predictions. Changes made:

1. **Automatic fallback to `interval=hilo`** – If 6‑minute predictions fail (no data or datum error), the script retries with `interval=hilo`, which subordinate stations support.
2. **`--interval-predictions` option** – You can force high/low predictions from the start:
   ```bash
   python scripts/download_noaa_water_level_final.py --interval-predictions hilo
   ```

Run:
```bash
python scripts/download_noaa_water_level_final.py
```

If 6‑minute predictions fail, it will automatically retry with high/low predictions and save them with a note like `(hilo fallback)` in the output. To use high/low predictions only:
```bash
python scripts/download_noaa_water_level_final.py --interval-predictions hilo
```

---

**User**

create a new script for getting daily data of water level and prediction. do not edit current script

---

**Cursor**


Added `scripts/download_noaa_daily_water_level.py`. It does the following:

- **high_low**: Observed daily high/low tide times and heights (1 year per request)
- **predictions (hilo)**: Predicted daily high/low tides (10 years per request)

**Output files:**
- `{station}_high_low.csv` – observed daily high/low water levels
- `{station}_predictions_daily.csv` – predicted daily high/low tides

**Behavior:** Same as the existing script: stations from `noaa_stations_in_domain.csv`, skips existing files, parallel fetches (8 workers), output to `D:\Brown\SWAT\viewer3\noaa`.

**Run:**
```bash
python scripts/download_noaa_daily_water_level.py
```

---

**User**

for the vtec images, i want to remap them so the x-axis ends at 31 dec 2025

---

**Cursor**


Noting the script already sets the x-axis to 31 Dec 2025. Checking for other references and ensuring the axis ends exactly at 31 Dec 2025:



Adding `--x-max` and ensuring the x-axis ends at 31 Dec 2025 (end of day):



Updates in `scripts/plot_vtec_timeline_all_stations.py`:

1. **X-axis end fixed at 31 Dec 2025** – The right edge is set to 31 Dec 2025 23:59:59 so the full last day is shown.

2. **CLI options for x-axis range:**
   ```bash
   python scripts/plot_vtec_timeline_all_stations.py --x-max 2025-12-31
   python scripts/plot_vtec_timeline_all_stations.py --x-min 2010-01-01 --x-max 2025-12-31
   ```

The default x-axis range remains 1 Jan 2010–31 Dec 2025. Regenerate the figures with:

```bash
python scripts/plot_vtec_timeline_all_stations.py
```

---

**User**

in the vtec images, x-axis should be similar to discharge chart. it starts from 1 Jan 1950 and ends on 31 dec 2025, with labels as years with 10 yrs increments. consider this role for all maps in this project

---

**Cursor**


Creating a shared constants module and updating all plot scripts to use the discharge-chart convention (1 Jan 1950–31 Dec 2025, 10-year labels).



Updating the shared module to only set formatter and locator; callers will set limits.



Checking whether other scripts need `sys.path` — they import from the same package:



Summary of changes:

### 1. Shared module: `scripts/chart_axis_constants.py`
- **X_MIN**: 1 Jan 1950  
- **X_MAX**: 31 Dec 2025 (end of day)  
- **`apply_chart_xaxis(ax)`**: sets xlim to 1950–2025 and year labels every 10 years (1950, 1960, 1970, …)

### 2. Updated plot scripts
All use the same x-axis convention:

| Script | Change |
|--------|--------|
| **plot_vtec_timeline_all_stations.py** | 1950–2025, YearLocator(10) |
| **plot_noaa_meteorological.py** | 1950–2025, YearLocator(10) |
| **plot_noaa_water_level_with_predictions.py** | 1950–2025, YearLocator(10) |
| **plot_precipitation_noaa_stations.py** | 1950–2025, YearLocator(10) (was data range) |

### Rule for new plots
Import from the shared module:
```python
from chart_axis_constants import apply_chart_xaxis
# then call:
apply_chart_xaxis(ax, set_limits=True)
```

Use `set_limits=False` only if xlim is set manually (e.g., VTEC with custom `--x-min`/`--x-max`).

---

**User**

should i plot charts again? how?

---

**Cursor**


Yes. To get the new x-axis (1950–2025, 10-year labels), you need to regenerate the plots.

From the project root (`D:\Brown\SWAT\viewer3`):

```powershell
# VTEC timelines
python scripts/plot_vtec_timeline_all_stations.py

# Water level with predictions
python scripts/plot_noaa_water_level_with_predictions.py

# Meteorological (water level + met)
python scripts/plot_noaa_meteorological.py

# Precipitation
python scripts/plot_precipitation_noaa_stations.py
```

You can also use `BUILD.bat`, which includes VTEC and other steps:

```powershell
BUILD.bat
```

That will run the fetch and plot steps defined in `BUILD.bat`.

---

**User**

tell me source of data for these 4 scripts

---

**Cursor**


Data sources for the four plot scripts:

---

### 1. **plot_vtec_timeline_all_stations.py**
- **Input:** `docs/vtec_by_usgs_and_noaa/vtec_events_<STAID>.csv`
- **Source:** IEM VTEC API (Iowa State) – NWS watches/warnings/advisories  
- **URL:** `https://mesonet.agron.iastate.edu/json/vtec_events_bypoint.py`  
- **Fetched by:** `fetch_vtec_by_usgs_and_noaa_locations.py` (uses USGS and NOAA station coordinates)

---

### 2. **plot_noaa_water_level_with_predictions.py**
- **Input:** `noaa/{station}_water_level.csv`, `noaa/{station}_predictions.csv`
- **Source:** NOAA CO-OPS Tides & Currents API  
- **URL:** `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`  
- **Fetched by:** `download_noaa_water_level_final.py`, `download_noaa_one_station.py`, or `download_noaa_water_level.py`

---

### 3. **plot_noaa_meteorological.py**
- **Input:** `noaa/{station}_*.csv` (water level and met files)
- **Source:** NOAA CO-OPS Tides & Currents API  
- **URL:** `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`  
- **Fetched by:** `download_noaa_one_station.py` (air temp, wind, pressure, water temp, humidity, visibility)

---

### 4. **plot_precipitation_noaa_stations.py**
- **Input:** `pr_extracted/pr_<STAID>.csv` (nearest USGS location per NOAA station)
- **Source:** GPM IMERG Final daily precipitation (NASA)  
- **URL:** `https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/GPM_3IMERGDF.07/`  
- **Pipeline:** `download_gpm_imerg_region_cloud.py` → NetCDF files → `extract_pr_at_locations.py` → `pr_extracted/`

---

**User**

for all figures, size should be the same. consider this as a role

---

**Cursor**


Adding shared figure size constants and updating all plot scripts.



Summary of changes:

### `scripts/chart_axis_constants.py`
- **FIG_WIDTH** = 12 inches  
- **FIG_HEIGHT** = 4 inches  
- **FIG_SIZE** = (12, 4)

### Updated plot scripts

| Script | Figure size |
|--------|-------------|
| **plot_vtec_timeline_all_stations.py** | `FIG_SIZE` (12×4) |
| **plot_noaa_water_level_with_predictions.py** | `FIG_SIZE` (12×4) |
| **plot_precipitation_noaa_stations.py** | `FIG_SIZE` (12×4) |
| **plot_noaa_meteorological.py** | `(FIG_WIDTH, FIG_HEIGHT × nrows)` — width 12", height 4" per panel |

Single-panel figures use 12×4 inches; the meteorological multi-panel plot keeps width 12 and scales height with the number of panels.

**Rule for new figures:**  
```python
from chart_axis_constants import FIG_SIZE  # single panel
# or
from chart_axis_constants import FIG_WIDTH, FIG_HEIGHT  # multi-panel: (FIG_WIDTH, FIG_HEIGHT * nrows)
```

---

**User**

add title within discharge plot that include the station ID

---

**Cursor**


Adding a Chart.js title inside the discharge chart that includes the station ID.



Added a Chart.js title inside the discharge chart that shows the station ID.

**Updates in `frontend/js/app.js`, `docs/js/app.js`, and `app.js`:**

1. **Chart title** – The chart now shows the station ID inside the plot via Chart.js’s title plugin:  
   `"Discharge (cfs) — Station 01108000"` (for example).

2. **`drawDischargeChart`** – Accepts an optional second argument: the formatted station ID for the title.

3. **Call sites** – All calls to `drawDischargeChart` now pass the station ID so the title is set correctly.

---

**User**

change the role so all charts/figures start on 1 Jan 2010 and end on 31 Dec 2025. add labels in x-axis as year with increment 2 yrs

---

**Cursor**


Updating the JavaScript discharge chart x-axis:



Updates are applied across all chart/figure code.

### Python scripts (`chart_axis_constants.py` + plot scripts)
- **X_MIN**: 1 Jan 2010  
- **X_MAX**: 31 Dec 2025  
- **Year labels**: every 2 years (`YearLocator(2)`)

### JavaScript discharge chart (`frontend/js/app.js`, `docs/js/app.js`, `app.js`)
- **x-axis**: 1 Jan 2010 – 31 Dec 2025  
- **Tick spacing**: `time.stepSize: 2` (labels every 2 years)

### Files touched
- `scripts/chart_axis_constants.py`
- `scripts/plot_vtec_timeline_all_stations.py`
- `scripts/plot_noaa_meteorological.py`
- `scripts/plot_noaa_water_level_with_predictions.py`
- `scripts/plot_precipitation_noaa_stations.py`
- `frontend/js/app.js`
- `docs/js/app.js`
- `app.js`

Regenerate the Python figures with:
```bash
python scripts/plot_vtec_timeline_all_stations.py
python scripts/plot_noaa_water_level_with_predictions.py
python scripts/plot_noaa_meteorological.py
python scripts/plot_precipitation_noaa_stations.py
```

---

**User**

the NOAA water level map for station 8454000 appear under all noaa stations. it should be under corresponding station only

---

**Cursor**


Checking the image-update logic — cached/previous images may remain visible:



Clearing the image before loading the new URL to prevent the previous image (e.g. 8454000) from remaining when the new URL returns 404:



Removing the fallback in `docs/js/app.js` that loads 8454000 when a station's water-level image is missing.



The problem was in `docs/js/app.js`: the water level `onerror` handler was always loading station 8454000’s image as a fallback:

```javascript
img.onerror = function () {
  img.src = base + "images/noaa/8454000_water_level_with_predictions.png";
};
```

**Updates in `frontend/js/app.js` and `docs/js/app.js`:**

1. **Remove 8454000 fallback** – When a station’s water level image is missing (404), show “No water level data available for this station” instead of loading 8454000.
2. **Clear previous image** – Set `img.src = ""` and call `img.removeAttribute("src")` in `onerror` so the previous image is not shown.
3. **Same logic for meteorological and precipitation** – Each figure is tied only to the selected station.

Each NOAA station now shows only its own water level, meteorological, and precipitation data; if data is missing, the “No … data available” message is shown.

---

**User**

give me script that can download data of Predictions, Verified, Preliminary, (Observed - Predicted) for period 1 jan 2010 to 31 dec 2025 from https://tidesandcurrents.noaa.gov/waterlevels.html?id=8447386&units=standard&bdate=20100101&edate=20251231&timezone=GMT&datum=MLLW&interval=h&action=data . results saved at D:\Brown\SWAT\viewer3\noaa

---

**Cursor**


Created `scripts/download_noaa_waterlevels_station.py`.

**What it downloads (from the [NOAA CO-OPS API](https://api.tidesandcurrents.noaa.gov/api/prod/)):**

| Data | Source | Output file |
|------|--------|-------------|
| **Verified + Preliminary** | `water_level` product (Quality: v=verified, p=preliminary) | `{station}_water_level.csv` |
| **Predictions** | `predictions` product (6-min or hilo fallback) | `{station}_predictions.csv` |
| **Observed − Predicted** | Water level − predictions at matching timestamps | `{station}_observed_minus_predicted.csv` |

**Defaults:** Station 8447386, 1 Jan 2010–31 Dec 2025, output: `D:\Brown\SWAT\viewer3\noaa`

**Run:**
```bash
python scripts/download_noaa_waterlevels_station.py
```

**With options:**
```bash
python scripts/download_noaa_waterlevels_station.py --station 8447386 --begin 20100101 --end 20251231
```

---

**User**

in noaa website, i noticed there are only these stations that have water levels data: https://tidesandcurrents.noaa.gov/waterlevels.html?id=8447386 https://tidesandcurrents.noaa.gov/waterlevels.html?id=8447636 https://tidesandcurrents.noaa.gov/waterlevels.html?id=8452660 https://tidesandcurrents.noaa.gov/waterlevels.html?id=8452660 https://tidesandcurrents.noaa.gov/waterlevels.html?id=8452660 https://tidesandcurrents.noaa.gov/waterlevels.html?id=8461490 . add a note of that. then, check the folder D:\Brown\SWAT\viewer3\noaa and tell me what is there and what still missing from these stations

---

**Cursor**


Summary:

### Note created
`noaa/WATER_LEVEL_STATIONS_NOTE.txt` – lists the four NOAA stations that have water level data on the NOAA Tides & Currents site.

---

### Contents of `D:\Brown\SWAT\viewer3\noaa`

| Station | water_level | predictions | high_low | daily_max_min |
|--------:|:-----------:|:-----------:|:--------:|:-------------:|
| **8447386** | ✓ | ✓ | ✓ | ✓ |
| **8447636** | ✓ | ✓ | ✓ | ✓ |
| **8452660** | ✓ | ✗ | ✓ | ✓ |
| **8461490** | ✗ | ✗ | ✗ | ✗ |

### What’s missing

1. **8452660** – `predictions.csv` is missing.
2. **8461490** – no water level products at all (`water_level.csv`, `predictions.csv`, `high_low.csv`, `daily_max_min.csv`).

Additional files in the folder (8452944, 8454000) belong to other stations and are not part of these four.

To download the missing data:

```bash
# 8452660 predictions
python scripts/download_noaa_water_level_final.py --stations 8452660

# 8461490 water_level and predictions
python scripts/download_noaa_water_level_final.py --stations 8461490
```

---

**User**

i gave you 6 links to 6 stations not 4

---

**Cursor**


Checking the six links: 8452660 appeared three times. Inferring the six intended station IDs from the domain and folder.



Updating the note to list six stations. The links show 8447386, 8447636, 8452660 (three times), and 8461490. Inferring 8452944 and 8454000 as the fifth and sixth stations — they have water level files in the folder.



Updated the note to list all 6 stations. Status for `D:\Brown\SWAT\viewer3\noaa`:

### Contents and gaps (6 water level stations)

| Station | Name | water_level | predictions | high_low | daily_max_min |
|--------:|------|:-----------:|:-----------:|:--------:|:-------------:|
| **8447386** | Fall River | ✓ | ✓ | ✓ | ✓ |
| **8447636** | New Bedford Harbor | ✓ | ✓ | ✓ | ✓ |
| **8452660** | Newport | ✓ | ✗ | ✓ | ✓ |
| **8452944** | Conimicut Light | ✓ | ✗ | ✓ | ✓ |
| **8454000** | Providence | ✓ | ✓ | ✓ | ✗ |
| **8461490** | New London | ✗ | ✗ | ✗ | ✗ |

### Missing

1. **8452660** – `predictions.csv`
2. **8452944** – `predictions.csv`
3. **8454000** – `daily_max_min.csv`
4. **8461490** – `water_level.csv`, `predictions.csv`, `high_low.csv`, `daily_max_min.csv`

If you intended different stations instead of the two 8452660 repeats, say which ones and I can adjust the note.

---

**User**

edit the script scripts/download_noaa_waterlevels_station.py to download predictions, verified, preliminary, observed-predicted records for these 6 stations. if anything exist, script will skip

---

**Cursor**


Updates made to `scripts/download_noaa_waterlevels_station.py`:

1. **6 default stations** – 8447386, 8447636, 8452660, 8452944, 8454000, 8461490
2. **Skip existing files** – If a file exists, it is not re-downloaded or recomputed
3. **Loop over all stations** – Each station is processed in turn
4. **`--force` / `-f`** – Forces re-download/recompute even when files exist
5. **`--stations`** – Optional list of station IDs to use instead of the default 6

**Run:**
```bash
python scripts/download_noaa_waterlevels_station.py
```

**Override stations:**
```bash
python scripts/download_noaa_waterlevels_station.py --stations 8447386 8461490
```

**Force re-download:**
```bash
python scripts/download_noaa_waterlevels_station.py --force
```

---

**User**

i need new script that download available meteorological data from all 14 noaa stations during the period (1 jan 2010 to 31 dec 2025). script will save results at D:\Brown\SWAT\viewer3\noaa and will get data from like this link https://tidesandcurrents.noaa.gov/met.html?id=8447386 

---

**Cursor**


Added `scripts/download_noaa_meteorological_all.py`.

**What it does**
- Uses the same CO-OPS API as [https://tidesandcurrents.noaa.gov/met.html](https://tidesandcurrents.noaa.gov/met.html)
- Fetches met data for all 14 stations from `noaa/noaa_stations_in_domain.csv`
- Time range: 1 Jan 2010 – 31 Dec 2025
- Output directory: `D:\Brown\SWAT\viewer3\noaa`

**Products**
- `air_temperature`, `water_temperature`, `wind`, `air_pressure`, `humidity`, `visibility`

**Output files**
- `{station}_{product}.csv`, e.g. `8447386_air_temperature.csv`, `8447386_wind.csv`

**Logic**
- Skips any output file that already exists
- Uses `--force` to re-download and overwrite
- Only standard library (no `requests` or `pandas`)

**Run**
```bash
python scripts/download_noaa_meteorological_all.py
```

**Force re-download**
```bash
python scripts/download_noaa_meteorological_all.py --force
```

---

**User**

look at files at D:\Brown\SWAT\viewer3\events. what is there?

---

**Cursor**


The `D:\Brown\SWAT\viewer3\events` folder has **2 files**:

---

### 1. **hist_hurr.txt** (~16 KB)
Tab-separated historical hurricane/tropical cyclone track data, with columns such as:
- **basin**, **number**, **year**, **name** – storm identifiers  
- **status_of_system** – TS (Tropical Storm), HU (Hurricane), EX (Extratropical), TD (Tropical Depression)  
- **latitude**, **longitude** – position  
- **month**, **day**, **hour**, **minute** – time  
- **maximum_sustained_wind**, **minimum_pressure** – intensity  
- **entries**, **statuses_of_system**, **record_identifier** – metadata  
- **Shape**, **Shape_Length** – geometry  

Includes storms from 1851 onward, focused on Atlantic basin events near the Northeast US coast (RI, MA, CT area).

---

### 2. **New Text Document.txt** (~1 KB)
A short markdown table of **recent storm events** (2010–2023):

| Year | Storm            | Type                            | RI  | MA  | Notes           |
|------|------------------|----------------------------------|-----|-----|-----------------|
| 2010 | March Nor'easter | Extratropical                   | ✔   | ✔   | Severe flooding |
| 2011 | Irene            | Hurricane/Post-tropical         | ✔   | ✔   | Major flooding  |
| 2012 | Sandy            | Hurricane → Extratropical       | ✔   | ✔   | Surge & wind    |
| 2017 | Jose, Philippe   | Tropical / Extratropical        | (✔) | (✔) | Indirect        |
| 2019 | Melissa          | Subtropical → Extratropical     | (✔) | (✔) | Indirect        |
| 2023 | Lee              | Hurricane (offshore)            | (✔) | (✔) | Marine impacts  |

---

**User**

are storms at New Text Document.txt already mentioned at hist_hurr.txt? 

---

**Cursor**


No. None of the storms in New Text Document.txt appear in hist_hurr.txt.

### Storms in New Text Document.txt vs hist_hurr.txt

| Storm               | Year | In hist_hurr.txt? |
|---------------------|------|--------------------|
| March Nor'easter    | 2010 | No                 |
| Irene               | 2011 | No                 |
| Sandy               | 2012 | No                 |
| Jose                | 2017 | No                 |
| Philippe            | 2017 | No                 |
| Melissa             | 2019 | No                 |
| Lee                 | 2023 | No                 |

### Years covered in hist_hurr.txt

`hist_hurr.txt` has tropical cyclone tracks for 1851 onward, but not for 2010–2012, 2017, 2019, or 2023. Years that do appear include 2000, 2004, 2005, 2006, 2007, 2008, 2013, 2015, 2016, and 2021 (Andrea, Ana, Hermine, Elsa, Fred, Henri, Ida, etc.).

So Irene, Sandy, Jose, Philippe, Melissa, and Lee are missing from the file. The 2010 March Nor'easter is an extratropical nor'easter, not a tropical cyclone, so it would normally not be in a tropical cyclone database like this.

---

**User**

can you search all storms and cyclones hit RI, MA, and CT states during 1 jan 2010 and 31 dec 2025. add results in new file

---

**Cursor**


Creating a comprehensive results file.



Created a results file at **`events/ri_ma_ct_storms_2010_2025.txt`** with all storms and cyclones that affected Rhode Island, Massachusetts, and Connecticut from January 1, 2010, to December 31, 2025.

The file includes:
- **36 documented events** (tropical cyclones, post-tropical systems, nor'easters, and major winter storms)
- **Details per storm**: date, name, type, states affected, and main impacts

**Highlights:**

| Year | Notable storms |
|------|----------------|
| 2010 | March Nor'easter (severe flooding), Hurricane Earl (offshore) |
| 2011 | Hurricane Irene (major flooding, 16 deaths in New England) |
| 2012 | Hurricane Sandy (surge and coastal damage) |
| 2016 | January Blizzard, Hermine remnants |
| 2017 | Hurricane Jose, Tropical Storm Philippe |
| 2018 | March Nor'easter, Florence/Michael remnants |
| 2019 | Dorian, Tropical Storm Melissa |
| 2020 | Isaias, Zeta (snow), Fay |
| 2021 | Elsa (RI landfall), Henri (RI landfall), Ida remnants, winter storms |
| 2023 | Hurricane Lee |
| 2024 | February Nor'easter, Beryl/Debby/Ernesto remnants |
| 2025 | Chantal, Hurricane Erin |

**Direct tropical landfalls in the three states:** Henri (2021) and Elsa (2021), both in Rhode Island. Irene and Sandy made landfall elsewhere but caused major impacts in RI, MA, and CT.

The file also notes NOAA’s Storm Events Database for more detailed, event-by-event data.

---

**User**

rearrange hist_hurr.txt file in a new text file that have only name, statuses_of_system, maximum_sustained_wind, minumum pressure, date (yy, mm, dd, hh, mm), and lat, lon

---

**Cursor**


Created **`events/hist_hurr_rearranged.txt`** with only these columns from `hist_hurr.txt`:

| Column | Description |
|--------|-------------|
| name | Storm name |
| statuses_of_system | Storm status (e.g., ["TS"], ["HU","TS"]) |
| maximum_sustained_wind | Wind speed (knots) |
| minimum_pressure | Min pressure (mb; -999 = missing) |
| year | Year |
| month | Month |
| day | Day |
| hour | Hour |
| minute | Minute |
| latitude | Latitude |
| longitude | Longitude |

The file is tab-separated, includes a header row, and has 162 data rows matching the original input.

---

**User**

keep only events occurred bet 1 jan 2010 and 31 dec 2025

---

**Cursor**


Filtering is complete. `hist_hurr_rearranged.txt` now contains only events between 1 Jan 2010 and 31 Dec 2025. The file has **15 data rows** covering these storms:

| Storm   | Year | Date range     |
|---------|------|----------------|
| ANDREA  | 2013 | Jun 8          |
| ANA     | 2015 | May 12         |
| HERMINE | 2016 | Sep 8          |
| ELSA    | 2021 | Jul 9          |
| FRED    | 2021 | Aug 20         |
| HENRI   | 2021 | Aug 22–24      |
| IDA     | 2021 | Sep 2          |

---

**User**

do filtering in new text file. do not edit prevoius file. create new one

---

**Cursor**


Creating `hist_hurr_2010_2025.txt` with filtered data and restoring `hist_hurr_rearranged.txt` to the full dataset.



Restoring `hist_hurr_rearranged.txt` to the full dataset:



Changes made:

1. **`hist_hurr_2010_2025.txt` created** – New file with only events from 1 Jan 2010 to 31 Dec 2025 (15 rows).
2. **`hist_hurr_rearranged.txt` restored** – Original file restored with the full rearranged dataset (161 rows).

The filtered file contains ANDREA, ANA, HERMINE, ELSA, FRED, HENRI, and IDA.

---

**User**

add eveents in New Text Document.txt and ri_ma_ct_storms_2010_2025 to hist_hurr_2010_2025. if event exist, do not repeat again. you may update info

create new text file. do not overwrite hist_hurr_2010_2025

---

**Cursor**


Creating `hist_hurr_2010_2025_merged.txt` with events from all three sources, avoiding duplicates.



Created **`events/hist_hurr_2010_2025_merged.txt`** without changing `hist_hurr_2010_2025.txt`.

The merged file contains:

- **From hist_hurr_2010_2025**: Andrea, Ana, Hermine, Elsa, Fred, Henri, Ida (with full track points)
- **From New Text Document**: March Nor'easter 2010, Irene, Sandy, Jose, Philippe, Melissa, Lee
- **From ri_ma_ct_storms_2010_2025**: Earl 2010, March Nor'easter 2013, Joaquin, January Blizzard 2016, March Nor'easter 2018, Florence, Michael, Dorian, Fay, Isaias, Zeta, Winter Storms 2020–2021, Earl 2022, February Nor'easter 2024, Beryl, Debby, Ernesto, Chantal, Erin

Events already present in `hist_hurr_2010_2025` are not duplicated. Events without IBTrACS track data were added with representative dates and approximate southern New England coordinates (lat ~41.5, lon ~71.5).

---

**User**

what do you think best way to present the merged file at https://saaj12.github.io/Hydrological_Modeling_RI/ . do not take action. just advise me?

---

**Cursor**


Here are practical ways to present the merged storm file on your Hydrological Modeling RI site:

---

### 1. **Map layer**

Add storm events as a map layer that users can toggle. Each event has `latitude` and `longitude`, so they can be drawn as markers or symbols. For multi-point storms (e.g., Henri, Elsa), connect points into tracks.

- **Pros**: Directly relates storms to station locations; easy to see regional impact.
- **Cons**: Track geometry is sparse for events with a single point.

---

### 2. **Storm selector + date filter**

Add a storm dropdown (e.g. “Storm events 2010–2025”). Choosing a storm:

- Filters discharge/water level/precipitation to that event’s date range
- Optionally zooms the map to that storm’s region

- **Pros**: Direct link between storms and hydrologic data; supports analysis of flooding events.
- **Cons**: Needs date-range logic per event (start/end dates).

---

### 3. **Time series annotations**

Mark storm dates on your discharge/water level/precipitation charts (vertical lines or shaded regions, e.g. “Henri – Aug 22, 2021”). Useful for correlating spikes with known storms.

- **Pros**: Strong for explaining large peaks; low development effort.
- **Cons**: Can get crowded if many events are shown at once.

---

### 4. **Combination (recommended)**

- **Map layer**: Show storm markers/tracks, color-coded by year or type.
- **Storm selector**: Choose a storm → filter or highlight its date range in the time series.
- **Event list**: Table or sidebar listing storms (name, date, type) as a reference.

---

### 5. **Technical approach**

- Convert the merged file to JSON (similar to `discharge_data.json`) and load it as a config/data file.
- Include `name`, `year`, `month`, `day`, `latitude`, `longitude`, and optionally `statuses_of_system` and `maximum_sustained_wind`.
- For events with multiple points, store them as arrays of `{lat, lon, date}`.
- For single-point events (nor’easters, etc.), derive a nominal date from year/month/day.

---

### Recommendation

Use **Option 4**: map layer + storm selector + event list. Storms are important drivers of hydrological extremes in your region, and this setup lets users connect storms to discharge and water levels without changing the site’s main focus on station data.

---

**User**

i will consider comination of way 3 and 2. but add black bars indicate start/end date of storm instead of vertical lines or shaded regions. if you couldnt do both ways, consider 3

---

**Cursor**


Implementing the storm selector, date filter, and black-bar annotations.



Summary of what was implemented:

## Implementation Summary

### 1. **Storm data export** (`scripts/export_storms_data.py`)
- Reads `events/hist_hurr_2010_2025_merged.txt`
- Produces `storms_data.json` with storm id, name, year, `startDate`, `endDate`, `displayLabel`
- Outputs to `frontend/data/storms_data.json` and `docs/data/storms_data.json`

### 2. **Storm selector (Way 2 – date filter)**
- Added a “Storm events (RI/MA/CT 2010–2025)” dropdown above the discharge chart
- Options: “— show all (with storm bars) —” plus one option per storm
- When a storm is selected:
  - Discharge series is filtered to the storm’s start/end dates
  - Chart x-axis zooms to that range
  - Storm name is shown in the chart title

### 3. **Black bar annotations (Way 3)**
- Uses `chartjs-plugin-annotation` (v2.2.1, Chart.js 3 compatible)
- For each storm, draws a black horizontal bar (`rgba(0,0,0,0.6)`) at the top of the chart from `startDate` to `endDate`
- Bars are ~5% of the y-axis height, at the top of the chart

### 4. **Files changed**
- **frontend/index.html** – Storm selector UI and annotation plugin script
- **frontend/js/app.js** – `loadStormsData`, storm selector handler, `drawDischargeChart` with date filtering and annotations
- **frontend/css/style.css** – Styles for storm controls
- **BUILD.bat** – Calls `export_storms_data.py` before preparing docs

### 5. **Behavior**
- On “show all”, discharge is unfiltered; storm bars are drawn across the full timeline
- On storm select, discharge is filtered, x-axis zooms to the storm dates, and that storm’s bar is visible in the zoomed range

`storms_data.json` is produced by the export script and included in the build. Run `BUILD.bat` or `python scripts/export_storms_data.py` to regenerate it.

---

**User**

nothing has changed in the github page. i cannot see storms update.

---

**Cursor**


Syncing docs: `docs/index.html` lacks the storm selector and annotation script; `frontend/` has the updates. Running the build to copy frontend into `docs`.



`docs/` is now updated with the storm controls and storm bar annotations. Next steps to see the changes on GitHub Pages:

**1. Commit and push the updated docs**

```bash
git add docs/
git add frontend/   # if you want the source frontend changes too
git status
git commit -m "Add storm events (RI/MA/CT 2010-2025) to discharge chart"
git push
```

**2. Wait for GitHub Pages**

After pushing, GitHub Pages may take 1–2 minutes to rebuild. Refresh https://saaj12.github.io/Hydrological_Modeling_RI/

**3. Confirm it works**

1. Select a USGS discharge station from the dropdown or map.
2. You should see:
   - **Storm events (RI/MA/CT 2010–2025)** dropdown above the discharge chart
   - Black bars on the chart for each storm
   - Filtering and zoom when you pick a specific storm

---

**If it still doesn’t appear**, check:

1. **GitHub Pages settings** – In the repo, **Settings → Pages** → Source: deploy from branch `main` (or `master`), folder: `/docs`.
2. **Correct URL** – If the repo name differs from `Hydrological_Modeling_RI`, the base URL will be different.
3. **Deploy status** – **Actions** tab for any failed GitHub Pages workflows.

---

**User**

storm bars are not clear. I cannot see them. did you add these bars to all plots? is it becase background is black in discharge figure? 

---

**Cursor**


Addressing the issues:

1. Visibility: Black bars (`rgba(0,0,0,0.6)`) on the dark chart background (#0d1117) are nearly invisible.
2. Scope: Storm bars were added only to the discharge chart. Water level, precipitation, VTEC, and meteorological plots are pre-generated PNGs; we can't add interactive annotations without modifying the Python scripts.

Changing storm bars to a contrasting color so they’re visible on the dark background.



Making the bars slightly thicker for better visibility:



Two updates were made:

1. **Bar color**: Switched from black (`rgba(0,0,0,0.6)`) to **semi-transparent white** (`rgba(255,255,255,0.4)`) with a white border so the bars stand out on the dark background.
2. **Bar size**: Increased height from about 5% to about 17% of the chart area to make them easier to see.

Storm bars are still only on the **discharge chart**; the water level, precipitation, VTEC, and meteorological plots are static images from Python, so bars there would require changes to those scripts.

Run `python scripts/prepare_gh_pages.py` and push to update GitHub Pages. You can also test locally by opening `frontend/index.html` in a browser.

---

**User**

instead of having Water level, precipitation, VTEC, and meteorological plots are pre-generated PNGs. can i get them like discharge plot?

---

**Cursor**


Converting the four plot types from PNGs to interactive Chart.js charts. Exploring data files and structure:



Creating export scripts and converting the frontend to use Chart.js.



Implementing frontend Chart.js rendering. Reading `app.js` structure:



Implementing incrementally: updating the HTML structure, then adding Chart.js logic.



Implementing the conversion: updating the HTML first, then the app logic.



Summary of the changes:

## Converted Water Level, Precipitation, Meteorological, and VTEC to Chart.js

### 1. **Export scripts** (create JSON from existing CSVs)
- `scripts/export_water_level_data.py` – from `noaa/*_water_level.csv` and `*_predictions.csv`
- `scripts/export_precipitation_data.py` – from `pr_extracted/` (nearest USGS to NOAA stations)
- `scripts/export_meteorological_data.py` – from `noaa/*_air_temperature.csv`, `*_wind.csv`, etc.
- `scripts/export_vtec_data.py` – from `docs/vtec_by_usgs_and_noaa/vtec_events_*.csv`

Outputs: `frontend/data/water_level_data.json`, `precipitation_data.json`, `meteorological_data.json`, `vtec_data.json`

### 2. **HTML updates**
- Storm selector moved outside the discharge chart so it applies to all time-series charts
- Water level, precipitation, meteorological, and VTEC `img` elements replaced with `canvas` elements for Chart.js

### 3. **App logic**
- Data loading for the new JSON sources
- Chart.js rendering for water level, precipitation, meteorological, and VTEC
- Storm bar annotations added to all five chart types
- Storm filter applies to discharge, water level, precipitation, meteorological, and VTEC

### 4. **Build**
- `BUILD.bat` updated to run the new export scripts before `prepare_gh_pages`

---

**Generate data and deploy**

```bash
python scripts/export_water_level_data.py
python scripts/export_precipitation_data.py
python scripts/export_meteorological_data.py
python scripts/export_vtec_data.py
python scripts/prepare_gh_pages.py
```

Or run `BUILD.bat`, which runs these and other steps.

**Data dependencies**
- Water level: `noaa/*_water_level.csv`, `*_predictions.csv`
- Precipitation: `pr_extracted/pr_all_locations.csv` and `pr_<usgs_id>.csv`
- Meteorological: `noaa/*_air_temperature.csv`, `*_wind.csv`, etc.
- VTEC: `docs/vtec_by_usgs_and_noaa/vtec_events_<staid>.csv`

If any JSON files are missing, the app shows “No … data available” for those panels.

---

**User**

add these 6 points as roles: 1- all charts have white background. 2- space between charts is enough and x-axis labels are visible. 3- all charts should have titles with the station ID included in the title. 4- all charts x-axes start on 1 jan 2010 and end at 31 dec 2025. 5- labels in x-axes are years with 2 yrs increments. 6- all charts have the same size with y-axes aligned vertically.

---

**Cursor**


Using the section h3 for titles (with station ID) instead of duplicating with Chart.js titles:



Summary of the updates:

## Changes applied

### 1. **White background**
- `.chart-wrap` background set to `#ffffff` (from `#0d1117`)
- Chart area border set to `#ddd`

### 2. **Spacing and x-axis labels**
- Chart padding: `0.75rem 1rem 1rem`
- `margin-bottom: 2rem` between charts
- Chart area padding: `{ top: 4, right: 8, bottom: 16, left: 8 }` for x-axis labels

### 3. **Titles with station ID**
- Discharge: `"Discharge (cfs) — Station " + idDisplay` (via `discharge-chart-title`)
- Water level: `"Water level (m MLLW) — Station " + noaaId`
- Precipitation: `"Precipitation (mm/day) — Station " + noaaId`
- Meteorological: `"Water level & meteorological — Station " + noaaId`
- VTEC: `"VTEC — Station " + idForVtec`

### 4. **X-axis range**
- All charts use `min: "2010-01-01"` and `max: "2025-12-31"` (discharge can override when a storm is selected)

### 5. **X-axis labels (years, 2-year increment)**
- `time: { unit: "year", stepSize: 2 }` on all time-based charts

### 6. **Same size and aligned y-axes**
- Chart height: `240px` (canvas `200px`)
- `layout.padding` for spacing
- `scales.y.minWidth: 48` so y-axis areas have similar width and align

### Additional
- Tick and grid colors updated to `#333` and `#e0e0e0` for white background
- Storm bar styling changed to `rgba(0,0,0,0.12)` for visibility on white

