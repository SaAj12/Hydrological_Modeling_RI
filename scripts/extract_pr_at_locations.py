"""
Extract daily precipitation (pr) from downloaded GPM IMERG .nc4 files
at locations listed in USGS Excel (51 locations) and optionally NOAA CSV (14 locations).

Input:
  - Directory of daily files: gpm_imerg_region/*.nc (or --input-dir)
  - USGS locations: usgs_locations.xlsx (or --locations path)
    Expected columns: STAID, LAT, LON.
  - NOAA locations (optional): noaa/noaa_stations_in_domain.csv (or --noaa-csv path)
    Expected columns: id, lat, lon. Use --noaa-csv to include 14 NOAA stations.

Output:
  - pr_all_locations.csv: date, location_id, lat, lon, pr_mm_per_day
  - pr_timeseries.xlsx: Date column + one column per location (pr in mm/day)
  - pr_<id>.csv: per-location time series (mm/day)

Usage (from project root D:\\Brown\\SWAT\\viewer3):
  pip install pandas openpyxl xarray netCDF4
  python scripts/extract_pr_at_locations.py
  python scripts/extract_pr_at_locations.py -i gpm_imerg_region -l usgs_locations.xlsx --noaa-csv noaa/noaa_stations_in_domain.csv
"""
import argparse
import datetime as dt
import os
import re
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)

# Default paths (relative to project root)
DEFAULT_LOCATIONS = os.path.join(PROJECT_ROOT, "usgs_locations.xlsx")
DEFAULT_NOAA_CSV = os.path.join(PROJECT_ROOT, "noaa", "noaa_stations_in_domain.csv")
DEFAULT_INPUT_DIR = os.path.join(PROJECT_ROOT, "gpm_imerg_region")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "pr_extracted")

# IMERG daily NetCDF: precipitation variable and coords
PR_VAR_NAMES = ("precipitationCal", "precipitation", "precipitationUncal")
MIN_DATE = dt.date(2010, 1, 1)
LAT_NAMES = ("lat", "latitude", "Latitude")
LON_NAMES = ("lon", "longitude", "Longitude")


def _staid_to_text(val) -> str:
    """Format STAID as text, preserving leading zeros (e.g. 01108000 not 1108000)."""
    if val is None or val == "" or (isinstance(val, float) and str(val).lower() == "nan"):
        return ""
    s = str(val).strip()
    if not s:
        return ""
    # If Excel stored it as number, it may be 1108000; zero-pad to 8 digits (USGS style)
    try:
        n = int(float(s))
        return str(n).zfill(8)
    except (TypeError, ValueError):
        return s


def load_locations(path: str):
    """Load location table from Excel. Uses STAID (text), LAT, LON. Returns list of dicts with lat, lon, id."""
    try:
        import pandas as pd
    except ImportError:
        print("Install pandas and openpyxl: pip install pandas openpyxl", file=sys.stderr)
        sys.exit(1)
    df = pd.read_excel(path, engine="openpyxl")

    col_upper = {str(c).upper().strip(): c for c in df.columns}
    lat_col = col_upper.get("LAT")
    lon_col = col_upper.get("LON")
    staid_col = col_upper.get("STAID")

    if lat_col is None or lon_col is None:
        raise ValueError(f"Could not find LAT and LON columns in {path}. Columns: {list(df.columns)}")
    if staid_col is None:
        raise ValueError(f"Could not find STAID column in {path}. Columns: {list(df.columns)}")

    rows = []
    for i, r in df.iterrows():
        try:
            lat = float(r[lat_col])
            lon = float(r[lon_col])
        except (TypeError, ValueError):
            continue
        lid = _staid_to_text(r[staid_col])
        if not lid:
            lid = f"loc_{i}"
        rows.append({"lat": lat, "lon": lon, "id": lid})
    return rows


