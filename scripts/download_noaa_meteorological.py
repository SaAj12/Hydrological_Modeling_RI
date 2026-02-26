"""
Download meteorological data from NOAA CO-OPS API for all NOAA stations.
Products: air_temperature, wind, air_pressure, water_temperature, humidity, visibility
Output: noaa/{station}_{product}.csv

API: https://api.tidesandcurrents.noaa.gov/api/prod/
Meteorological products: 6-min default, 1 month per request; no datum.
Not all stations have met sensors; empty responses are skipped.

Run from project root: python scripts/download_noaa_meteorological.py
Dependencies: pip install requests
If no data: run with --test to check API; 403 may indicate network blocking.
"""
import argparse
import os
import sys
import time
from collections import defaultdict
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

# Meteorological products (no datum; 6-min default)
MET_PRODUCTS = [
    "air_temperature",
    "wind",
    "air_pressure",
    "water_temperature",
    "humidity",
    "visibility",
]


def load_station_ids(csv_path):
    """Return list of station IDs from noaa_stations_in_domain.csv."""
    try:
        import pandas as pd
    except ImportError:
        print("Install: pip install pandas", file=sys.stderr)
        sys.exit(1)
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
                    print("\n  [403 Forbidden] NOAA API may block automated requests. Try: --test, different network.", file=sys.stderr)
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


def _fetch_met_chunk(args):
    """Fetch one (station, product, month) chunk. Returns (station, product, header, rows)."""
    station, product, b, e = args
    url = f"{BASE_URL}?station={station}&product={product}&units=metric&time_zone=gmt&format=csv&begin_date={b:%Y%m%d}&end_date={e:%Y%m%d}&{APP_PARAM}"
    text = fetch_url(url)
    if not text or "error" in text.lower() or text.strip().startswith("{"):
        return station, product, None, []
    if "Date Time" not in text and "date_time" not in text.lower():
        return station, product, None, []
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return station, product, None, []
    header = lines[0]
    rows = [ln for ln in lines[1:] if ln.strip()]
    return station, product, header, rows


def run(noaa_csv, output_dir, begin, end, products, stations_only=None, workers=8):
    stations = load_station_ids(noaa_csv)
    if not stations:
        print("No station IDs found.", file=sys.stderr)
        sys.exit(1)
    if stations_only:
        stations = [s for s in stations if s in stations_only]
    os.makedirs(output_dir, exist_ok=True)
    print(f"Downloading meteorological data for {len(stations)} stations ({begin} to {end})")
    print(f"  Products: {', '.join(products)}, workers={workers}")

    # Build all (station, product, month) chunks
    tasks = []
    for station in stations:
        for product in products:
            for b, e in _month_chunks(begin, end):
                tasks.append((station, product, b, e))

    # Fetch in parallel, group results by (station, product)
    data = defaultdict(lambda: {"header": None, "rows": []})
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_fetch_met_chunk, t): t for t in tasks}
        for fut in as_completed(futures):
            station, product, header, rows = fut.result()
            if header and rows:
                key = (station, product)
                if data[key]["header"] is None:
                    data[key]["header"] = header
                data[key]["rows"].extend(rows)
            done += 1
            if done % 100 == 0:
                print(f"  ... {done}/{len(tasks)} requests done", flush=True)
            time.sleep(0.03)

    # Write CSVs
    for i, station in enumerate(stations):
        results = []
        for product in products:
            key = (station, product)
            if key in data and data[key]["rows"]:
                out_path = os.path.join(output_dir, f"{station}_{product}.csv")
                h = data[key]["header"] or "Date Time,Value"
                rows = sorted(data[key]["rows"])
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(h + "\n")
                    f.write("\n".join(rows))
                results.append(f"{product}:ok")
            else:
                results.append(f"{product}:-")
        print(f"  [{i+1}/{len(stations)}] {station}  " + "  ".join(results))


def main():
    p = argparse.ArgumentParser(description="Download NOAA meteorological data for all stations")
    p.add_argument("--noaa-csv", "-n", default=DEFAULT_NOAA_CSV, help="NOAA stations CSV")
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    p.add_argument("--begin", "-b", default="2010-01-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end", "-e", default="2025-12-31", help="End date YYYY-MM-DD")
    p.add_argument("--products", "-p", default=None,
                   help="Comma-separated products (default: all). Options: air_temperature, wind, air_pressure, water_temperature, humidity, visibility")
    p.add_argument("--stations", "-s", default=None, help="Comma-separated station IDs (default: all)")
    p.add_argument("--workers", "-w", type=int, default=8, help="Parallel download workers (default: 8)")
    p.add_argument("--test", "-t", action="store_true", help="Test API: fetch one air_temperature request and print result")
    args = p.parse_args()

    if args.test:
        test_url = f"{BASE_URL}?station=8461490&product=air_temperature&units=metric&time_zone=gmt&format=csv&begin_date=20240101&end_date=20240102&{APP_PARAM}"
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
    products = [x.strip() for x in args.products.split(",")] if args.products else MET_PRODUCTS
    products = [x for x in products if x in MET_PRODUCTS] or MET_PRODUCTS
    stations_only = set(s.strip() for s in args.stations.split(",")) if args.stations else None

    run(args.noaa_csv, args.output_dir, begin, end, products, stations_only, args.workers)


if __name__ == "__main__":
    main()
