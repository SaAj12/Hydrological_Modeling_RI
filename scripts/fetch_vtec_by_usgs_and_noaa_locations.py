"""
Query IEM VTEC (NWS Watch/Warning/Advisory) by point for USGS and NOAA locations.
Uses Approximate Location Buffer Radius = 0.01 deg (~1 mile) as on:
https://mesonet.agron.iastate.edu/vtec/search.php (Manual Point Selection).

API: https://mesonet.agron.iastate.edu/json/vtec_events_bypoint.py

Input:
  - USGS locations: usgs_locations.xlsx (STAID, LAT, LON)
  - NOAA locations: noaa/noaa_stations_in_domain.csv (id, lat, lon)

Output: docs/vtec_by_usgs_and_noaa/
  - vtec_events_all_locations.csv (combined)
  - vtec_events_<STAID>.csv per USGS station
  - vtec_events_<id>.csv per NOAA station

Run from project root: python scripts/fetch_vtec_by_usgs_and_noaa_locations.py
Dependencies: pip install pandas openpyxl
"""
import argparse
import io
import os
import sys
import urllib.parse
import urllib.request

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)

DEFAULT_USGS_LOCATIONS = os.path.join(PROJECT_ROOT, "usgs_locations.xlsx")
DEFAULT_NOAA_CSV = os.path.join(PROJECT_ROOT, "noaa", "noaa_stations_in_domain.csv")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "docs", "vtec_by_usgs_and_noaa")
VTEC_API = "https://mesonet.agron.iastate.edu/json/vtec_events_bypoint.py"
DEFAULT_SDATE = "1986-01-01"
DEFAULT_EDATE = "2025-12-31"
BUFFER_DEG = 0.01  # ~1 mile


def _staid_to_text(val) -> str:
    """Format STAID as text (e.g. 01108000 not 1108000)."""
    if val is None or val == "" or (isinstance(val, float) and str(val).lower() == "nan"):
        return ""
    s = str(val).strip()
    if not s:
        return ""
    try:
        n = int(float(s))
        return str(n).zfill(8)
    except (TypeError, ValueError):
        return s


def load_usgs_locations(path: str):
    """Load STAID, LAT, LON from Excel. Returns list of dicts with id, lat, lon."""
    try:
        import pandas as pd
        import openpyxl  # noqa: F401
    except ImportError:
        print("Install: pip install pandas openpyxl", file=sys.stderr)
        sys.exit(1)
    df = pd.read_excel(path, engine="openpyxl")
    col_upper = {str(c).upper().strip(): c for c in df.columns}
    lat_col = col_upper.get("LAT")
    lon_col = col_upper.get("LON")
    staid_col = col_upper.get("STAID")
    if not lat_col or not lon_col or not staid_col:
        raise ValueError(f"Need columns STAID, LAT, LON in {path}. Found: {list(df.columns)}")
    rows = []
    for i, r in df.iterrows():
        try:
            lat = float(r[lat_col])
            lon = float(r[lon_col])
        except (TypeError, ValueError):
            continue
        lid = _staid_to_text(r[staid_col]) or f"loc_{i}"
        rows.append({"id": lid, "lat": lat, "lon": lon})
    return rows


