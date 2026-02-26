"""
Download all observations from NOAA Tides & Currents for one station (metric units).
Station page: https://tidesandcurrents.noaa.gov/stationhome.html?id=8444069&name=Castle%20Island,%20North%20of&state=MA

Uses CO-OPS Data API: https://api.tidesandcurrents.noaa.gov/api/prod/

Downloads (all in metric: m, °C, hPa, m/s as applicable):
  - Water Levels: 6-minute water level (datum MLLW) — observed (verified + preliminary)
  - Predictions: 6-minute tide predictions (datum MLLW)
  - Wind, Air Temperature, Water Temperature, Air Pressure (6-minute)

By default station 8444069 (Castle Island, North of, MA). Request limits: 6-min data = 1 month per call.

Run from project root:
  python scripts/download_noaa_one_station.py
  python scripts/download_noaa_one_station.py --station 8454000 --begin 20200101
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
DEFAULT_STATION = "8444069"
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
DEFAULT_OUTPUT_DIR = r"D:\Brown\SWAT\viewer3\noaa"
# (product, needs_datum, chunk_months, chunk_years, extra_params)
# 6-min water_level = 1 month/request; predictions interval=6 = 1 year/request
PRODUCTS = [
    ("water_level", True, 1, None, None),       # Observed 6-min, MLLW
    ("predictions", True, None, 1, {"interval": "6"}),  # Tide predictions 6-min, 1 year/request
    ("air_temperature", False, 1, None, None),
    ("water_temperature", False, 1, None, None),
    ("wind", False, 1, None, None),
    ("air_pressure", False, 1, None, None),
]
DEFAULT_START = "19900101"


def fetch_chunk(station: str, product: str, begin: str, end: str, datum: str = "MLLW", extra_params: dict = None) -> str:
    """Return CSV text for one chunk; always request metric units."""
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
    if datum and product in (
        "water_level", "hourly_height", "high_low", "monthly_mean",
        "one_minute_water_level", "predictions", "ofs_water_level",
        "daily_mean", "daily_max_min",
    ):
        params["datum"] = datum
    if extra_params:
        params.update(extra_params)
    url = API_BASE + "?" + urlencode(params)
    try:
        req = Request(url, headers={"User-Agent": "NOAA-Station-Download/1.0"})
        with urlopen(req, timeout=120) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return ""
    if not text or "error" in text.lower()[:500] or "No data" in text:
        return ""
    return text


def month_chunks(b: str, e: str, months: int = 1):
    """Yield (begin, end) date strings in month-sized chunks."""
    bd = datetime.strptime(b, "%Y%m%d").date()
    ed = datetime.strptime(e, "%Y%m%d").date()
    while bd <= ed:
        end_chunk = min(bd + timedelta(days=31 * months), ed)
        yield bd.strftime("%Y%m%d"), end_chunk.strftime("%Y%m%d")
        bd = end_chunk + timedelta(days=1)


def year_chunks(b: str, e: str, years: int = 1):
    """Yield (begin, end) date strings in year-sized chunks."""
    bd = datetime.strptime(b, "%Y%m%d").date()
    ed = datetime.strptime(e, "%Y%m%d").date()
    while bd <= ed:
        end_chunk = min(bd + timedelta(days=365 * years), ed)
        yield bd.strftime("%Y%m%d"), end_chunk.strftime("%Y%m%d")
        bd = end_chunk + timedelta(days=1)


def _fetch_task(args):
    """Unpack args for ThreadPoolExecutor; returns (begin, end, csv_text)."""
    station, product, b, e, datum, needs_datum, extra_params = args
    csv_text = fetch_chunk(
        station, product, b, e,
        datum=datum if needs_datum else None,
        extra_params=extra_params,
    )
    time.sleep(0.05)  # Small delay to avoid hammering API
    return (b, e, csv_text)


def run_one_station(
    station: str,
    output_dir: str,
    begin_date: str,
    end_date: str,
    datum: str,
    workers: int = 8,
):
    for prod in PRODUCTS:
        product = prod[0]
        needs_datum = prod[1]
        chunk_m = prod[2]
        chunk_y = prod[3]
        extra_params = prod[4] if len(prod) > 4 else None
        out_path = os.path.join(output_dir, f"{station}_{product}.csv")
        if chunk_m and chunk_m >= 1:
            chunks = list(month_chunks(begin_date, end_date, chunk_m))
        elif chunk_y and chunk_y >= 1:
            chunks = list(year_chunks(begin_date, end_date, chunk_y))
        else:
            chunks = [(begin_date, end_date)]

        tasks = [
            (station, product, b, e, datum, needs_datum, extra_params)
            for b, e in chunks
        ]
        results_by_range = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_fetch_task, t): (t[2], t[3]) for t in tasks}
            for fut in as_completed(futures):
                b, e, csv_text = fut.result()
                results_by_range[(b, e)] = csv_text

        header = None
        all_rows = []
        for b, e in chunks:
            csv_text = results_by_range.get((b, e), "")
            if not csv_text.strip():
                continue
            reader = csv.reader(io.StringIO(csv_text))
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
    p = argparse.ArgumentParser(
        description="Download all observations from NOAA Tides & Currents (water level, wind, air/water temp, pressure) in metric units"
    )
    p.add_argument(
        "--station", "-s", default=DEFAULT_STATION,
        help=f"Station ID (default: {DEFAULT_STATION} Castle Island, North of, MA)"
    )
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    p.add_argument("--begin", "-b", default=DEFAULT_START, help="Begin date yyyyMMdd")
    p.add_argument("--end", "-e", default=None, help="End date yyyyMMdd (default: today)")
    p.add_argument("--datum", default="MLLW", help="Datum for water level (default: MLLW)")
    p.add_argument("--workers", "-w", type=int, default=8, help="Parallel download workers (default: 8)")
    args = p.parse_args()

    if args.end is None:
        args.end = datetime.utcnow().strftime("%Y%m%d")

    os.makedirs(args.output_dir, exist_ok=True)
    print(f"Station {args.station} | units=metric | {args.begin} to {args.end}")
    run_one_station(
        args.station,
        args.output_dir,
        args.begin,
        args.end,
        args.datum,
        workers=args.workers,
    )
    print("Done. Output in", args.output_dir)


if __name__ == "__main__":
    main()
