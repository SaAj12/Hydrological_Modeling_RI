"""
Export NOAA Tides & Currents stations to JSON for the Hydrological Modeling map.
Reads from D:\\go\\pr\\noaa\\noaa_stations_in_domain.csv (or --input).
Output: frontend/data/noaa_stations.json, docs/data/noaa_stations.json
"""
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = Path(r"D:\go\pr\noaa\noaa_stations_in_domain.csv")


def main():
    import argparse
    p = argparse.ArgumentParser(description="Export NOAA stations to JSON for map")
    p.add_argument("-i", "--input", default=DEFAULT_INPUT, type=Path, help="Input CSV path")
    args = p.parse_args()
    inp = args.input
    if not inp.exists():
        print(f"Input not found: {inp}")
        sys.exit(1)
    stations = []
    with open(inp, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                lat = float(row.get("lat", 0))
                lon = float(row.get("lon", 0))
            except (ValueError, TypeError):
                continue
            stations.append({
                "id": row.get("id", "").strip(),
                "name": row.get("name", "").strip(),
                "lat": lat,
                "lon": lon,
                "state": row.get("state", "").strip(),
                "url": row.get("url", "").strip(),
            })
    out = {"stations": stations}
    for subdir in ["frontend", "docs"]:
        d = PROJECT_ROOT / subdir / "data"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "noaa_stations.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"Exported {len(stations)} NOAA stations to {p}")


if __name__ == "__main__":
    main()