def load_noaa_locations(path: str):
    """Load NOAA station table from CSV. Uses id, lat, lon. Returns list of dicts with lat, lon, id."""
    try:
        import pandas as pd
    except ImportError:
        print("Install pandas: pip install pandas", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(path, encoding="utf-8")
    col_lower = {str(c).lower().strip(): c for c in df.columns}
    lat_col = col_lower.get("lat")
    lon_col = col_lower.get("lon")
    id_col = col_lower.get("id")
    if lat_col is None or lon_col is None:
        raise ValueError(f"Could not find lat and lon columns in {path}. Columns: {list(df.columns)}")
    if id_col is None:
        id_col = col_lower.get("station") or list(df.columns)[0]
    rows = []
    seen_ids = set()
    for i, r in df.iterrows():
        try:
            lat = float(r[lat_col])
            lon = float(r[lon_col])
        except (TypeError, ValueError):
            continue
        lid = str(r[id_col]).strip() if pd.notna(r[id_col]) else ""
        if not lid:
            lid = f"noaa_{i}"
        if lid in seen_ids:
            continue
        seen_ids.add(lid)
        rows.append({"lat": lat, "lon": lon, "id": lid})
    return rows


def list_nc4_dates(input_dir: str):
    """Return sorted list of (date, full_path) for each daily NetCDF in input_dir."""
    # 3B-DAY.MS.MRG.3IMERG.YYYYMMDD-S000000-E235959.V07B.nc4 (global)
    pattern1 = re.compile(r"3B-DAY\.MS\.MRG\.3IMERG\.(\d{8})-S000000-E235959\.V07B\.nc4$")
    # gpm_imerg_region_YYYYMMDD.nc (regional from cloud script)
    pattern2 = re.compile(r"gpm_imerg_region_(\d{8})\.nc$")
    out = []
    for f in os.listdir(input_dir):
        path = os.path.join(input_dir, f)
        if not os.path.isfile(path):
            continue
        ymd = None
        if pattern1.match(f):
            ymd = pattern1.match(f).group(1)
        elif pattern2.match(f):
            ymd = pattern2.match(f).group(1)
        if ymd:
            try:
                d = dt.datetime.strptime(ymd, "%Y%m%d").date()
                out.append((d, path))
            except ValueError:
                pass
    out.sort(key=lambda x: x[0])
    return out


def _is_valid_pr(val) -> bool:
    """Return True if value is a valid precipitation (mm/day). Reject NaN and fill values."""
    if val is None:
        return False
    try:
        f = float(val)
    except (TypeError, ValueError):
        return False
    if f != f:  # NaN
        return False
    if f < 0 or f > 10000:  # IMERG fill often -9999 or very large
        return False
    return True


def _get_pr_from_ds(pr_da, lat_name, lon_name, lat: float, lon_for_grid: float):
    """Extract pr (mm/day) at (lat, lon_for_grid) from open DataArray."""
    val = None
    try:
        interped = pr_da.interp(
            **{lat_name: lat, lon_name: lon_for_grid},
            method="linear",
        ).squeeze()
        v = float(interped.values)
        if _is_valid_pr(v):
            val = v
    except Exception:
        pass
    if val is None:
        try:
            nearest = pr_da.sel(
                **{lat_name: lat, lon_name: lon_for_grid},
                method="nearest",
            ).squeeze()
            v = float(nearest.values)
            if _is_valid_pr(v):
                val = v
        except Exception:
            pass
    return val


def run(
    locations_path: str = DEFAULT_LOCATIONS,
    noaa_csv_path: str = None,
    input_dir: str = DEFAULT_INPUT_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    output_single: str = None,
):
    """Extract pr at each location for each date and write CSVs."""
    if not os.path.isfile(locations_path):
        print(f"Locations file not found: {locations_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(input_dir):
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    locations = load_locations(locations_path)
    if not locations:
        print("No valid (lat, lon) rows in locations file.", file=sys.stderr)
        sys.exit(1)
    print(f"Loaded {len(locations)} USGS locations from {locations_path}")

    # Add NOAA locations if CSV path provided and exists
    if noaa_csv_path and os.path.isfile(noaa_csv_path):
        usgs_ids = {loc["id"] for loc in locations}
        noaa_locs = load_noaa_locations(noaa_csv_path)
        for loc in noaa_locs:
            if loc["id"] not in usgs_ids:
                locations.append(loc)
                usgs_ids.add(loc["id"])
        print(f"Added {len(noaa_locs)} NOAA locations from {noaa_csv_path}")

    files = [(d, p) for d, p in list_nc4_dates(input_dir) if d >= MIN_DATE]
    if not files:
        print(f"No daily NetCDF files on or after {MIN_DATE} found in {input_dir}", file=sys.stderr)
        sys.exit(1)
    print(f"Found {len(files)} daily files")

    os.makedirs(output_dir, exist_ok=True)

    # Build combined rows: open each file once, extract all locations, then close
    try:
        import xarray as xr
    except ImportError:
        print("Install xarray netCDF4: pip install xarray netCDF4", file=sys.stderr)
        sys.exit(1)
    combined = []
    for i, (date, nc_path) in enumerate(files):
        if (i + 1) % 500 == 0 or i == 0:
            print(f"  Processing file {i + 1}/{len(files)} ...", flush=True)
        try:
            ds = xr.open_dataset(nc_path, mask_and_scale=True)
        except Exception as e:
            print(f"  {date}: open failed: {e}", file=sys.stderr)
            for loc in locations:
                combined.append({"date": date, "location_id": loc["id"], "lat": loc["lat"], "lon": loc["lon"], "pr_mm_per_day": None})
            continue
        pvar = next((v for v in PR_VAR_NAMES if v in ds), None)
        lat_name = next((c for c in LAT_NAMES if c in ds.coords or c in ds.dims), None)
        lon_name = next((c for c in LON_NAMES if c in ds.coords or c in ds.dims), None)
        if not pvar or not lat_name or not lon_name:
            ds.close()
            for loc in locations:
                combined.append({"date": date, "location_id": loc["id"], "lat": loc["lat"], "lon": loc["lon"], "pr_mm_per_day": None})
            continue
        lon_vals = ds[lon_name].values
        lon_is_360 = float(lon_vals.min()) >= 0
        pr_da = ds[pvar]
        for loc in locations:
            lat, lon = loc["lat"], loc["lon"]
            lon_sel = lon if not lon_is_360 else (lon if 0 <= lon <= 360 else (lon + 360 if lon < 0 else lon - 360))
            pr = _get_pr_from_ds(pr_da, lat_name, lon_name, lat, lon_sel)
            combined.append({"date": date, "location_id": loc["id"], "lat": loc["lat"], "lon": loc["lon"], "pr_mm_per_day": pr})
        ds.close()

    # Write combined CSV
    try:
        import pandas as pd
    except ImportError:
        import csv
        out_path = output_single or os.path.join(output_dir, "pr_all_locations.csv")
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "location_id", "lat", "lon", "pr_mm_per_day"])
            w.writeheader()
            w.writerows(combined)
    else:
        df = pd.DataFrame(combined)
        out_path = output_single or os.path.join(output_dir, "pr_all_locations.csv")
        df.to_csv(out_path, index=False)
        print(f"Wrote combined CSV: {out_path}")

        if output_single is None:
            # Excel: first column Date (daily, sorted), one column per location
            pivot = df.pivot(index="date", columns="location_id", values="pr_mm_per_day")
            pivot = pivot.sort_index()
            pivot.index.name = "Date"
            excel_path = os.path.join(output_dir, "pr_timeseries.xlsx")
            pivot.to_excel(excel_path)
            print(f"Wrote Excel (Date + locations): {excel_path}")

            # One CSV per location
            for loc in locations:
                loc_id = loc["id"]
                sub = df[df["location_id"] == loc_id][["date", "lat", "lon", "pr_mm_per_day"]]
                safe_id = re.sub(r'[^\w\-]', '_', str(loc_id))[:64]
                per_file = os.path.join(output_dir, f"pr_{safe_id}.csv")
                sub.to_csv(per_file, index=False)
            print(f"Wrote {len(locations)} per-location CSVs in {output_dir}")


def main():
    p = argparse.ArgumentParser(description="Extract GPM IMERG pr at USGS and NOAA locations")
    p.add_argument("--locations", "-l", default=DEFAULT_LOCATIONS, help="USGS Excel path (STAID, LAT, LON)")
    p.add_argument("--noaa-csv", "-n", default=None, help="NOAA CSV path (id, lat, lon). Default: noaa/noaa_stations_in_domain.csv if exists")
    p.add_argument("--input-dir", "-i", default=DEFAULT_INPUT_DIR, help="Directory with daily NetCDF files")
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Directory for output CSVs")
    p.add_argument("--output", "-O", default=None, help="Single output CSV path (no per-location files)")
    args = p.parse_args()
    noaa_path = args.noaa_csv
    if noaa_path is None and os.path.isfile(DEFAULT_NOAA_CSV):
        noaa_path = DEFAULT_NOAA_CSV
    run(
        locations_path=args.locations,
        noaa_csv_path=noaa_path,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        output_single=args.output,
    )


if __name__ == "__main__":
    main()
