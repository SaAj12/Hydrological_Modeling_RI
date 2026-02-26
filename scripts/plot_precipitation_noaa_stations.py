"""
Plot precipitation (GPM IMERG) for each NOAA station.
Uses nearest USGS pr data from pr_extracted (pr_<STAID>.csv). NOAA stations mapped by lat/lon.
X-axis: 1 Jan 2010 – 31 Dec 2025, year labels every 2 years.
Output: docs/images/noaa/precipitation_<noaa_id>.png
"""
import argparse
import csv
import math
import os
import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent
NOAA_CSV = PROJECT_ROOT / "noaa" / "noaa_stations_in_domain.csv"
PR_EXTRACTED = PROJECT_ROOT / "pr_extracted"
sys.path.insert(0, str(_SCRIPT_DIR))
from chart_axis_constants import FIG_SIZE, apply_chart_xaxis


def load_noaa_stations(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                lat = float(row.get("lat", 0))
                lon = float(row.get("lon", 0))
                lid = str(row.get("id", "")).strip()
                if lid:
                    rows.append({"id": lid, "lat": lat, "lon": lon})
            except (TypeError, ValueError):
                continue
    return rows


def load_pr_locations(pr_all_path):
    """Return list of (location_id, lat, lon) from pr_all_locations.csv."""
    seen = set()
    out = []
    with open(pr_all_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lid = str(row.get("location_id", "")).strip()
            if not lid or lid in seen:
                continue
            seen.add(lid)
            try:
                lat = float(row.get("lat", 0))
                lon = float(row.get("lon", 0))
                out.append((lid, lat, lon))
            except (TypeError, ValueError):
                continue
    return out


def dist_deg(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def nearest_usgs(noaa_lat, noaa_lon, pr_locs):
    best_id, best_d = None, float("inf")
    for lid, lat, lon in pr_locs:
        d = dist_deg(noaa_lat, noaa_lon, lat, lon)
        if d < best_d:
            best_d, best_id = d, lid
    return best_id


def plot_one(pr_csv_path, out_path, station_id):
    try:
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        return False

    df = pd.read_csv(pr_csv_path)
    if df.empty or "date" not in df.columns:
        return False
    pr_col = "pr_mm_per_day" if "pr_mm_per_day" in df.columns else df.columns[-1]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    if df.empty:
        return False

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(df["date"], df[pr_col], color="steelblue", linewidth=0.5, alpha=0.9)
    ax.fill_between(df["date"], df[pr_col], alpha=0.3, color="steelblue")
    ax.set_xlabel("")
    ax.set_ylabel("mm/day")
    ax.set_title(f"Precipitation (GPM IMERG) — Station {station_id}", fontsize=12)
    apply_chart_xaxis(ax, set_limits=True)
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=0)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.94, bottom=0.1)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.02)
    plt.close()
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input-dir", type=Path, default=PR_EXTRACTED)
    p.add_argument("--noaa-csv", type=Path, default=NOAA_CSV)
    args = p.parse_args()

    pr_all = args.input_dir / "pr_all_locations.csv"
    if not pr_all.exists():
        print(f"pr_all_locations.csv not found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)
    if not args.noaa_csv.exists():
        print(f"NOAA stations not found: {args.noaa_csv}", file=sys.stderr)
        sys.exit(1)

    noaa_stations = load_noaa_stations(args.noaa_csv)
    pr_locs = load_pr_locations(pr_all)
    if not pr_locs:
        print("No USGS pr locations.", file=sys.stderr)
        sys.exit(1)

    out_dirs = [
        PROJECT_ROOT / "docs" / "images" / "noaa",
        PROJECT_ROOT / "frontend" / "images" / "noaa",
    ]
    ok = 0
    for s in noaa_stations:
        usgs_id = nearest_usgs(s["lat"], s["lon"], pr_locs)
        pr_path = args.input_dir / f"pr_{usgs_id}.csv"
        if not pr_path.exists():
            print(f"  {s['id']}: no pr data (nearest {usgs_id})", file=sys.stderr)
            continue
        wrote = False
        for out_dir in out_dirs:
            out_path = out_dir / f"precipitation_{s['id']}.png"
            if plot_one(str(pr_path), str(out_path), s["id"]):
                wrote = True
        if wrote:
            print(f"  {s['id']} <- pr_{usgs_id}.csv")
            ok += 1
    print(f"Done: {ok} precipitation plots")


if __name__ == "__main__":
    main()
