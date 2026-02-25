"""
Plot water level: Predictions, Verified observed, Preliminary observed, Observed - Predicted.
Reads from PROJECT_ROOT/noaa/ (or --input-dir). Writes to docs/images/noaa/ and frontend/images/noaa/.
X-axis: 1 Jan 2010 – 31 Dec 2025.

Run from project root: python scripts/plot_noaa_water_level_with_predictions.py
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


def run_plot(input_dir, output_dir, station):
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    wl_path = os.path.join(input_dir, f"{station}_water_level.csv")
    pred_path = os.path.join(input_dir, f"{station}_predictions.csv")

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

    res_dt, res_val = [], []
    if pred_dt is not None and len(pred_dt) > 0:
        obs_df = pd.DataFrame({"dt": pd.to_datetime(wl_dt), "obs": wl_val})
        pred_df = pd.DataFrame({"dt": pd.to_datetime(pred_dt), "pred": pred_val})
        merged = obs_df.merge(pred_df, on="dt", how="inner")
        if not merged.empty:
            res_dt = merged["dt"].values
            res_val = (merged["obs"] - merged["pred"]).values

    fig, ax = plt.subplots(figsize=(12, 4))
    lw = 0.35
    if verified_dt:
        ax.plot(verified_dt, verified_val, color="steelblue", linewidth=lw, alpha=0.9, label="Verified")
    if prelim_dt:
        ax.plot(prelim_dt, prelim_val, color="orange", linewidth=lw, alpha=0.8, label="Preliminary")
    if pred_dt is not None and len(pred_dt) > 0:
        ax.plot(pred_dt, pred_val, color="green", linewidth=lw, alpha=0.8, label="Predictions")
    if len(res_dt) > 0:
        ax.plot(res_dt, res_val, color="crimson", linewidth=lw, alpha=0.8, label="Observed − Predicted")

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title(f"Station {station} — Water level (m MLLW)", fontsize=12)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(X_MIN, X_MAX)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    plt.xticks(rotation=0)
    plt.tight_layout()
    out_path = os.path.join(output_dir, f"{station}_water_level_with_predictions.png")
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return True


def main():
    p = argparse.ArgumentParser(description="Plot NOAA water level (2010–2025), output to docs and frontend")
    p.add_argument("--input-dir", "-i", default=DEFAULT_INPUT_DIR, help="Folder with station CSVs")
    p.add_argument("--station", "-s", default="8454000", help="Station ID")
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

    outputs = [
        os.path.join(PROJECT_ROOT, "docs", "images", "noaa"),
        os.path.join(PROJECT_ROOT, "frontend", "images", "noaa"),
    ]
    ok = False
    for out_dir in outputs:
        if run_plot(args.input_dir, out_dir, args.station):
            print(f"Wrote {args.station}_water_level_with_predictions.png to {out_dir}")
            ok = True
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
