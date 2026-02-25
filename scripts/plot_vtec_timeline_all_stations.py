"""
Plot VTEC timeline for every station for the Hydrological Modeling GitHub Page.
Reads vtec_events_<STAID>.csv from docs/vtec_by_usgs, plots only selected warning
classes, x-axis 1 Jan 2010–31 Dec 2025, y-axis warning_name. Writes PNGs to
docs/images/vtec/ so https://saaj12.github.io/Hydrological-Modeling/ can show
each figure below the discharge chart for the corresponding station.

Allowed warning_name (plotted in this order):
  Severe Thunderstorm Warning, Flash Flood Warning, Flood Warning,
  High Wind Warning, Tornado Warning, Tropical Storm Warning, Winter Storm Warning

Run from viewer2: python scripts/plot_vtec_timeline_all_stations.py
Dependencies: pip install pandas matplotlib
"""
import argparse
import os
import re
import sys
from datetime import datetime

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
DOCS = os.path.join(PROJECT_ROOT, "docs")
DEFAULT_INPUT_DIR = os.path.join(DOCS, "vtec_by_usgs")
DEFAULT_OUTPUT_DIR = os.path.join(DOCS, "images", "vtec")

# Plot ONLY these 7 warning types, in this y-axis order (matches discharge chart era 1950–2025)
ALLOWED_WARNING_NAMES = [
    "Severe Thunderstorm Warning",
    "Flash Flood Warning",
    "Flood Warning",
    "High Wind Warning",
    "Tornado Warning",
    "Tropical Storm Warning",
    "Winter Storm Warning",
]
ALLOWED_SET = frozenset(ALLOWED_WARNING_NAMES)
X_MIN = datetime(2010, 1, 1)
X_MAX = datetime(2025, 12, 31)


def parse_dt(s):
    """Parse 'YYYY-MM-DD HH:MM' or similar to datetime."""
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def plot_one(csv_path: str, output_path: str, station_id: str) -> bool:
    """Plot one station's VTEC timeline (filtered classes, x 1950–2025); return True on success."""
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        return False

    df = pd.read_csv(csv_path)
    if df.empty:
        df = pd.DataFrame(columns=["warning_name", "issued", "expired"])
    for col in ["warning_name", "issued", "expired"]:
        if col not in df.columns:
            return False

    # Normalize warning_name (strip whitespace) so filtering matches
    df["warning_name"] = df["warning_name"].astype(str).str.strip()
    df["issued_dt"] = df["issued"].apply(parse_dt)
    df["expired_dt"] = df["expired"].apply(parse_dt)
    df = df.dropna(subset=["issued_dt", "expired_dt"])
    # Keep ONLY the 7 allowed warning types; drop all others
    df = df[df["warning_name"].isin(ALLOWED_SET)].copy()
    # Y-axis: only these 7 types, in fixed order; show only types that have data (or all 7 if empty)
    name_order = [n for n in ALLOWED_WARNING_NAMES if (not df.empty and n in df["warning_name"].values)]
    if not name_order:
        name_order = list(ALLOWED_WARNING_NAMES)
    name_to_y = {n: i for i, n in enumerate(name_order)}
    df["y"] = df["warning_name"].map(name_to_y)
    bar_height = 0.7
    df["width"] = (df["expired_dt"] - df["issued_dt"]).dt.total_seconds() / (24 * 3600)
    df["left"] = df["issued_dt"]

    fig, ax = plt.subplots(figsize=(14, max(6, len(name_order) * 0.5)))
    for _, row in df.iterrows():
        ax.barh(
            row["y"],
            row["width"],
            left=mdates.date2num(row["left"]),
            height=bar_height,
            align="center",
            color="steelblue",
            edgecolor="navy",
            linewidth=0.5,
        )
    ax.set_yticks(range(len(name_order)))
    ax.set_yticklabels(name_order, fontsize=14)
    ax.set_ylim(-0.6, len(name_order) - 0.4)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title(f"VTEC events — Station {station_id}", fontsize=14)
    ax.xaxis_date()
    # Fixed x-axis: 1 Jan 2010 – 31 Dec 2025 (match discharge chart)
    ax.set_xlim(mdates.date2num(X_MIN), mdates.date2num(X_MAX))
    # Same style as discharge: years only, 10-year increment (1950, 1960, 1970, ...)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.tick_params(axis="both", labelsize=14)
    plt.xticks(rotation=0)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return True


def main():
    p = argparse.ArgumentParser(
        description="Plot VTEC timeline per station for GitHub Page (2010–2025, selected warning types)"
    )
    p.add_argument(
        "--input-dir", "-i", default=DEFAULT_INPUT_DIR,
        help="Directory containing vtec_events_<STAID>.csv (default: docs/vtec_by_usgs)",
    )
    p.add_argument(
        "--output-dir", "-o", default=DEFAULT_OUTPUT_DIR,
        help="Directory for PNGs (default: docs/images/vtec)",
    )
    args = p.parse_args()
    output_dir = args.output_dir

    try:
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
    except ImportError:
        print("Install dependencies: python -m pip install pandas matplotlib", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.input_dir):
        print(f"Directory not found: {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    pattern = re.compile(r"^vtec_events_([^\\/]+)\.csv$", re.I)
    files = []
    for f in os.listdir(args.input_dir):
        m = pattern.match(f)
        if m and f != "vtec_events_all_locations.csv":
            staid = m.group(1)
            files.append((staid, os.path.join(args.input_dir, f)))
    files.sort(key=lambda x: x[0])

    if not files:
        print(f"No per-station CSVs in {args.input_dir} (expected vtec_events_<STAID>.csv)", file=sys.stderr)
        sys.exit(1)

    print("Warning types plotted:", ", ".join(ALLOWED_WARNING_NAMES))
    print("X-axis: 2010-01-01 to 2025-12-31")
    ok = 0
    for staid, csv_path in files:
        out_path = os.path.join(output_dir, f"vtec_timeline_{staid}.png")
        if plot_one(csv_path, out_path, staid):
            print(f"  {staid}: {out_path}")
            ok += 1
        else:
            print(f"  {staid}: skip (no data or bad format)", file=sys.stderr)
    print(f"Done: {ok}/{len(files)} figures in {output_dir}")


if __name__ == "__main__":
    main()
