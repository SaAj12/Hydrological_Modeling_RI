"""
Download water level data (Predictions, Verified, Preliminary) and compute Observed - Predicted
from NOAA CO-OPS API for the 6 stations that have water level data on NOAA website.
Data source: https://tidesandcurrents.noaa.gov/waterlevels.html (uses same CO-OPS API)

Outputs in D:\\Brown\\SWAT\\viewer3\\noaa\\:
  - {station}_water_level.csv     (Verified + Preliminary, Quality column: v=verified, p=preliminary)
  - {station}_predictions.csv     (Tide predictions)
  - {station}_observed_minus_predicted.csv (Observed - Predicted, computed)

Skips any file that already exists. Use --force to re-download.

API: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
- water_level: 6-min observed, 1 month per request
- predictions: 6-min tide predictions, 1 year per request (hilo fallback for subordinate stations)

Run from project root: python scripts/download_noaa_waterlevels_station.py
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
DEFAULT_OUTPUT_DIR = r"D:\Brown\SWAT\viewer3\noaa"
# 6 NOAA stations with water level data: https://tidesandcurrents.noaa.gov/waterlevels.html
WATER_LEVEL_STATIONS = ["8447386", "8447636", "8452660", "8452944", "8454000", "8461490"]
DEFAULT_START = "20100101"
DEFAULT_END = "20251231"


def fetch_chunk(station: str, product: str, begin: str, end: str, datum: str = "MLLW", extra_params: dict = None) -> str:
    params = {
        "station": station,
        "product": product,
        "begin_date": begin,
        "end_date": end,
        "time_zone": "gmt",
        "units": "metric",
        "format": "csv",
        "application": "NOAA-WaterLevels-Download",
    }
    if datum and product in ("water_level", "predictions",):
        params["datum"] = datum
    if extra_params:
        params.update(extra_params)
    url = API_BASE + "?" + urlencode(params)
    try:
        req = Request(url, headers={"User-Agent": "NOAA-WaterLevels/1.0"})
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


def download_product(station: str, output_dir: str, begin_date: str, end_date: str, datum: str,
                     product: str, needs_datum: bool, chunk_m: int, chunk_y: int, extra_params: dict, workers: int,
                     skip_existing: bool = True) -> bool:
    out_path = os.path.join(output_dir, f"{station}_{product}.csv")
    if skip_existing and os.path.isfile(out_path):
        print(f"  {product}: skipped (exists)")
        return True
    if chunk_m and chunk_m >= 1:
        chunks = list(month_chunks(begin_date, end_date, chunk_m))
    elif chunk_y and chunk_y >= 1:
        chunks = list(year_chunks(begin_date, end_date, chunk_y))
    else:
        chunks = [(begin_date, end_date)]

    # Predictions: try interval=6 first; fallback to hilo for subordinate stations
    datum_use = datum
    if product == "predictions" and extra_params.get("interval") == "6":
        test_text = fetch_chunk(station, product, chunks[0][0], chunks[0][1], datum="MLLW", extra_params=extra_params)
        if test_text and ("No Predictions" in test_text or "Datum" in test_text) and "Date Time" not in test_text:
            extra_params = {"interval": "hilo"}
            chunks = list(year_chunks(begin_date, end_date, 10))

    tasks = [(station, product, b, e, datum_use, needs_datum, extra_params) for b, e in chunks]
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for t in tasks:
            b, e, text = _fetch_task(t)
            results[(b, e)] = text

    header = None
    all_rows = []
    for b, e in chunks:
        text = results.get((b, e), "")
        if not text or "error" in text.lower()[:500] or "No data" in text or "No Predictions" in text or "Datum" in text.lower():
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


def compute_observed_minus_predicted(wl_path: str, pred_path: str, out_path: str, skip_existing: bool = True) -> bool:
    """Merge water_level and predictions on timestamp, output Observed - Predicted."""
    if skip_existing and os.path.isfile(out_path):
        print(f"  observed_minus_predicted: skipped (exists)")
        return True
    try:
        import pandas as pd
    except ImportError:
        print("  observed_minus_predicted: requires pandas (pip install pandas)", file=sys.stderr)
        return False
    if not os.path.isfile(wl_path) or not os.path.isfile(pred_path):
        print(f"  observed_minus_predicted: skipped (need water_level and predictions)")
        return False
    wl = pd.read_csv(wl_path)
    pred = pd.read_csv(pred_path)
    if wl.empty or pred.empty or len(wl.columns) < 2 or len(pred.columns) < 2:
        return False
    time_col = "Date Time" if "Date Time" in wl.columns else wl.columns[0]
    val_col = "Water Level" if "Water Level" in wl.columns else wl.columns[1]
    pred_time = pred.columns[0]
    pred_val_col = pred.columns[1]
    wl["_dt"] = pd.to_datetime(wl[time_col], errors="coerce")
    pred["_dt"] = pd.to_datetime(pred[pred_time], errors="coerce")
    wl = wl.dropna(subset=["_dt", val_col])
    pred = pred.dropna(subset=["_dt", pred_val_col])
    if wl.empty or pred.empty:
        return False
    merged = wl[["_dt", val_col]].merge(pred[["_dt", pred_val_col]], on="_dt", how="inner")
    merged["Observed_minus_Predicted"] = merged[val_col] - merged[pred_val_col]
    merged = merged.sort_values("_dt")
    out_df = merged[["_dt", "Observed_minus_Predicted"]].copy()
    out_df["Date Time"] = out_df["_dt"].dt.strftime("%Y-%m-%d %H:%M")
    out_df = out_df[["Date Time", "Observed_minus_Predicted"]]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    out_df.to_csv(out_path, index=False)
    print(f"  observed_minus_predicted: {len(out_df)} rows -> {out_path}")
    return True


def main():
    p = argparse.ArgumentParser(
        description="Download water level (Verified, Preliminary), Predictions, Observed-Predicted for 6 NOAA stations"
    )
    p.add_argument("--stations", "-s", nargs="*", default=None, help="Station IDs (default: 6 water level stations)")
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    p.add_argument("--begin", "-b", default=DEFAULT_START, help="Begin date yyyyMMdd")
    p.add_argument("--end", "-e", default=DEFAULT_END, help="End date yyyyMMdd")
    p.add_argument("--datum", default="MLLW", help="Datum")
    p.add_argument("--workers", "-w", type=int, default=8, help="Parallel workers")
    p.add_argument("--force", "-f", action="store_true", help="Re-download even if file exists")
    args = p.parse_args()

    stations = args.stations if args.stations else WATER_LEVEL_STATIONS
    skip = not args.force

    os.makedirs(args.output_dir, exist_ok=True)
    print(f"Stations: {len(stations)} | {args.begin} to {args.end} | output: {args.output_dir} | skip_existing={skip}")

    for station in stations:
        print(f"Station {station}")
        # 1. water_level (Verified + Preliminary)
        download_product(
            station, args.output_dir, args.begin, args.end,
            args.datum, "water_level", True, 1, None, {}, args.workers, skip_existing=skip,
        )
        # 2. predictions
        download_product(
            station, args.output_dir, args.begin, args.end,
            args.datum, "predictions", True, None, 1, {"interval": "6"}, args.workers, skip_existing=skip,
        )
        # 3. Observed - Predicted (computed)
        wl_path = os.path.join(args.output_dir, f"{station}_water_level.csv")
        pred_path = os.path.join(args.output_dir, f"{station}_predictions.csv")
        out_path = os.path.join(args.output_dir, f"{station}_observed_minus_predicted.csv")
        compute_observed_minus_predicted(wl_path, pred_path, out_path, skip_existing=skip)

    print("Done.")


if __name__ == "__main__":
    main()
