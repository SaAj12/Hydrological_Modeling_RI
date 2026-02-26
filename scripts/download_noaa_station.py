"""
Download all available data for NOAA Tides & Currents stations into a local folder.
Uses CO-OPS Data API: https://api.tidesandcurrents.noaa.gov/api/prod/

By default downloads data for all 14 stations in domain (RI/MA/CT).
Downloads daily data only: high_low (tides), daily_max_min, daily_mean (Great Lakes).
Saves one CSV per product per station in output_dir.
Skips products whose output file already exists (use --force to re-download).

Run from project root: python scripts/download_noaa_station.py
"""
import argparse
import csv
import io
import os
import sys
import time
from datetime import date, datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen, Request

API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
DEFAULT_STATIONS = [
    "8444069",   # Castle Island, North of, MA
    "8447386",   # Fall River, MA
    "8447387",   # Borden Flats Light at Fall River, MA
    "8447412",   # Fall River Visibility, MA
    "8447627",   # New Bedford, Barrier Gate, MA
    "8447636",   # New Bedford Harbor, MA
    "8452314",   # Sandy Point Visibility, Prudence Island, RI
    "8452660",   # Newport, RI
    "8452944",   # Conimicut Light, RI
    "8452951",   # Potter Cove, Prudence Island, RI
    "8453662",   # Providence Visibility, RI
    "8454000",   # Providence, RI
    "8454123",   # Port of Davisville, RI
    "8461490",   # New London, CT
]
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
DEFAULT_OUTPUT_DIR = r"D:\Brown\SWAT\viewer3\noaa"
PRODUCTS = [
    ("high_low", True, None, 1),
    ("daily_max_min", True, None, 10),
    ("daily_mean", True, None, 10),
]
DEFAULT_START = "19900101"
REQUEST_DELAY = 0.5


def fetch_chunk(station: str, product: str, begin: str, end: str, datum: str = "MLLW", interval: str = None) -> str:
    """Return CSV text for one chunk, or empty if error/no data."""
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
    if interval and product == "predictions":
        params["interval"] = interval
    url = API_BASE + "?" + urlencode(params)
    try:
        req = Request(url, headers={"User-Agent": "NOAA-Station-Download/1.0"})
        with urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return ""
    if not text or "error" in text.lower()[:500] or "No data" in text:
        return ""
    return text


def run_one_station(
    station: str,
    output_dir: str,
    begin_date: str,
    end_date: str,
    datum: str,
    skip_existing: bool = True,
):
    def month_chunks(b, e, months=1):
        bd = datetime.strptime(b, "%Y%m%d").date()
        ed = datetime.strptime(e, "%Y%m%d").date()
        chunk_days = 31 * max(1, months)
        while bd <= ed:
            end_chunk = min(bd + timedelta(days=chunk_days), ed)
            yield bd.strftime("%Y%m%d"), end_chunk.strftime("%Y%m%d")
            bd = end_chunk + timedelta(days=1)

    def year_chunks(b, e, years=1):
        bd = datetime.strptime(b, "%Y%m%d").date()
        ed = datetime.strptime(e, "%Y%m%d").date()
        while bd <= ed:
            end_chunk = min(bd + timedelta(days=365 * years), ed)
            yield bd.strftime("%Y%m%d"), end_chunk.strftime("%Y%m%d")
            bd = end_chunk + timedelta(days=1)

    for product, needs_datum, chunk_m, chunk_y in PRODUCTS:
        out_path = os.path.join(output_dir, f"{station}_{product}.csv")
        if skip_existing and os.path.isfile(out_path):
            print(f"  {product}: skipped (already exists)")
            continue
        header_written = False
        total_rows = 0
        if chunk_m and chunk_m >= 1:
            chunks = list(month_chunks(begin_date, end_date, chunk_m))
        elif chunk_m and chunk_m < 1:
            bd = datetime.strptime(begin_date, "%Y%m%d").date()
            ed = datetime.strptime(end_date, "%Y%m%d").date()
            chunks = []
            while bd <= ed:
                end_chunk = min(bd + timedelta(days=4), ed)
                chunks.append((bd.strftime("%Y%m%d"), end_chunk.strftime("%Y%m%d")))
                bd = end_chunk + timedelta(days=1)
        elif chunk_y:
            chunks = list(year_chunks(begin_date, end_date, chunk_y))
        else:
            chunks = [(begin_date, end_date)]

        for i, (b, e) in enumerate(chunks):
            time.sleep(REQUEST_DELAY)
            csv_text = fetch_chunk(station, product, b, e, datum=datum if needs_datum else None)
            if not csv_text.strip():
                continue
            reader = csv.reader(io.StringIO(csv_text))
            rows = list(reader)
            if not rows:
                continue
            head = rows[0]
            data_rows = rows[1:] if len(rows) > 1 else []
            if not header_written:
                with open(out_path, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(head)
                    w.writerows(data_rows)
                    total_rows += len(data_rows)
                header_written = True
            else:
                if data_rows:
                    with open(out_path, "a", newline="", encoding="utf-8") as f:
                        csv.writer(f).writerows(data_rows)
                    total_rows += len(data_rows)
        if header_written:
            print(f"  {product}: {total_rows} rows -> {out_path}")
        else:
            print(f"  {product}: no data (skipped)")


def run(
    stations: list = None,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    begin_date: str = DEFAULT_START,
    end_date: str = None,
    datum: str = "MLLW",
    skip_existing: bool = True,
):
    if stations is None:
        stations = DEFAULT_STATIONS
    if end_date is None:
        end_date = datetime.utcnow().strftime("%Y%m%d")
    os.makedirs(output_dir, exist_ok=True)
    for station in stations:
        print(f"Station {station}")
        run_one_station(station, output_dir, begin_date, end_date, datum, skip_existing)


def main():
    p = argparse.ArgumentParser(
        description="Download all NOAA Tides & Currents data for one or more stations (default: Providence + nearby RI/MA)"
    )
    p.add_argument(
        "--stations", "-s", nargs="*", default=None,
        help="Station ID(s), e.g. 8454000 8452660. If omitted, uses all default nearby stations."
    )
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    p.add_argument("--begin", "-b", default=DEFAULT_START, help="Begin date yyyyMMdd")
    p.add_argument("--end", "-e", default=None, help="End date yyyyMMdd (default: today)")
    p.add_argument("--datum", default="MLLW", help="Datum for water level products")
    p.add_argument("--force", "-f", action="store_true", help="Re-download even if file exists")
    args = p.parse_args()
    run(
        stations=DEFAULT_STATIONS if not args.stations else args.stations,
        output_dir=args.output_dir,
        begin_date=args.begin,
        end_date=args.end,
        datum=args.datum,
        skip_existing=not args.force,
    )


if __name__ == "__main__":
    main()
