"""
Download water level and predictions from NOAA CO-OPS API for all NOAA stations.
Output: noaa/{station}_water_level.csv, noaa/{station}_predictions.csv

API: https://api.tidesandcurrents.noaa.gov/api/prod/
- water_level: 6-min, 1 month per request; datum required
- predictions: 6-min, 1 year per request

Run from project root: python scripts/download_noaa_water_level.py
Dependencies: pip install requests
If no data: run with --test to check API; 403 may indicate network blocking.
"""
import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)

DEFAULT_NOAA_CSV = os.path.join(PROJECT_ROOT, "noaa", "noaa_stations_in_domain.csv")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "noaa")
BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
APP_PARAM = "application=SWAT_Viewer_Brown"
USER_AGENT = "SWAT-Viewer/1.0 (Brown University Hydrological Modeling)"
START_DATE = date(2010, 1, 1)
END_DATE = date(2025, 12, 31)


def load_station_ids(csv_path):
    """Return list of station IDs from noaa_stations_in_domain.csv."""
    try:
        import pandas as pd
    except ImportError:
        print("Install: pip install pandas", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(csv_path):
        return []
    df = pd.read_csv(csv_path, encoding="utf-8")
    col_lower = {str(c).lower().strip(): c for c in df.columns}
    id_col = col_lower.get("id") or list(df.columns)[0]
    ids = []
    for v in df[id_col].dropna().unique():
        s = str(v).strip()
        if s and s.isdigit():
            ids.append(s)
    return ids


def fetch_url(url, max_retries=3):
    """Fetch URL; return response text or None. Uses User-Agent and application param."""
    try:
        import requests
    except ImportError:
        print("Install: pip install requests", file=sys.stderr)
        sys.exit(1)
    sep = "&" if "?" in url else "?"
    full_url = url + sep + APP_PARAM if APP_PARAM not in url else url
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(max_retries):
        try:
            r = requests.get(full_url, headers=headers, timeout=90)
            if r.status_code == 403:
                if attempt == 0:
                    print("\n  [403 Forbidden] NOAA API may block automated requests. Try: --test, different network, or browser.", file=sys.stderr)
                return None
            if r.status_code >= 400:
                return None
            return r.text
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None
    return None


def _month_chunks(begin, end):
    """Yield (begin_date, end_date) for each month."""
    current = begin
    while current <= end:
        month_end = (current.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        chunk_end = min(month_end, end)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def _year_chunks(begin, end):
    """Yield (begin_date, end_date) for each year (predictions allow 1 year per request)."""
    current = begin
    while current <= end:
        year_end = date(current.year, 12, 31)
        chunk_end = min(year_end, end)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def _fetch_and_parse(url, product_type):
    """Fetch URL and return (header, rows) or (None, [])."""
    text = fetch_url(url)
    if not text or "Date Time" not in text:
        return None, []
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return None, []
    header = lines[0]
    rows = [ln for ln in lines[1:] if ln.strip()]
    if product_type == "water_level":
        header = header.replace("O or R (F=forecasted)", "Quality")
    return header, rows


def download_water_level(station, out_dir, begin, end, workers=6):
    """Download water level (6-min) in monthly chunks, parallelized."""
    out_path = os.path.join(out_dir, f"{station}_water_level.csv")
    urls = []
    for b, e in _month_chunks(begin, end):
        urls.append((b, e, f"{BASE_URL}?station={station}&product=water_level&datum=MLLW&units=metric&time_zone=gmt&format=csv&begin_date={b:%Y%m%d}&end_date={e:%Y%m%d}&{APP_PARAM}"))
    all_rows = []
    header = None
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_fetch_and_parse, url, "water_level") for _, _, url in urls]
        for fut in as_completed(futures):
            h, rows = fut.result()
            if h and rows:
                if header is None:
                    header = h
                all_rows.extend(rows)
            time.sleep(0.05)
    if not all_rows:
        return False
    if header is None:
        header = "Date Time,Water Level,Sigma,Quality"
    all_rows.sort()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        f.write("\n".join(all_rows))
    return True


def download_predictions(station, out_dir, begin, end, workers=6):
    """Download predictions (6-min) in yearly chunks, parallelized. API allows 1 year per request."""
    out_path = os.path.join(out_dir, f"{station}_predictions.csv")
    urls = []
    for b, e in _year_chunks(begin, end):
        urls.append((b, e, f"{BASE_URL}?station={station}&product=predictions&datum=MLLW&units=metric&time_zone=gmt&format=csv&interval=6&begin_date={b:%Y%m%d}&end_date={e:%Y%m%d}&{APP_PARAM}"))
    all_rows = []
    header = None
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_fetch_and_parse, url, "predictions") for _, _, url in urls]
        for fut in as_completed(futures):
            h, rows = fut.result()
            if h and rows:
                if header is None:
                    header = h
                all_rows.extend(rows)
            time.sleep(0.05)
    if not all_rows:
        return False
    if header is None:
        header = "Date Time,Prediction"
    all_rows.sort()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        f.write("\n".join(all_rows))
    return True


def run(noaa_csv, output_dir, begin, end, stations_only=None, workers=6):
    stations = load_station_ids(noaa_csv)
    if not stations:
        print("No station IDs found.", file=sys.stderr)
        sys.exit(1)
    if stations_only:
        stations = [s for s in stations if s in stations_only]
    os.makedirs(output_dir, exist_ok=True)
    print(f"Downloading water level and predictions for {len(stations)} stations ({begin} to {end})")

    for i, station in enumerate(stations):
        print(f"  [{i+1}/{len(stations)}] {station} ...", end=" ", flush=True)
        wl_ok = download_water_level(station, output_dir, begin, end, workers)
        pred_ok = download_predictions(station, output_dir, begin, end, workers)
        if wl_ok:
            print(f"water_level ok", end="")
        else:
            print(f"water_level (no data)", end="")
        if pred_ok:
            print(f", predictions ok")
        else:
            print(f", predictions (no data)")


def main():
    p = argparse.ArgumentParser(description="Download NOAA water level and predictions for all stations")
    p.add_argument("--noaa-csv", "-n", default=DEFAULT_NOAA_CSV, help="NOAA stations CSV")
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    p.add_argument("--begin", "-b", default="2010-01-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end", "-e", default="2025-12-31", help="End date YYYY-MM-DD")
    p.add_argument("--stations", "-s", default=None, help="Comma-separated station IDs (default: all)")
    p.add_argument("--workers", "-w", type=int, default=6, help="Parallel download workers (default: 6)")
    p.add_argument("--test", "-t", action="store_true", help="Test API: fetch one water_level request and print result")
    args = p.parse_args()

    if args.test:
        test_url = f"{BASE_URL}?station=8454000&product=water_level&datum=MLLW&units=metric&time_zone=gmt&format=csv&begin_date=20240101&end_date=20240102&{APP_PARAM}"
        try:
            import requests
            r = requests.get(test_url, headers={"User-Agent": USER_AGENT}, timeout=30)
            print(f"Status: {r.status_code}")
            print(f"Response (first 800 chars):\n{r.text[:800]}")
        except Exception as e:
            print(f"Error: {e}")
        return

    begin = date.fromisoformat(args.begin)
    end = date.fromisoformat(args.end)
    stations_only = set(s.strip() for s in args.stations.split(",")) if args.stations else None

    run(args.noaa_csv, args.output_dir, begin, end, stations_only, args.workers)


if __name__ == "__main__":
    main()
