"""
Download available meteorological data from all 14 NOAA stations (1 Jan 2010 – 31 Dec 2025).
Data source: https://tidesandcurrents.noaa.gov/met.html (uses CO-OPS API)

Products: air_temperature, water_temperature, wind, air_pressure, humidity, visibility
Output: D:\\Brown\\SWAT\\viewer3\\noaa\\{station}_{product}.csv

Skips any file that already exists. Use --force to re-download.
Not all stations have all met sensors; empty products are skipped.

API: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
- Meteorological products: 6-min default, 1 month per request; no datum.

Run from project root: python scripts/download_noaa_meteorological_all.py
"""
import argparse
import csv
import io
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen, Request

API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
DEFAULT_STATIONS_CSV = os.path.join(PROJECT_ROOT, "noaa", "noaa_stations_in_domain.csv")
DEFAULT_OUTPUT_DIR = r"D:\Brown\SWAT\viewer3\noaa"
DEFAULT_START = "20100101"
DEFAULT_END = "20251231"

MET_PRODUCTS = [
    "air_temperature",
    "water_temperature",
    "wind",
    "air_pressure",
    "humidity",
    "visibility",
]


def load_station_ids(csv_path: str) -> list:
    """Return list of station IDs from noaa_stations_in_domain.csv."""
    ids = []
    if not os.path.isfile(csv_path):
        return ids
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = row.get("id", list(row.values())[0] if row else "")
            s = str(val).strip()
            if s and s.isdigit():
                ids.append(s)
    return ids


def fetch_chunk(station: str, product: str, begin: str, end: str) -> str:
    params = {
        "station": station,
        "product": product,
        "begin_date": begin,
        "end_date": end,
        "time_zone": "gmt",
        "units": "metric",
        "format": "csv",
        "application": "NOAA-Met-Download",
    }
    url = API_BASE + "?" + urlencode(params)
    try:
        req = Request(url, headers={"User-Agent": "NOAA-Met-Download/1.0"})
        with urlopen(req, timeout=120) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def month_chunks(b: str, e: str, months: int = 1):
    bd = datetime.strptime(b, "%Y%m%d").date()
    ed = datetime.strptime(e, "%Y%m%d").date()
    while bd <= ed:
        end_chunk = min(bd + timedelta(days=31 * months), ed)
        yield bd.strftime("%Y%m%d"), end_chunk.strftime("%Y%m%d")
        bd = end_chunk + timedelta(days=1)


def _fetch_task(args):
    station, product, b, e = args
    text = fetch_chunk(station, product, b, e)
    time.sleep(0.05)
    return (b, e, text)


def download_product(station: str, output_dir: str, begin_date: str, end_date: str,
                     product: str, workers: int, skip_existing: bool) -> bool:
    out_path = os.path.join(output_dir, f"{station}_{product}.csv")
    if skip_existing and os.path.isfile(out_path):
        print(f"  {product}: skipped (exists)")
        return True

    chunks = list(month_chunks(begin_date, end_date, 1))
    tasks = [(station, product, b, e) for b, e in chunks]
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for t in tasks:
            b, e, text = _fetch_task(t)
            results[(b, e)] = text

    header = None
    all_rows = []
    for b, e in chunks:
        text = results.get((b, e), "")
        if not text or "error" in text.lower()[:500] or "No data" in text:
            continue
        if "Date Time" not in text and "date_time" not in text.lower():
            continue
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            continue
        if header is None:
            header = rows[0]
        all_rows.extend(rows[1:] if len(rows) > 1 else [])

    if header and all_rows:
        all_rows.sort(key=lambda r: r[0] if r else "")
        os.makedirs(output_dir, exist_ok=True)
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(all_rows)
        print(f"  {product}: {len(all_rows)} rows -> {out_path}")
        return True
    print(f"  {product}: no data")
    return False


def main():
    p = argparse.ArgumentParser(
        description="Download meteorological data from all 14 NOAA stations (2010–2025)"
    )
    p.add_argument("--stations-csv", default=DEFAULT_STATIONS_CSV, help="Path to noaa_stations_in_domain.csv")
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    p.add_argument("--begin", "-b", default=DEFAULT_START, help="Begin date yyyyMMdd")
    p.add_argument("--end", "-e", default=DEFAULT_END, help="End date yyyyMMdd")
    p.add_argument("--workers", "-w", type=int, default=8, help="Parallel workers")
    p.add_argument("--force", "-f", action="store_true", help="Re-download even if file exists")
    args = p.parse_args()

    stations = load_station_ids(args.stations_csv)
    if not stations:
        print("No station IDs found. Check", args.stations_csv)
        return

    skip = not args.force
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"Meteorological data | {len(stations)} stations | {args.begin} to {args.end} | output: {args.output_dir} | skip_existing={skip}")

    for station in stations:
        print(f"Station {station}")
        for product in MET_PRODUCTS:
            download_product(station, args.output_dir, args.begin, args.end, product, args.workers, skip)

    print("Done.")


if __name__ == "__main__":
    main()
