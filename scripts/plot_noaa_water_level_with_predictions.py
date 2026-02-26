"""
Plot water level: Predictions, Verified observed, Preliminary observed, Observed - Predicted.
Reads from PROJECT_ROOT/noaa/ (or --input-dir). Writes to docs/images/noaa/ and frontend/images/noaa/.
X-axis: 1 Jan 2010 – 31 Dec 2025, year labels every 2 years.

Run from project root: python scripts/plot_noaa_water_level_with_predictions.py
"""
import argparse
import os
import sys
from datetime import datetime

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
DEFAULT_INPUT_DIR = os.path.join(PROJECT_ROOT, "noaa")
from chart_axis_constants import FIG_SIZE, apply_chart_xaxis


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
        if c.strip() in candidates or c.strip().lower() in [x.lower() for x in candidates]:
            return c
    return None


def load_water_level(csv_path):
    import pandas as pd
    df = pd.read_csv(csv_path)
    if df.empty or len(df.columns) < 2:
        return None, None, None
    time_col = _find_col(df, ["Date Time", "DateTime", "date time"]) or df.columns[0]
    value_col = _find_col(df, ["Water Level", " water level", "Water Level"]) or df.columns[1]
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


def load_observed_minus_predicted(csv_path):
    """Load precomputed Observed − Predicted from {station}_observed_minus_predicted.csv."""
    import pandas as pd
    if not os.path.isfile(csv_path):
        return None, None
    df = pd.read_csv(csv_path)
    if df.empty or len(df.columns) < 2:
        return None, None
    time_col = _find_col(df, ["Date Time", "DateTime"]) or df.columns[0]
    val_col = _find_col(df, ["Observed_minus_Predicted", "Observed minus Predicted", "value"]) or df.columns[1]
    df["dt"] = df[time_col].apply(parse_dt)
    df["value"] = pd.to_numeric(df[val_col], errors="coerce")
    df = df.dropna(subset=["dt", "value"])
    if df.empty:
        return None, None
    return df["dt"].values, df["value"].values


def run_plot(input_dir, output_dir, station):
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    wl_path = os.path.join(input_dir, f"{station}_water_level.csv")
    pred_path = os.path.join(input_dir, f"{station}_predictions.csv")
    omp_path = os.path.join(input_dir, f"{station}_observed_minus_predicted.csv")

    if not os.path.isfile(wl_path):
        print(f"  Skip: {wl_path} not found", file=sys.stderr)
        return False

    wl_dt, wl_val, quality = load_water_level(wl_path)
    if wl_dt is None:
        print(f"  Skip: no valid water level data in {wl_path}", file=sys.stderr)
        return False

    pred_dt, pred_val = None, None
    if os.path.isfile(pred_path):
        pred_dt, pred_val = load_predictions(pred_path)

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

    # Observed − Predicted: prefer precomputed file, else merge water_level and predictions
    res_dt, res_val = [], []
    if os.path.isfile(omp_path):
        res_dt, res_val = load_observed_minus_predicted(omp_path)
        if res_dt is None:
            res_dt, res_val = [], []
    if (not res_dt or len(res_dt) == 0) and pred_dt is not None and len(pred_dt) > 0:
        obs_df = pd.DataFrame({"dt": pd.to_datetime(wl_dt), "obs": wl_val})
        pred_df = pd.DataFrame({"dt": pd.to_datetime(pred_dt), "pred": pred_val})
        merged = obs_df.merge(pred_df, on="dt", how="inner")
        if not merged.empty:
            res_dt = merged["dt"].values
            res_val = (merged["obs"] - merged["pred"]).values

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    lw = 0.35
    if verified_dt:
        ax.plot(verified_dt, verified_val, color="steelblue", linewidth=lw, alpha=0.9, label="Verified")
    if prelim_dt:
        ax.plot(prelim_dt, prelim_val, color="orange", linewidth=lw, alpha=0.8, label="Preliminary")
    if pred_dt is not None and len(pred_dt) > 0:
        ax.plot(pred_dt, pred_val, color="green", linewidth=lw, alpha=0.8, label="Predictions")
    if res_dt is not None and len(res_dt) > 0:
        ax.plot(res_dt, res_val, color="crimson", linewidth=lw, alpha=0.8, label="Observed − Predicted")

    ax.set_xlabel("")
    ax.set_ylabel("m MLLW")
    ax.set_title(f"Station {station} — Water level: Predictions, Verified, Preliminary, Observed − Predicted", fontsize=12)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    apply_chart_xaxis(ax, set_limits=True)
    plt.xticks(rotation=0)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.94, bottom=0.1)
    out_path = os.path.join(output_dir, f"{station}_water_level_with_predictions.png")
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.02)
    plt.close()
    return True


def load_station_ids(csv_path):
    """Return list of station IDs from noaa_stations_in_domain.csv."""
    try:
        import pandas as pd
    except ImportError:
        return []
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


def main():
    p = argparse.ArgumentParser(description="Plot NOAA water level (2010–2025), output to docs and frontend")
    p.add_argument("--input-dir", "-i", default=DEFAULT_INPUT_DIR, help="Folder with station CSVs")
    p.add_argument("--stations", "-s", default=None, help="Comma-separated station IDs (default: all from noaa_stations_in_domain.csv)")
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
        wl_path = os.path.join(args.input_dir, f"{station}_water_level.csv")
        if not os.path.isfile(wl_path):
            continue
        for out_dir in outputs:
            if run_plot(args.input_dir, out_dir, station):
                print(f"  {station}: wrote to {out_dir}")
                ok_count += 1

    if ok_count == 0:
        print("No water level plots generated.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
