"""Export precipitation (GPM IMERG) per NOAA station to JSON for Chart.js."""
import csv
import json
import math
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent
NOAA_CSV = PROJECT_ROOT / "noaa" / "noaa_stations_in_domain.csv"
PR_EXTRACTED = PROJECT_ROOT / "pr_extracted"
OUTPUT_FRONTEND = PROJECT_ROOT / "frontend" / "data" / "precipitation_data.json"
OUTPUT_DOCS = PROJECT_ROOT / "docs" / "data" / "precipitation_data.json"


def load_noaa(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({"id": str(r.get("id", "")).strip(), "lat": float(r.get("lat", 0)), "lon": float(r.get("lon", 0))})
            except (TypeError, ValueError):
                pass
    return [x for x in rows if x["id"]]


def load_pr_locations(path):
    out = []
    seen = set()
    with open(path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lid = str(r.get("location_id", "")).strip()
            if not lid or lid in seen:
                continue
            seen.add(lid)
            try:
                out.append((lid, float(r.get("lat", 0)), float(r.get("lon", 0))))
            except (TypeError, ValueError):
                pass
    return out


def dist(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def nearest(noaa_lat, noaa_lon, pr_locs):
    best_id, best_d = None, float("inf")
    for lid, lat, lon in pr_locs:
        d = dist(noaa_lat, noaa_lon, lat, lon)
        if d < best_d:
            best_d, best_id = d, lid
    return best_id


def main():
    try:
        import pandas as pd
    except ImportError:
        print("Install: pip install pandas", file=sys.stderr)
        sys.exit(1)
    pr_all = PR_EXTRACTED / "pr_all_locations.csv"
    if not pr_all.exists():
        print("pr_all_locations.csv not found", file=sys.stderr)
        sys.exit(1)
    if not NOAA_CSV.exists():
        print("noaa_stations_in_domain.csv not found", file=sys.stderr)
        sys.exit(1)
    noaa = load_noaa(NOAA_CSV)
    pr_locs = load_pr_locations(pr_all)
    series = {}
    for s in noaa:
        usgs_id = nearest(s["lat"], s["lon"], pr_locs)
        pr_path = PR_EXTRACTED / f"pr_{usgs_id}.csv"
        if not pr_path.exists():
            continue
        df = pd.read_csv(pr_path)
        if df.empty or "date" not in df.columns:
            continue
        pr_col = "pr_mm_per_day" if "pr_mm_per_day" in df.columns else df.columns[-1]
        arr = [{"date": str(r["date"])[:10], "value": round(float(r[pr_col]), 2)} for _, r in df.iterrows()]
        if arr:
            series[s["id"]] = arr
    out = {"series": series}
    OUTPUT_FRONTEND.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FRONTEND, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(OUTPUT_DOCS, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Exported precipitation for {len(series)} stations")


if __name__ == "__main__":
    main()
