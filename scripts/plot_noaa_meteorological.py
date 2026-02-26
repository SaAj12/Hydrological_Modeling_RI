"""
Plot NOAA meteorological data as separate single-panel figures per product.
Products: air_pressure, air_temperature, water_temperature, wind, humidity.
Reads from noaa/*.csv. Writes to docs/images/noaa/ and frontend/images/noaa/.
X-axis: 1 Jan 2010 – 31 Dec 2025, year labels every 2 years.

Output: {station}_air_pressure.png, {station}_air_temperature.png, etc.

Run from project root: python scripts/plot_noaa_meteorological.py
"""
import argparse
import os
import sys
from datetime import datetime

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
DEFAULT_INPUT_DIR = os.path.join(PROJECT_ROOT, "noaa")
from chart_axis_constants import FIG_SIZE, apply_chart_xaxis

# Products to plot (order: air_pressure, air_temperature, water_temperature, wind, humidity)
PRODUCTS = ["air_pressure", "air_temperature", "water_temperature", "wind", "humidity"]
PRODUCT_CONFIG = {
    "air_pressure": (
        ["Air Pressure", "air pressure", "Barometric Pressure", "v"],
        "hPa",
        "Air pressure",
    ),
    "air_temperature": (
        ["Air Temperature", "air temperature", "Air Temp", "t"],
        "°C",
        "Air temperature",
    ),
    "water_temperature": (
        ["Water Temperature", "water temperature", "Water Temp", "v"],
        "°C",
        "Water temperature",
    ),
    "wind": (
        ["Speed", "speed", "Wind Speed", "Wind", "s"],
        "m/s",
        "Wind speed",
    ),
    "humidity": (
        ["Humidity", "humidity", "Relative Humidity", "v"],
        "%",
        "Humidity",
    ),
}


def parse_dt(s):
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def _find_col(df, candidates):
    for c in df.columns:
        cst = str(c).strip()
        if cst in candidates or cst.lower() in [x.lower() for x in candidates]:
            return c
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load_product_csv(csv_path, value_candidates):
    """Load time series from met CSV. Returns (dt_array, value_array) or (None, None)."""
    import pandas as pd
    if not os.path.isfile(csv_path):
        return None, None
    df = pd.read_csv(csv_path)
    if df.empty or len(df.columns) < 2:
        return None, None
    time_col = _find_col(df, ["Date Time", "DateTime", "date_time", "t"]) or df.columns[0]
    value_col = _find_col(df, value_candidates)
    if value_col is None:
        value_col = df.columns[1]
    df["dt"] = df[time_col].apply(parse_dt)
    df["value"] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=["dt", "value"])
    if df.empty:
        return None, None
    return df["dt"].values, df["value"].values


def load_station_ids(csv_path):
    import pandas as pd
    if not os.path.isfile(csv_path):
        return []
    df = pd.read_csv(csv_path, encoding="utf-8")
    col_lower = {str(c).lower().strip(): c for c in df.columns}
    id_col = col_lower.get("id") or list(df.columns)[0]
    ids = []
    for v in df[id_col].dropna().unique():
        s = str(v).strip()
        if s and s.isdigit():
            ids.append(s)
    return ids


def plot_one_product(input_dir, output_dir, station, product):
    """Plot one station/product. Returns True if plot was written."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cfg = PRODUCT_CONFIG[product]
    path = os.path.join(input_dir, f"{station}_{product}.csv")
    dt, val = load_product_csv(path, cfg[0])
    if dt is None or len(dt) == 0:
        return False

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(dt, val, color="steelblue", linewidth=0.35, alpha=0.9)
    ax.set_title(f"Station {station} — {cfg[2]}", fontsize=12)
    ax.set_ylabel(cfg[1], fontsize=10)
    ax.set_xlabel("")
    ax.grid(True, alpha=0.3)
    apply_chart_xaxis(ax, set_limits=True)
    plt.xticks(rotation=0)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.94, bottom=0.1)
    out_path = os.path.join(output_dir, f"{station}_{product}.png")
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.02)
    plt.close()
    return True


def main():
    p = argparse.ArgumentParser(description="Plot NOAA meteorological data (separate plots per product)")
    p.add_argument("--input-dir", "-i", default=DEFAULT_INPUT_DIR, help="Folder with station CSVs")
    p.add_argument("--stations", "-s", default=None, help="Comma-separated station IDs (default: all)")
    args = p.parse_args()

    try:
        import matplotlib
        matplotlib.use("Agg")
    except ImportError:
        print("Install: python -m pip install pandas matplotlib", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.input_dir):
        print(f"Directory not found: {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    if args.stations:
        stations = [s.strip() for s in args.stations.split(",") if s.strip()]
    else:
        noaa_csv = os.path.join(PROJECT_ROOT, "noaa", "noaa_stations_in_domain.csv")
        stations = load_station_ids(noaa_csv)

    outputs = [
        os.path.join(PROJECT_ROOT, "docs", "images", "noaa"),
        os.path.join(PROJECT_ROOT, "frontend", "images", "noaa"),
    ]

    ok_count = 0
    for station in stations:
        for product in PRODUCTS:
            for out_dir in outputs:
                if plot_one_product(args.input_dir, out_dir, station, product):
                    print(f"  {station} {product} -> {out_dir}")
                    ok_count += 1
                    break

    if ok_count == 0:
        print("No meteorological plots generated. Run download_noaa_meteorological_all.py first.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
