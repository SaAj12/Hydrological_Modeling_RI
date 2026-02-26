"""
Download daily water level and predictions from NOAA CO-OPS API for all stations in domain.
- high_low: verified high/low tide times and levels (1 year per request)
- predictions: predicted high/low tides, interval=hilo (10 years per request)

Skips stations/products whose output file already exists.
Output: D:\\Brown\\SWAT\\viewer3\\noaa\\{station}_high_low.csv, {station}_predictions_daily.csv

API: https://api.tidesandcurrents.noaa.gov/api/prod/

Run from project root: python scripts/download_noaa_daily_water_level.py
"""
import argparse
import csv
import io
import os
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

# (product, needs_datum, chunk_years, extra_params)
# high_low: 1 year/request; predictions hilo: 10 years/request
PRODUCTS = [
    ("high_low", True, 1, None),
    ("predictions", True, 10, {"interval": "hilo"}),
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


def fetch_chunk(station: str, product: str, begin: str, end: str, datum: str = "MLLW", extra_params: dict = None) -> str:
    params = {
        "station": station,
        "product": product,
        "begin_date": begin,
        "end_date": end,
        "time_zone": "gmt",
        "units": "metric",
        "format": "csv",
        "application": "noaa_station_download",
    }
    if datum and product in ("high_low", "predictions",):
        params["datum"] = datum
    if extra_params:
        params.update(extra_params)
    url = API_BASE + "?" + urlencode(params)
    try:
        req = Request(url, headers={"User-Agent": "NOAA-Station-Download/1.0"})
        with urlopen(req, timeout=120) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def year_chunks(b: str, e: str, years: int = 1):
    bd = datetime.strptime(b, "%Y%m%d").date()
    ed = datetime.strptime(e, "%Y%m%d").date()
    while bd <= ed:
        end_chunk = min(bd + timedelta(days=365 * years), ed)
        yield bd.strftime("%Y%m%d"), end_chunk.strftime("%Y%m%d")
        bd = end_chunk + timedelta(days=1)


def _fetch_task(args):
    station, product, b, e, datum, needs_datum, extra_params = args
    text = fetch_chunk(station, product, b, e, datum=datum if needs_datum else None, extra_params=extra_params)
    time.sleep(0.05)
    return (b, e, text)


def run_one_station(
    station: str,
    output_dir: str,
    begin_date: str,
    end_date: str,
    datum: str,
    skip_existing: bool,
    workers: int,
):
    for prod in PRODUCTS:
        product = prod[0]
        needs_datum = prod[1]
        chunk_years = prod[2]
        extra_params = prod[3] or {}
        out_name = f"{station}_predictions_daily.csv" if product == "predictions" else f"{station}_{product}.csv"
        out_path = os.path.join(output_dir, out_name)

        if skip_existing and os.path.isfile(out_path):
            print(f"  {product}: skipped (exists)")
            continue

        chunks = list(year_chunks(begin_date, end_date, chunk_years))
        tasks = [(station, product, b, e, datum, needs_datum, extra_params) for b, e in chunks]

        results = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_fetch_task, t): t for t in tasks}
            for fut in as_completed(futures):
                b, e, text = fut.result()
                results[(b, e)] = text

        header = None
        all_rows = []
        for b, e in chunks:
            text = results.get((b, e), "")
            if not text or "error" in text.lower()[:500] or "No data" in text:
                continue
            if "No Predictions" in text or "Datum" in text.lower():
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
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(header)
                w.writerows(all_rows)
            print(f"  {product}: {len(all_rows)} rows -> {out_path}")
        else:
            print(f"  {product}: no data (skipped)")


def main():
    p = argparse.ArgumentParser(description="Download daily water level (high_low) and predictions for all domain stations")
    p.add_argument("--stations-csv", default=DEFAULT_STATIONS_CSV, help="Path to noaa_stations_in_domain.csv")
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    p.add_argument("--begin", "-b", default=DEFAULT_START, help="Begin date yyyyMMdd")
    p.add_argument("--end", "-e", default=None, help="End date yyyyMMdd (default: today)")
    p.add_argument("--datum", default="MLLW", help="Datum for water level products")
    p.add_argument("--workers", "-w", type=int, default=8, help="Parallel workers")
    p.add_argument("--force", "-f", action="store_true", help="Re-download even if file exists")
    args = p.parse_args()

    stations = load_station_ids(args.stations_csv)
    if not stations:
        print("No station IDs found. Check", args.stations_csv)
        return

    if args.end is None:
        args.end = datetime.utcnow().strftime("%Y%m%d")

    os.makedirs(args.output_dir, exist_ok=True)
    print(f"Daily data | Stations: {len(stations)} | {args.begin} to {args.end} | skip_existing={not args.force}")
    for station in stations:
        print(f"Station {station}")
        run_one_station(
            station, args.output_dir, args.begin, args.end,
            args.datum, skip_existing=not args.force, workers=args.workers,
        )
    print("Done. Output in", args.output_dir)


if __name__ == "__main__":
    main()
