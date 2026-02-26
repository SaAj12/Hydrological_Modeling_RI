"""
Export sensors from sensors.txt to JSON for the Hydrological Modeling map.
Reads tab-separated: Station Name, Latitude, Longitude, Sensor Type.
Output: frontend/data/sensors_data.json, docs/data/sensors_data.json
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "sensors.txt"


def main():
    import argparse
    p = argparse.ArgumentParser(description="Export sensors to JSON for map")
    p.add_argument("-i", "--input", default=DEFAULT_INPUT, type=Path, help="Input sensors.txt path")
    args = p.parse_args()
    inp = args.input
    if not inp.exists():
        print(f"Input not found: {inp}")
        sys.exit(1)
    sensors = []
    with open(inp, "r", encoding="utf-8") as f:
        lines = f.readlines()
    if not lines:
        print("Empty file")
        sys.exit(0)
    header = lines[0].strip().split("\t")
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        try:
            lat = float(parts[1])
            lon = float(parts[2])
        except (ValueError, TypeError):
            continue
        sensors.append({
            "name": parts[0].strip(),
            "lat": lat,
            "lon": lon,
            "sensorType": parts[3].strip().lower(),
        })
    out = {"sensors": sensors}
    for subdir in ["frontend", "docs"]:
        d = PROJECT_ROOT / subdir / "data"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "sensors_data.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"Exported {len(sensors)} sensors to {p}")


if __name__ == "__main__":
    main()
