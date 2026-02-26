"""
Plot precipitation (GPM IMERG) for USGS discharge stations.
Reads from pr_extracted/pr_<STAID>.csv. Output: docs/images/pr/precipitation_<staid>.png

Uses discharge_data.json or usgs_locations to get USGS station IDs.

Run from project root: python scripts/plot_precipitation_usgs_stations.py
"""
import argparse
import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent
PR_EXTRACTED = PROJECT_ROOT / "pr_extracted"
DISCHARGE_JSON = PROJECT_ROOT / "frontend" / "data" / "discharge_data.json"
sys.path.insert(0, str(_SCRIPT_DIR))
from chart_axis_constants import FIG_SIZE, apply_chart_xaxis


def _staid_8(s):
    """Format station ID as 8-digit string."""
    if s is None or s == "":
        return ""
    try:
        return str(int(float(str(s).strip()))).zfill(8)
    except (TypeError, ValueError):
        return str(s).strip()


def load_usgs_station_ids():
    """Get USGS station IDs from discharge_data.json or pr_extracted filenames."""
    if DISCHARGE_JSON.exists():
        with open(DISCHARGE_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        stations = data.get("stations", [])
        ids = []
        for s in stations:
            sid = s.get("id", "")
            if sid:
                ids.append(_staid_8(sid))
        if ids:
            return list(dict.fromkeys(ids))
    pr_files = list(PR_EXTRACTED.glob("pr_*.csv"))
    ids = []
    for f in pr_files:
        stem = f.stem
        if stem.startswith("pr_") and stem != "pr_all_locations":
            sta = stem[3:]
            if sta.isdigit():
                ids.append(_staid_8(sta))
    return sorted(set(ids))


def plot_one(pr_csv_path, out_path, station_id):
    try:
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    if not os.path.isfile(pr_csv_path):
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
    p = argparse.ArgumentParser(description="Plot precipitation for USGS stations from pr_extracted")
    p.add_argument("-i", "--input-dir", type=Path, default=PR_EXTRACTED)
    p.add_argument("--discharge-json", type=Path, default=DISCHARGE_JSON)
    args = p.parse_args()

    if not args.input_dir.exists():
        print(f"pr_extracted not found: {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    station_ids = load_usgs_station_ids()
    if not station_ids:
        print("No USGS station IDs found (check discharge_data.json or pr_extracted).", file=sys.stderr)
        sys.exit(1)

    out_dirs = [
        PROJECT_ROOT / "docs" / "images" / "pr",
        PROJECT_ROOT / "frontend" / "images" / "pr",
    ]
    ok = 0
    for staid in station_ids:
        pr_path = args.input_dir / f"pr_{staid}.csv"
        if not pr_path.exists():
            continue
        wrote = False
        for out_dir in out_dirs:
            out_path = out_dir / f"precipitation_{staid}.png"
            if plot_one(str(pr_path), str(out_path), staid):
                wrote = True
        if wrote:
            print(f"  {staid}")
            ok += 1
    print(f"Done: {ok} USGS precipitation plots")


if __name__ == "__main__":
    main()
