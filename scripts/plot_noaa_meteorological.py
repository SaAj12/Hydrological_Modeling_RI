"""
Plot NOAA meteorological data plus water level with predictions.
Water level: verified, preliminary, predictions, observed − predicted.
Met: air temp, wind, pressure, water temp, humidity, visibility.
Reads from noaa/*.csv. Writes to docs/images/noaa/ and frontend/images/noaa/.
X-axis: 1 Jan 2010 – 31 Dec 2025.

Run from project root: python scripts/plot_noaa_meteorological.py
"""
import argparse
import os
import sys
from datetime import datetime

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
DEFAULT_INPUT_DIR = os.path.join(PROJECT_ROOT, "noaa")
X_MIN = datetime(2010, 1, 1)
X_MAX = datetime(2025, 12, 31)

# Product -> (column candidates, y-label, title)
PRODUCT_CONFIG = {
    "air_temperature": (
        ["Air Temperature", "air temperature", "Air Temp", "t"],
        "°C",
        "Air temperature",
    ),
    "wind": (
        ["Speed", "speed", "Wind Speed", "Wind", "s"],
        "m/s",
        "Wind speed",
    ),
    "air_pressure": (
        ["Air Pressure", "air pressure", "Barometric Pressure", "v"],
        "hPa",
        "Air pressure",
    ),
    "water_temperature": (
        ["Water Temperature", "water temperature", "Water Temp", "v"],
        "°C",
        "Water temperature",
    ),
    "humidity": (
        ["Humidity", "humidity", "Relative Humidity", "v"],
        "%",
        "Humidity",
    ),
    "visibility": (
        ["Visibility", "visibility", "v"],
        "km",
        "Visibility",
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
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        cst = str(c).strip()
        if cst in candidates or cst.lower() in [x.lower() for x in candidates]:
            return c
    return None


def load_product_csv(csv_path, value_candidates):
    """Load time series from met CSV. Returns (dt_array, value_array) or (None, None)."""
    import pandas as pd
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


def load_water_level(csv_path):
    """Load water level with quality. Returns (dt, value, quality) or (None, None, None)."""
    import pandas as pd
    df = pd.read_csv(csv_path)
    if df.empty or len(df.columns) < 2:
        return None, None, None
    time_col = _find_col(df, ["Date Time", "DateTime", "date time"]) or df.columns[0]
    value_col = _find_col(df, ["Water Level", " water level"]) or df.columns[1]
    quality_col = _find_col(df, ["Quality", " quality"])
    df["dt"] = df[time_col].apply(parse_dt)
    df["value"] = pd.to_numeric(df[value_col], errors="coerce")
    if quality_col is not None:
        df["quality"] = df[quality_col].astype(str).str.strip().str.lower()
    else:
        df["quality"] = "v"
    df = df.dropna(subset=["dt"])
    df = df[df["value"].notna()]
    if df.empty:
        return None, None, None
    return df["dt"].values, df["value"].values, df["quality"].values


def load_predictions(csv_path):
    """Load predictions. Returns (dt, value) or (None, None)."""
    import pandas as pd
    df = pd.read_csv(csv_path)
    if df.empty or len(df.columns) < 2:
        return None, None
    time_col = _find_col(df, ["Date Time", "DateTime"]) or df.columns[0]
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


def run_plot(input_dir, output_dir, station):
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    # Water level with predictions (first panel)
    wl_data = None
    wl_path = os.path.join(input_dir, f"{station}_water_level.csv")
    pred_path = os.path.join(input_dir, f"{station}_predictions.csv")
    if os.path.isfile(wl_path):
        wl_dt, wl_val, quality = load_water_level(wl_path)
        if wl_dt is not None and len(wl_dt) > 0:
            verified_dt, verified_val = [], []
            prelim_dt, prelim_val = [], []
            for i in range(len(wl_dt)):
                q = (quality[i] if quality is not None else "v").strip().lower()
                if q == "v":
                    verified_dt.append(wl_dt[i])
                    verified_val.append(wl_val[i])
                elif q == "p":
                    prelim_dt.append(wl_dt[i])
                    prelim_val.append(wl_val[i])
            pred_dt, pred_val = None, None
            if os.path.isfile(pred_path):
                pred_dt, pred_val = load_predictions(pred_path)
            res_dt, res_val = [], []
            if pred_dt is not None and len(pred_dt) > 0:
                obs_df = pd.DataFrame({"dt": pd.to_datetime(wl_dt), "obs": wl_val})
                pred_df = pd.DataFrame({"dt": pd.to_datetime(pred_dt), "pred": pred_val})
                merged = obs_df.merge(pred_df, on="dt", how="inner")
                if not merged.empty:
                    res_dt = merged["dt"].values
                    res_val = (merged["obs"] - merged["pred"]).values
            wl_data = (verified_dt, verified_val, prelim_dt, prelim_val, pred_dt, pred_val, res_dt, res_val)

    # Meteorological products
    met_panels = []
    for product in PRODUCT_CONFIG:
        path = os.path.join(input_dir, f"{station}_{product}.csv")
        if os.path.isfile(path):
            cfg = PRODUCT_CONFIG[product]
            dt, val = load_product_csv(path, cfg[0])
            if dt is not None and len(dt) > 0:
                met_panels.append((product, dt, val, cfg))

    if not wl_data and not met_panels:
        return False

    panels = []
    if wl_data:
        panels.append(("water_level", wl_data, None))
    for item in met_panels:
        panels.append(("met", item, None))

    n = len(panels)
    ncols = 2
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 3 * nrows), squeeze=False)
    lw = 0.35

    for idx, panel in enumerate(panels):
        ax = axes[idx // ncols, idx % ncols]
        if panel[0] == "water_level":
            vdt, vval, pdt, pval, pred_dt, pred_val, res_dt, res_val = panel[1]
            if vdt:
                ax.plot(vdt, vval, color="steelblue", linewidth=lw, alpha=0.9, label="Verified")
            if pdt:
                ax.plot(pdt, pval, color="orange", linewidth=lw, alpha=0.8, label="Preliminary")
            if pred_dt is not None and len(pred_dt) > 0:
                ax.plot(pred_dt, pred_val, color="green", linewidth=lw, alpha=0.8, label="Predictions")
            if len(res_dt) > 0:
                ax.plot(res_dt, res_val, color="crimson", linewidth=lw, alpha=0.8, label="Observed − Predicted")
            ax.set_title("Water level (m MLLW)", fontsize=10)
            ax.set_ylabel("m", fontsize=9)
            ax.legend(loc="upper right", fontsize=7)
        else:
            product, dt, val, cfg = panel[1]
            ax.plot(dt, val, color="steelblue", linewidth=lw, alpha=0.9)
            ax.set_title(cfg[2], fontsize=10)
            ax.set_ylabel(cfg[1], fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(X_MIN, X_MAX)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator(5))

    for idx in range(len(panels), nrows * ncols):
        axes[idx // ncols, idx % ncols].set_visible(False)

    plt.suptitle(f"Station {station} — Water level & meteorological", fontsize=12, y=1.02)
    plt.tight_layout()
    out_path = os.path.join(output_dir, f"{station}_meteorological.png")
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return True


def main():
    p = argparse.ArgumentParser(description="Plot NOAA meteorological data for all stations")
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
        for out_dir in outputs:
            if run_plot(args.input_dir, out_dir, station):
                print(f"  {station}: meteorological plot -> {out_dir}")
                ok_count += 1
                break

    if ok_count == 0:
        print("No meteorological plots generated. Run download_noaa_meteorological.py first.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
