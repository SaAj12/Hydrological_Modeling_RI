"""
Download GPM IMERG Final daily precipitation for a regional bounding box.
Uses direct HTTPS + .netrc (same auth as global download) - no earthaccess.
Downloads full file temporarily, subsets by bbox, saves regional .nc, deletes full.

Domain: 39.1–44.4°N, 74.2–68.7°W (original bbox + 2° each direction).

Usage (from project root D:\\go\\pr):
  pip install requests xarray netCDF4
  python scripts/download_gpm_imerg_region_cloud.py   # all data 1998-01-01 through today
  python scripts/download_gpm_imerg_region_cloud.py --begin 1998-01-01 --end 2024-12-31

Output: gpm_imerg_region/gpm_imerg_region_YYYYMMDD.nc
"""
import argparse
import datetime as dt
import os
import sys
import warnings

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
DEFAULT_START = dt.date(1998, 1, 1)
DEFAULT_END = None  # today; all available data from 1998-01-01 through latest


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


def run(begin_date: dt.date, end_date: dt.date = None, out_dir: str = DEFAULT_OUTPUT_DIR):
    import tempfile

    if end_date is None:
        end_date = dt.date.today()
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
        import xarray as xr
    except ImportError:
        print("Install: pip install requests xarray netCDF4", file=sys.stderr)
        sys.exit(1)

    session = requests.Session()
    session.auth = (user, password)
    session.headers["User-Agent"] = "GPM-Region-Download/1.0"

    ok = 0
    fail = 0
    current = begin_date
    while current <= end_date:
        y, m, d = current.year, current.month, current.day
        yyyymmdd = f"{y}{m:02d}{d:02d}"
        fname = f"3B-DAY.MS.MRG.3IMERG.{yyyymmdd}-S000000-E235959.V07B.nc4"
        url = f"{BASE_URL}/{y}/{m:02d}/{fname}"
        out_path = os.path.join(out_dir, f"gpm_imerg_region_{yyyymmdd}.nc")

        if os.path.isfile(out_path):
            print(f"Skip (exists): {yyyymmdd}")
            ok += 1
            current += dt.timedelta(days=1)
            continue

        print(f"  {yyyymmdd} ...", end=" ", flush=True)
        tmp_path = None
        try:
            r = session.get(url, stream=True, timeout=180)
            r.raise_for_status()
            if len(r.content) < 10000 and b"html" in r.content[:2000].lower():
                print("auth failed")
                fail += 1
                current += dt.timedelta(days=1)
                continue
            with tempfile.NamedTemporaryFile(suffix=".nc4", delete=False) as tmp:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        tmp.write(chunk)
                tmp_path = tmp.name
            ds = xr.open_dataset(tmp_path, mask_and_scale=True)
            lat_name = next((c for c in ("lat", "latitude") if c in ds.coords or c in ds.dims), None)
            lon_name = next((c for c in ("lon", "longitude") if c in ds.coords or c in ds.dims), None)
            if not lat_name or not lon_name:
                ds.close()
                print("no lat/lon")
                fail += 1
            else:
                # IMERG: lon -180..180, lat -90..90, both ascending
                sub = ds.sel(**{lat_name: slice(SOUTH, NORTH), lon_name: slice(WEST, EAST)})
                sub.load()
                # Clear encodings to avoid NetCDF "Invalid argument" on lon
                for v in list(sub.coords) + list(sub.data_vars):
                    sub[v].encoding = {}
                if "time" in sub.coords:
                    sub["time"].encoding = {"units": "seconds since 1970-01-01T00:00:00Z", "calendar": "gregorian"}
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    sub.to_netcdf(out_path)
                ds.close()
                sub.close()
                print(f"-> {out_path}")
                ok += 1
        except Exception as e:
            print(str(e))
            fail += 1
        finally:
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        current += dt.timedelta(days=1)

    print(f"Done: {ok} ok, {fail} failed.")


def main():
    p = argparse.ArgumentParser(description="Download GPM IMERG regional subset (HTTPS + .netrc)")
    p.add_argument("--begin", "-b", default="1998-01-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end", "-e", default=None, help="End date YYYY-MM-DD (default: today)")
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    args = p.parse_args()
    begin = dt.datetime.strptime(args.begin, "%Y-%m-%d").date()
    end = dt.datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else None
    run(begin, end, args.output_dir)


if __name__ == "__main__":
    main()