def load_noaa_locations(path: str):
    """Load id, lat, lon from NOAA CSV. Returns list of dicts with id, lat, lon."""
    try:
        import pandas as pd
    except ImportError:
        print("Install: pip install pandas", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(path, encoding="utf-8")
    col_lower = {str(c).lower().strip(): c for c in df.columns}
    lat_col = col_lower.get("lat")
    lon_col = col_lower.get("lon")
    id_col = col_lower.get("id") or col_lower.get("station") or (list(df.columns)[0] if len(df.columns) else None)
    if not lat_col or not lon_col or not id_col:
        raise ValueError(f"Need columns id, lat, lon in {path}. Found: {list(df.columns)}")
    rows = []
    seen = set()
    for i, r in df.iterrows():
        try:
            lat = float(r[lat_col])
            lon = float(r[lon_col])
        except (TypeError, ValueError):
            continue
        lid = str(r[id_col]).strip() if pd.notna(r[id_col]) else ""
        if not lid or lid in seen:
            continue
        seen.add(lid)
        rows.append({"id": lid, "lat": lat, "lon": lon})
    return rows


def fetch_vtec_csv(lat: float, lon: float, buffer: float, sdate: str, edate: str):
    """GET VTEC events by point; return CSV text or None on error."""
    params = {
        "lat": lat,
        "lon": lon,
        "buffer": buffer,
        "sdate": sdate,
        "edate": edate,
        "fmt": "csv",
    }
    url = VTEC_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "VTEC-Fetch/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def run(
    usgs_locations_path: str = DEFAULT_USGS_LOCATIONS,
    noaa_csv_path: str = None,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    sdate: str = DEFAULT_SDATE,
    edate: str = DEFAULT_EDATE,
    buffer_deg: float = BUFFER_DEG,
):
    """Query VTEC by point for each USGS and NOAA location (buffer 0.01 deg) and save CSVs."""
    try:
        import pandas as pd
    except ImportError:
        print("Install: pip install pandas openpyxl", file=sys.stderr)
        sys.exit(1)

    locations = []
    if os.path.isfile(usgs_locations_path):
        usgs = load_usgs_locations(usgs_locations_path)
        locations.extend(usgs)
        print(f"Loaded {len(usgs)} USGS locations from {usgs_locations_path}")
    else:
        print(f"USGS locations not found: {usgs_locations_path}", file=sys.stderr)

    if noaa_csv_path and os.path.isfile(noaa_csv_path):
        usgs_ids = {loc["id"] for loc in locations}
        noaa = load_noaa_locations(noaa_csv_path)
        for loc in noaa:
            if loc["id"] not in usgs_ids:
                locations.append(loc)
                usgs_ids.add(loc["id"])
        print(f"Added {len(noaa)} NOAA locations from {noaa_csv_path}")
    elif noaa_csv_path:
        print(f"NOAA CSV not found: {noaa_csv_path}", file=sys.stderr)

    if not locations:
        print("No locations to fetch.", file=sys.stderr)
        sys.exit(1)

    print(f"VTEC API: buffer={buffer_deg} deg (~1 mile), sdate={sdate}, edate={edate}")
    os.makedirs(output_dir, exist_ok=True)

    all_dfs = []
    for loc in locations:
        staid = loc["id"]
        lat, lon = loc["lat"], loc["lon"]
        print(f"  Fetching {staid} ({lat:.4f}, {lon:.4f}) ...", end=" ", flush=True)
        csv_text = fetch_vtec_csv(lat, lon, buffer_deg, sdate, edate)
        if not csv_text or not csv_text.strip():
            print("no data or error")
            continue
        try:
            df = pd.read_csv(io.StringIO(csv_text))
            out = df[[]].copy()
            for c in ["phenomena", "significance", "issued", "expired"]:
                if c in df.columns:
                    out[c] = df[c]
            if "name" in df.columns:
                out["warning_name"] = df["name"]
            elif "ph_name" in df.columns and "sig_name" in df.columns:
                out["warning_name"] = (df["ph_name"].astype(str) + " " + df["sig_name"].astype(str)).str.strip()
            else:
                out["warning_name"] = out["phenomena"].astype(str) + "." + out["significance"].astype(str)
            out.insert(0, "STAID", staid)
            order = [c for c in ["STAID", "phenomena", "significance", "warning_name", "issued", "expired"] if c in out.columns]
            out = out[order]
            all_dfs.append(out)
            print(f"{len(out)} events")
        except Exception as e:
            print(f"parse error: {e}")

    if not all_dfs:
        print("No VTEC data retrieved for any location.")
        return

    combined = pd.concat(all_dfs, ignore_index=True)
    csv_path = os.path.join(output_dir, "vtec_events_all_locations.csv")
    combined.to_csv(csv_path, index=False)
    print(f"Wrote combined CSV: {csv_path}")

    n_wrote = 0
    for loc in locations:
        staid = loc["id"]
        sub = combined[combined["STAID"] == staid]
        if sub.empty:
            continue
        safe_id = str(staid).replace("/", "_").replace("\\", "_")[:64]
        per_path = os.path.join(output_dir, f"vtec_events_{safe_id}.csv")
        sub.to_csv(per_path, index=False)
        n_wrote += 1
    print(f"Wrote {n_wrote} per-station CSVs in {output_dir}")


def main():
    p = argparse.ArgumentParser(
        description="Fetch IEM VTEC by point for USGS and NOAA locations (buffer 0.01 deg)"
    )
    p.add_argument("--locations", "-l", default=DEFAULT_USGS_LOCATIONS, help="USGS Excel with STAID, LAT, LON")
    p.add_argument("--noaa-csv", "-n", default=None, help="NOAA CSV with id, lat, lon. Default: noaa/noaa_stations_in_domain.csv if exists")
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    p.add_argument("--sdate", default=DEFAULT_SDATE, help="Start date (YYYY-MM-DD)")
    p.add_argument("--edate", default=DEFAULT_EDATE, help="End date (YYYY-MM-DD)")
    p.add_argument("--buffer", type=float, default=BUFFER_DEG, help="Buffer in decimal degrees (default 0.01)")
    args = p.parse_args()

    noaa_path = args.noaa_csv
    if noaa_path is None and os.path.isfile(DEFAULT_NOAA_CSV):
        noaa_path = DEFAULT_NOAA_CSV

    run(
        usgs_locations_path=args.locations,
        noaa_csv_path=noaa_path,
        output_dir=args.output_dir,
        sdate=args.sdate,
        edate=args.edate,
        buffer_deg=args.buffer,
    )


if __name__ == "__main__":
    main()
