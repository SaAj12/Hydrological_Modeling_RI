"""
Export VTEC events per station to JSON for Chart.js.
Reads from docs/vtec_by_usgs_and_noaa/vtec_events_<STAID>.csv
Output: frontend/data/vtec_data.json
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent
DEFAULT_INPUT = PROJECT_ROOT / "docs" / "vtec_by_usgs_and_noaa"
OUTPUT_FRONTEND = PROJECT_ROOT / "frontend" / "data" / "vtec_data.json"
OUTPUT_DOCS = PROJECT_ROOT / "docs" / "data" / "vtec_data.json"

ALLOWED = [
    "Severe Thunderstorm Warning",
    "Flash Flood Warning",
    "Flood Warning",
    "High Wind Warning",
    "Tornado Warning",
    "Tropical Storm Warning",
    "Winter Storm Warning",
]


def parse_dt(s):
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def main():
    try:
        import pandas as pd
    except ImportError:
        print("Install: pip install pandas", file=sys.stderr)
        sys.exit(1)

    if not DEFAULT_INPUT.is_dir():
        print(f"Not found: {DEFAULT_INPUT}", file=sys.stderr)
        sys.exit(1)

    pattern = re.compile(r"^vtec_events_([^\\/]+)\.csv$", re.I)
    series = {}
    for f in sorted(os.listdir(DEFAULT_INPUT)):
        m = pattern.match(f)
        if not m or f == "vtec_events_all_locations.csv":
            continue
        staid = m.group(1)
        path = DEFAULT_INPUT / f
        df = pd.read_csv(path)
        if df.empty or "warning_name" not in df.columns or "issued" not in df.columns or "expired" not in df.columns:
            series[staid] = []
            continue
        df["warning_name"] = df["warning_name"].astype(str).str.strip()
        df = df[df["warning_name"].isin(ALLOWED)]
        df["issued_dt"] = df["issued"].apply(parse_dt)
        df["expired_dt"] = df["expired"].apply(parse_dt)
        df = df.dropna(subset=["issued_dt", "expired_dt"])
        arr = []
        for _, r in df.iterrows():
            issued = r["issued_dt"].strftime("%Y-%m-%d %H:%M") if hasattr(r["issued_dt"], "strftime") else str(r["issued"])[:16]
            expired = r["expired_dt"].strftime("%Y-%m-%d %H:%M") if hasattr(r["expired_dt"], "strftime") else str(r["expired"])[:16]
            arr.append({"warning_name": r["warning_name"], "issued": issued, "expired": expired})
        series[staid] = arr

    out = {"series": series, "warning_order": ALLOWED}
    OUTPUT_FRONTEND.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FRONTEND, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(OUTPUT_DOCS, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Exported VTEC for {len(series)} stations")


if __name__ == "__main__":
    main()
