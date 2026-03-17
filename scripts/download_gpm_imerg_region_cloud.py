"""
Download GPM IMERG Final daily precipitation for a regional bounding box.
Uses direct HTTPS + .netrc (same auth as global download) - no earthaccess.
Downloads full file temporarily, subsets by bbox, saves regional .nc, deletes full.
Runs multiple dates in parallel for faster throughput.

Domain: 39.1–44.4°N, 74.2–68.7°W (original bbox + 2° each direction).

Usage (from project root):
  pip install requests xarray netCDF4
  python scripts/download_gpm_imerg_region_cloud.py   # 2010-01-01 through 2025-12-31
  python scripts/download_gpm_imerg_region_cloud.py --begin 2010-01-01 --end 2025-12-31
  python scripts/download_gpm_imerg_region_cloud.py -j 8   # 8 parallel workers

Output: gpm_imerg_region/gpm_imerg_region_YYYYMMDD.nc
"""
import argparse
import datetime as dt
import os
import sys
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)

BASE_URL = "https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/GPM_3IMERGDF.07"
# Domain expanded by 2 deg in all directions from original
NORTH = 44.350747   # was 42.350747 + 2
SOUTH = 39.095955   # was 41.095955 - 2
WEST = -74.245582   # was -72.245582 - 2
EAST = -68.711999   # was -70.711999 + 2
# IMERG daily uses lon -180..180 (not 0-360) and lat -90..90, both ascending

DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "gpm_imerg_region")
DEFAULT_START = dt.date(2010, 1, 1)
DEFAULT_END = dt.date(2025, 12, 31)
CHUNK_SIZE = 2 * 1024 * 1024  # 2 MB chunks for fewer syscalls


def get_earthdata_auth():
    try:
        import netrc
    except ImportError:
        return None, None
    for name in (".netrc", "_netrc"):
        nrc_path = os.path.join(os.path.expanduser("~"), name)
        if os.path.isfile(nrc_path):
            try:
                n = netrc.netrc(nrc_path)
                a = n.authenticators("urs.earthdata.nasa.gov")
                if a:
                    return a[0], a[2]
            except Exception:
                pass
    return None, None


def _process_one_date(
    current: dt.date,
    out_dir: str,
    user: str,
    password: str,
) -> tuple[str, bool, str]:
    """Download, subset, and save one date. Returns (yyyymmdd, success, message)."""
    import tempfile

    import requests
    import xarray as xr

    y, m, d = current.year, current.month, current.day
    yyyymmdd = f"{y}{m:02d}{d:02d}"
    fname = f"3B-DAY.MS.MRG.3IMERG.{yyyymmdd}-S000000-E235959.V07B.nc4"
    url = f"{BASE_URL}/{y}/{m:02d}/{fname}"
    out_path = os.path.join(out_dir, f"gpm_imerg_region_{yyyymmdd}.nc")

    if os.path.isfile(out_path):
        return (yyyymmdd, True, "skip")

    session = requests.Session()
    session.auth = (user, password)
    session.headers["User-Agent"] = "GPM-Region-Download/1.0"
    tmp_path = None
    try:
        r = session.get(url, stream=True, timeout=180)
        r.raise_for_status()
        # Check first chunk for HTML auth/login page (don't consume full body)
        first_chunk = next(r.iter_content(chunk_size=8192), b"")
        if len(first_chunk) < 10000 and b"html" in first_chunk[:2000].lower():
            return (yyyymmdd, False, "auth failed")
        with tempfile.NamedTemporaryFile(suffix=".nc4", delete=False) as tmp:
            tmp.write(first_chunk)
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    tmp.write(chunk)
            tmp_path = tmp.name
        ds = xr.open_dataset(tmp_path, mask_and_scale=True)
        lat_name = next((c for c in ("lat", "latitude") if c in ds.coords or c in ds.dims), None)
        lon_name = next((c for c in ("lon", "longitude") if c in ds.coords or c in ds.dims), None)
        if not lat_name or not lon_name:
            ds.close()
            return (yyyymmdd, False, "no lat/lon")
        # IMERG: lon -180..180, lat -90..90, both ascending
        sub = ds.sel(**{lat_name: slice(SOUTH, NORTH), lon_name: slice(WEST, EAST)})
        sub.load()
        ds.close()
        for v in list(sub.coords) + list(sub.data_vars):
            sub[v].encoding = {}
        if "time" in sub.coords:
            sub["time"].encoding = {"units": "seconds since 1970-01-01T00:00:00Z", "calendar": "gregorian"}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            sub.to_netcdf(out_path)
        sub.close()
        return (yyyymmdd, True, "ok")
    except Exception as e:
        return (yyyymmdd, False, str(e))
    finally:
        if tmp_path and os.path.isfile(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def run(
    begin_date: dt.date = None,
    end_date: dt.date = None,
    out_dir: str = DEFAULT_OUTPUT_DIR,
    jobs: int = 4,
):
    if begin_date is None:
        begin_date = DEFAULT_START
    if end_date is None:
        end_date = DEFAULT_END
    os.makedirs(out_dir, exist_ok=True)
    user, password = get_earthdata_auth()
    if not user or not password:
        print(
            "Earthdata credentials not found. Add to ~/.netrc or ~/_netrc:\n"
            "  machine urs.earthdata.nasa.gov login YOUR_USER password YOUR_PASSWORD\n"
            "Then authorize 'NASA GESDISC DATA ARCHIVE' at:\n"
            "  https://urs.earthdata.nasa.gov/approve_app?client_id=e2WVk8Pw6weeLUKZYOxvTQ",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        import requests
        import xarray as xr  # noqa: F401 - used in worker
    except ImportError:
        print("Install: pip install requests xarray netCDF4", file=sys.stderr)
        sys.exit(1)

    dates = []
    current = begin_date
    while current <= end_date:
        dates.append(current)
        current += dt.timedelta(days=1)

    ok = 0
    fail = 0
    print_lock = threading.Lock()

    def process(d: dt.date):
        return _process_one_date(d, out_dir, user, password)

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = {ex.submit(process, d): d for d in dates}
        for fut in as_completed(futures):
            yyyymmdd, success, msg = fut.result()
            with print_lock:
                if success:
                    ok += 1
                    suffix = f" (exists)" if msg == "skip" else f" -> {os.path.join(out_dir, f'gpm_imerg_region_{yyyymmdd}.nc')}"
                    print(f"{yyyymmdd}{suffix}")
                else:
                    fail += 1
                    print(f"{yyyymmdd}: {msg}")

    print(f"Done: {ok} ok, {fail} failed.")


def main():
    p = argparse.ArgumentParser(description="Download GPM IMERG regional subset (HTTPS + .netrc)")
    p.add_argument("--begin", "-b", default="2010-01-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end", "-e", default="2025-12-31", help="End date YYYY-MM-DD")
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    p.add_argument("--jobs", "-j", type=int, default=4, help="Parallel download workers (default: 4)")
    args = p.parse_args()
    begin = dt.datetime.strptime(args.begin, "%Y-%m-%d").date()
    end = dt.datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else None
    run(begin, end, args.output_dir, jobs=args.jobs)


if __name__ == "__main__":
    main()
