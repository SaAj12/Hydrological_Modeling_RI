"""
Download water_level and predictions (6-min) from NOAA CO-OPS API for all stations in domain.
Skips stations/products whose output file already exists.
Output: D:\\Brown\\SWAT\\viewer3\\noaa\\{station}_water_level.csv, {station}_predictions.csv

API: https://api.tidesandcurrents.noaa.gov/api/prod/
- water_level: 6-min observed, 1 month per request
- predictions: 6-min tide predictions, 1 year per request

Stations from noaa/noaa_stations_in_domain.csv. Use --force to re-download existing files.

Run from project root: python scripts/download_noaa_water_level_final.py
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

# (product, needs_datum, chunk_months, chunk_years, extra_params) - extra_params overridden by interval_predictions
PRODUCTS = [
    ("water_level", True, 1, None, None),
    ("predictions", True, None, 1, {"interval": "6"}),
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
    if datum and product in ("water_level", "predictions",):
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


def month_chunks(b: str, e: str, months: int = 1):
    bd = datetime.strptime(b, "%Y%m%d").date()
    ed = datetime.strptime(e, "%Y%m%d").date()
    while bd <= ed:
        end_chunk = min(bd + timedelta(days=31 * months), ed)
        yield bd.strftime("%Y%m%d"), end_chunk.strftime("%Y%m%d")
        bd = end_chunk + timedelta(days=1)


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
    datum_predictions: str,
    interval_predictions: str,
    skip_existing: bool,
    workers: int,
):
    for prod in PRODUCTS:
        product = prod[0]
        needs_datum = prod[1]
        chunk_m, chunk_y = prod[2], prod[3]
        extra_params = dict(prod[4] or {}) if len(prod) > 4 else {}
        if product == "predictions" and interval_predictions:
            extra_params["interval"] = interval_predictions
        out_path = os.path.join(output_dir, f"{station}_{product}.csv")

        if skip_existing and os.path.isfile(out_path):
            print(f"  {product}: skipped (exists)")
            continue

        if chunk_m and chunk_m >= 1:
            chunks = list(month_chunks(begin_date, end_date, chunk_m))
        elif chunk_y and chunk_y >= 1:
            years_per_chunk = 10 if extra_params.get("interval") == "hilo" else chunk_y
            chunks = list(year_chunks(begin_date, end_date, years_per_chunk))
        else:
            chunks = [(begin_date, end_date)]

        # Predictions: try interval=6 first; subordinate stations only support interval=hilo
        datum_use = datum_predictions if product == "predictions" else datum
        extra_use = extra_params
        if product == "predictions" and needs_datum and datum_use == "MLLW":
            test_text = fetch_chunk(station, product, chunks[0][0], chunks[0][1],
                                    datum="MLLW", extra_params=extra_params)
            if test_text and ("No Predictions" in test_text or "Datum" in test_text) and "Date Time" not in test_text:
                datum_use = "MSL"

        tasks = [(station, product, b, e, datum_use, needs_datum, extra_use) for b, e in chunks]
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

        used_hilo = False
        # Predictions fallback: subordinate stations only support interval=hilo (high/low), not 6-min
        if product == "predictions" and (not header or not all_rows) and extra_params and extra_params.get("interval") == "6":
            time.sleep(0.2)
            hilo_params = {"interval": "hilo"}
            hilo_chunks = list(year_chunks(begin_date, end_date, 10))  # hilo allows 10 years/request
            hilo_tasks = [(station, product, b, e, "MLLW", needs_datum, hilo_params) for b, e in hilo_chunks]
            hilo_results = {}
            with ThreadPoolExecutor(max_workers=min(workers, 4)) as ex:
                for t in hilo_tasks:
                    hilo_results[(t[2], t[3])] = fetch_chunk(
                        station, product, t[2], t[3], datum="MLLW", extra_params=hilo_params
                    )
                    time.sleep(0.1)
            for b, e in hilo_chunks:
                text = hilo_results.get((b, e), "")
                if not text or "No Predictions" in text or "Datum" in text.lower() or "error" in text.lower()[:500]:
                    continue
                reader = csv.reader(io.StringIO(text))
                rows = list(reader)
                if not rows:
                    continue
                if header is None:
                    header = rows[0]
                all_rows.extend(rows[1:] if len(rows) > 1 else [])
            if header and all_rows:
                used_hilo = True
            all_rows.sort(key=lambda r: r[0] if r else "")
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(header)
                w.writerows(all_rows)
            suffix = " (hilo fallback)" if product == "predictions" and used_hilo else ""
            print(f"  {product}: {len(all_rows)} rows -> {out_path}{suffix}")
        else:
            print(f"  {product}: no data (skipped)")


def main():
    p = argparse.ArgumentParser(description="Download water_level and predictions for all domain stations")
    p.add_argument("--stations-csv", default=DEFAULT_STATIONS_CSV, help="Path to noaa_stations_in_domain.csv")
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    p.add_argument("--begin", "-b", default=DEFAULT_START, help="Begin date yyyyMMdd")
    p.add_argument("--end", "-e", default=None, help="End date yyyyMMdd (default: today)")
    p.add_argument("--datum", default="MLLW", help="Datum for water_level")
    p.add_argument("--datum-predictions", default="MLLW", help="Datum for predictions; use MSL if MLLW fails")
    p.add_argument("--interval-predictions", default="6", choices=["6", "hilo"], help="6=6-min (harmonic only), hilo=high/low (subordinate stations)")
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
    print(f"Stations: {len(stations)} | {args.begin} to {args.end} | skip_existing={not args.force}")
    for station in stations:
        print(f"Station {station}")
        run_one_station(
            station, args.output_dir, args.begin, args.end,
            args.datum, args.datum_predictions, args.interval_predictions,
            skip_existing=not args.force, workers=args.workers,
        )
    print("Done. Output in", args.output_dir)


if __name__ == "__main__":
    main()
