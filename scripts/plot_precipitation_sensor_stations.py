"""
Plot precipitation (GPM IMERG) for sensor stations.
Maps each sensor to nearest precipitation location from pr_extracted/pr_all_locations.csv,
then writes static PNGs for GitHub Pages.

Output:
  - docs/images/sensors/precipitation_sensor_<first_3_words>_<index>.png
  - frontend/images/sensors/precipitation_sensor_<first_3_words>_<index>.png
"""
import argparse
import csv
import json
import math
import os
import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent
SENSORS_JSON = PROJECT_ROOT / "frontend" / "data" / "sensors_data.json"
PR_EXTRACTED = PROJECT_ROOT / "pr_extracted"
sys.path.insert(0, str(_SCRIPT_DIR))
from chart_axis_constants import FIG_SIZE, apply_chart_xaxis


def load_sensors(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for i, s in enumerate(data.get("sensors", [])):
        try:
            lat = float(s.get("lat"))
            lon = float(s.get("lon"))
        except (TypeError, ValueError):
            continue
        out.append({
            "index": i,
            "name": str(s.get("name", "")).strip() or f"Sensor {i + 1}",
            "lat": lat,
            "lon": lon,
        })
    return out


def load_pr_locations(pr_all_path):
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


def sensor_slug_first3(name):
    """Return lowercase slug from the first 3 cleaned alphanumeric words."""
    if name is None:
        name = ""
    parts = str(name).strip().split()
    cleaned = []
    for part in parts:
        tok = re.sub(r"[^A-Za-z0-9]+", "", part).strip()
        if tok:
            cleaned.append(tok.lower())
        if len(cleaned) >= 3:
            break
    if not cleaned:
        return "sensor"
    return "_".join(cleaned)

def dist_deg(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def nearest_location(lat, lon, pr_locs):
    best_id, best_d = None, float("inf")
    for lid, la, lo in pr_locs:
        d = dist_deg(lat, lon, la, lo)
        if d < best_d:
            best_d, best_id = d, lid
    return best_id


def plot_one(pr_csv_path, out_path, sensor_name):
    try:
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
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
    ax.set_title(f"Precipitation (GPM IMERG) — {sensor_name}", fontsize=12)
    apply_chart_xaxis(ax, set_limits=True)
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=0)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.94, bottom=0.1)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.02)
    plt.close()
    return True


def main():
    p = argparse.ArgumentParser(description="Plot precipitation for sensor stations")
    p.add_argument("-i", "--input-dir", type=Path, default=PR_EXTRACTED)
    p.add_argument("--sensors-json", type=Path, default=SENSORS_JSON)
    args = p.parse_args()

    pr_all = args.input_dir / "pr_all_locations.csv"
    if not pr_all.exists():
        print(f"pr_all_locations.csv not found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)
    if not args.sensors_json.exists():
        print(f"Sensors JSON not found: {args.sensors_json}", file=sys.stderr)
        sys.exit(1)

    sensors = load_sensors(args.sensors_json)
    pr_locs = load_pr_locations(pr_all)
    if not sensors:
        print("No sensor locations found.", file=sys.stderr)
        sys.exit(1)
    if not pr_locs:
        print("No precipitation locations found.", file=sys.stderr)
        sys.exit(1)

    out_dirs = [
        PROJECT_ROOT / "docs" / "images" / "sensors",
        PROJECT_ROOT / "frontend" / "images" / "sensors",
    ]

    ok = 0
    for s in sensors:
        slug = sensor_slug_first3(s.get("name", ""))
        nearest_id = nearest_location(s["lat"], s["lon"], pr_locs)
        pr_path = args.input_dir / f"pr_{nearest_id}.csv"
        if not pr_path.exists():
            print(f"  sensor_{s['index']}: no pr data (nearest {nearest_id})", file=sys.stderr)
            continue
        wrote = False
        for out_dir in out_dirs:
            out_path = out_dir / f"precipitation_sensor_{slug}_{s['index']}.png"
            if plot_one(str(pr_path), str(out_path), s["name"]):
                wrote = True
        if wrote:
            print(f"  sensor_{s['index']} <- pr_{nearest_id}.csv")
            ok += 1

    # Remove old filenames from previous runs (precipitation_sensor_<index>.png)
    old_re = re.compile(r"^precipitation_sensor_\d+\.png$")
    for out_dir in out_dirs:
        if not out_dir.exists():
            continue
        for fn in out_dir.iterdir():
            if fn.is_file() and old_re.match(fn.name):
                try:
                    fn.unlink()
                except OSError:
                    pass

    print(f"Done: {ok} sensor precipitation plots")


if __name__ == "__main__":
    main()

