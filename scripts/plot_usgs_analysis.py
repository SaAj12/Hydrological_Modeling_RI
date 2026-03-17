"""
Plot USGS analysis PNGs for GitHub Pages (static figures).

Outputs (per station, both frontend/ and docs/):
  - fdc_<STAID8>.png
  - pot_counts_annual_<STAID8>.png
  - pot_counts_seasonal_<STAID8>.png
  - seasonality_monthly_<STAID8>.png
  - extremes_topN_<STAID8>.png

Design decisions (from usgs_analysis_plan.txt):
  - POT threshold: target-rate method (≈2 events/year)
  - Declustering window: 14 days (keep max-Q within cluster)
  - Time window for time-based plots: show within 2010–2025 (clip axes, not data storage)

Run from project root:
  python scripts/plot_usgs_analysis.py
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent
DEFAULT_DISCHARGE_JSON = PROJECT_ROOT / "frontend" / "data" / "discharge_data.json"

sys.path.insert(0, str(_SCRIPT_DIR))
from chart_axis_constants import X_MIN, X_MAX, FIG_SIZE, FIG_WIDTH, FIG_HEIGHT, apply_chart_xaxis


def _staid_8(s):
    """Format station ID as 8-digit string."""
    if s is None or s == "":
        return ""
    try:
        return str(int(float(str(s).strip()))).zfill(8)
    except (TypeError, ValueError):
        return str(s).strip()


def _dt(s):
    if s is None:
        return None
    t = str(s).strip()
    if not t:
        return None
    try:
        return datetime.strptime(t[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _season_label(month: int) -> str:
    # Seasons: DJF, MAM, JJA, SON
    if month in (12, 1, 2):
        return "DJF"
    if month in (3, 4, 5):
        return "MAM"
    if month in (6, 7, 8):
        return "JJA"
    return "SON"


@dataclass(frozen=True)
class PotConfig:
    target_events_per_year: float = 2.0
    decluster_days: int = 14


def load_discharge(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run: python scripts/export_discharge_data.py")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def series_to_df(series):
    import pandas as pd

    df = pd.DataFrame(series or [])
    if df.empty:
        return df
    if "date" not in df.columns or "value" not in df.columns:
        return pd.DataFrame(columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date")
    return df


def window_df(df, x_min=X_MIN, x_max=X_MAX):
    """Subset to display window for time-based plots."""
    if df.empty:
        return df
    m = (df["date"] >= x_min) & (df["date"] <= x_max)
    return df.loc[m].copy()


def decluster_events(exceed_df, decluster_days: int):
    """
    Given dataframe of exceedances with columns date,value (sorted by date),
    decluster by grouping exceedances within decluster_days and keeping max value per cluster.
    Returns dataframe with event_date,event_value.
    """
    import pandas as pd

    if exceed_df.empty:
        return pd.DataFrame(columns=["event_date", "event_value"])

    exceed_df = exceed_df.sort_values("date").reset_index(drop=True)
    keep_rows = []
    cluster_start = 0
    for i in range(1, len(exceed_df)):
        gap = (exceed_df.loc[i, "date"] - exceed_df.loc[i - 1, "date"]).days
        if gap > decluster_days:
            chunk = exceed_df.iloc[cluster_start:i]
            j = chunk["value"].idxmax()
            keep_rows.append(exceed_df.loc[j])
            cluster_start = i
    # last cluster
    chunk = exceed_df.iloc[cluster_start:]
    j = chunk["value"].idxmax()
    keep_rows.append(exceed_df.loc[j])

    ev = pd.DataFrame(keep_rows)[["date", "value"]].copy()
    ev = ev.rename(columns={"date": "event_date", "value": "event_value"})
    ev = ev.sort_values("event_date").reset_index(drop=True)
    return ev


def annual_counts(events_df):
    import pandas as pd

    if events_df.empty:
        return pd.Series(dtype="float64")
    years = events_df["event_date"].dt.year.astype(int)
    return years.value_counts().sort_index()


def seasonal_counts(events_df):
    import pandas as pd

    if events_df.empty:
        return pd.DataFrame(columns=["year", "season", "count"])
    df = events_df.copy()
    df["year"] = df["event_date"].dt.year.astype(int)
    df["season"] = df["event_date"].dt.month.astype(int).map(_season_label)
    out = df.groupby(["year", "season"]).size().reset_index(name="count")
    return out


def choose_threshold_target_rate(df_window, cfg: PotConfig):
    """
    Choose a discharge threshold so mean declustered events/year ~ target.
    Returns threshold (float) and declustered events dataframe.
    """
    import numpy as np
    import pandas as pd

    if df_window.empty:
        return None, pd.DataFrame(columns=["event_date", "event_value"])

    vals = df_window["value"].dropna().astype(float).values
    if vals.size == 0:
        return None, pd.DataFrame(columns=["event_date", "event_value"])

    # Candidate thresholds across high quantiles (robust + fast).
    qs = np.concatenate([np.arange(0.80, 0.96, 0.02), np.arange(0.96, 0.995, 0.005), np.arange(0.995, 0.9995, 0.001)])
    qs = np.clip(qs, 0.0, 0.9999)
    candidates = np.unique(np.quantile(vals, qs))
    candidates = candidates[np.isfinite(candidates)]
    if candidates.size == 0:
        return None, pd.DataFrame(columns=["event_date", "event_value"])

    # Determine which years are "in play" inside the display window (have any observations).
    years_with_data = sorted(set(df_window["date"].dt.year.astype(int).tolist()))
    if not years_with_data:
        return None, pd.DataFrame(columns=["event_date", "event_value"])

    best = None
    best_events = None
    best_score = None

    for thr in candidates:
        exc = df_window.loc[df_window["value"] >= thr, ["date", "value"]].dropna()
        if exc.empty:
            continue
        ev = decluster_events(exc, cfg.decluster_days)
        c = annual_counts(ev)
        # mean over years in window; missing years treated as 0
        mean_rate = float(sum(float(c.get(y, 0.0)) for y in years_with_data) / len(years_with_data))
        score = abs(mean_rate - cfg.target_events_per_year)
        # Prefer thresholds that don't wildly exceed target (ties go to higher threshold / fewer events).
        tie_break = mean_rate
        key = (score, tie_break)
        if best_score is None or key < best_score:
            best_score = key
            best = float(thr)
            best_events = ev

    if best is None:
        return None, pd.DataFrame(columns=["event_date", "event_value"])
    return best, best_events


def plot_fdc(df, out_path, staid8):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    vals = df["value"].dropna().astype(float).values
    if vals.size == 0:
        return False
    vals = np.sort(vals)[::-1]
    n = vals.size
    p = (np.arange(1, n + 1) / (n + 1.0)) * 100.0

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(p, vals, color="#3fb950", linewidth=1.2)
    ax.set_xlabel("Percent exceedance (%)")
    ax.set_ylabel("Discharge (cfs)")
    ax.set_title(f"Flow duration curve (FDC) — Station {staid8}", fontsize=12)
    ax.grid(True, alpha=0.25)
    try:
        ax.set_yscale("log")
    except Exception:
        pass
    fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.12)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return True


def plot_pot_annual(events_df, out_path, staid8, threshold, cfg: PotConfig):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    years = list(range(X_MIN.year, X_MAX.year + 1))
    counts = {int(y): 0 for y in years}
    if not events_df.empty:
        c = annual_counts(events_df)
        for y in years:
            counts[int(y)] = int(c.get(int(y), 0))

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.bar(years, [counts[y] for y in years], color="steelblue", edgecolor="navy", linewidth=0.4)
    ax.set_ylabel("Event count")
    ax.set_xlabel("Year")
    title_thr = f"{threshold:.3g}" if threshold is not None else "—"
    ax.set_title(
        f"POT event counts (annual) — Station {staid8}\n"
        f"Target {cfg.target_events_per_year:g} events/yr, decluster {cfg.decluster_days} days, threshold {title_thr} cfs",
        fontsize=11,
    )
    ax.grid(True, axis="y", alpha=0.25)
    ax.set_xlim(X_MIN.year - 0.8, X_MAX.year + 0.8)
    ax.set_xticks(list(range(X_MIN.year, X_MAX.year + 1, 2)))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.14)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return True


def plot_pot_seasonal(events_df, out_path, staid8, threshold, cfg: PotConfig):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    seasons = ["DJF", "MAM", "JJA", "SON"]
    years = list(range(X_MIN.year, X_MAX.year + 1))

    # Build year x season matrix
    mat = {s: [0 for _ in years] for s in seasons}
    if not events_df.empty:
        sc = seasonal_counts(events_df)
        if not sc.empty:
            by = {(int(r["year"]), str(r["season"])): int(r["count"]) for _, r in sc.iterrows()}
            for yi, y in enumerate(years):
                for s in seasons:
                    mat[s][yi] = by.get((int(y), s), 0)

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    bottom = [0 for _ in years]
    colors = {"DJF": "#58a6ff", "MAM": "#3fb950", "JJA": "#f0883e", "SON": "#bf8700"}
    for s in seasons:
        ax.bar(years, mat[s], bottom=bottom, label=s, color=colors.get(s, None), edgecolor="#222", linewidth=0.2)
        bottom = [b + v for b, v in zip(bottom, mat[s])]

    ax.set_ylabel("Event count")
    ax.set_xlabel("Year")
    title_thr = f"{threshold:.3g}" if threshold is not None else "—"
    ax.set_title(
        f"POT event counts (seasonal) — Station {staid8}\n"
        f"Target {cfg.target_events_per_year:g} events/yr, decluster {cfg.decluster_days} days, threshold {title_thr} cfs",
        fontsize=11,
    )
    ax.grid(True, axis="y", alpha=0.25)
    ax.set_xlim(X_MIN.year - 0.8, X_MAX.year + 0.8)
    ax.set_xticks(list(range(X_MIN.year, X_MAX.year + 1, 2)))
    ax.legend(ncol=4, fontsize=9, frameon=False, loc="upper left")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.14)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return True


def plot_seasonality_monthly(events_df, out_path, staid8):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    months = list(range(1, 13))
    counts = {m: 0 for m in months}
    if not events_df.empty:
        vc = events_df["event_date"].dt.month.value_counts()
        for m in months:
            counts[m] = int(vc.get(m, 0))

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.bar(months, [counts[m] for m in months], color="#6e7681", edgecolor="#30363d", linewidth=0.4)
    ax.set_xlabel("Month")
    ax.set_ylabel("Event count")
    ax.set_title(f"Flood seasonality (monthly) — Station {staid8}", fontsize=12)
    ax.set_xticks(months)
    ax.grid(True, axis="y", alpha=0.25)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.12)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return True


def plot_extremes_topn(df_window, out_path, staid8, n_top=10):
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if df_window.empty:
        return False
    d = df_window.dropna(subset=["date", "value"]).copy()
    if d.empty:
        return False
    d["year"] = d["date"].dt.year.astype(int)
    # Annual maxima (calendar year)
    idx = d.groupby("year")["value"].idxmax()
    peaks = d.loc[idx, ["date", "value", "year"]].sort_values("value", ascending=False).head(int(n_top))
    if peaks.empty:
        return False

    peaks = peaks.reset_index(drop=True)
    peaks["rank"] = list(range(1, len(peaks) + 1))

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.scatter(peaks["rank"], peaks["value"], color="#d29922", edgecolor="#8a6f00", zorder=3)
    for _, r in peaks.iterrows():
        label = f"{r['year']}"
        ax.annotate(label, (r["rank"], r["value"]), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.set_xlabel("Rank (1 = largest annual max)")
    ax.set_ylabel("Discharge (cfs)")
    ax.set_title(f"Large floods (top-N annual maxima) — Station {staid8}", fontsize=12)
    ax.grid(True, alpha=0.25)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.12)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return True


def main():
    p = argparse.ArgumentParser(description="Generate USGS analysis PNGs (FDC, POT, seasonality, extremes)")
    p.add_argument("--discharge-json", type=Path, default=DEFAULT_DISCHARGE_JSON)
    p.add_argument("--target-events-per-year", type=float, default=2.0)
    p.add_argument("--decluster-days", type=int, default=14)
    p.add_argument("--top-n", type=int, default=10)
    p.add_argument("--only", type=str, default="", help="Optional single station id (raw or 8-digit)")
    args = p.parse_args()

    try:
        import pandas as pd  # noqa: F401
        import matplotlib  # noqa: F401
        matplotlib.use("Agg")
    except ImportError:
        print("Install dependencies: python -m pip install pandas matplotlib numpy", file=sys.stderr)
        sys.exit(1)

    cfg = PotConfig(target_events_per_year=float(args.target_events_per_year), decluster_days=int(args.decluster_days))

    data = load_discharge(args.discharge_json)
    stations = data.get("stations", [])
    series_map = data.get("series", {}) or {}

    out_dirs = [
        PROJECT_ROOT / "docs" / "images" / "usgs_analysis",
        PROJECT_ROOT / "frontend" / "images" / "usgs_analysis",
    ]
    for d in out_dirs:
        d.mkdir(parents=True, exist_ok=True)

    only = args.only.strip()
    if only:
        only8 = _staid_8(only)
    else:
        only8 = ""

    ok = 0
    total = 0
    for st in stations:
        sid = st.get("id", "")
        if not sid:
            continue
        staid8 = _staid_8(sid)
        if only8 and staid8 != only8 and str(sid).strip() != only.strip():
            continue

        series = series_map.get(str(sid)) or series_map.get(staid8) or series_map.get(str(int(staid8))) if staid8.isdigit() else None
        if not series:
            continue

        total += 1
        df = series_to_df(series)
        dfw = window_df(df, X_MIN, X_MAX)
        if df.empty:
            continue

        threshold, events = choose_threshold_target_rate(dfw, cfg)

        wrote_any = False
        for out_dir in out_dirs:
            if plot_fdc(df, str(out_dir / f"fdc_{staid8}.png"), staid8):
                wrote_any = True
            if plot_pot_annual(events, str(out_dir / f"pot_counts_annual_{staid8}.png"), staid8, threshold, cfg):
                wrote_any = True
            if plot_pot_seasonal(events, str(out_dir / f"pot_counts_seasonal_{staid8}.png"), staid8, threshold, cfg):
                wrote_any = True
            if plot_seasonality_monthly(events, str(out_dir / f"seasonality_monthly_{staid8}.png"), staid8):
                wrote_any = True
            if plot_extremes_topn(dfw, str(out_dir / f"extremes_topN_{staid8}.png"), staid8, n_top=args.top_n):
                wrote_any = True

        if wrote_any:
            ok += 1
            print(f"  {staid8}  (thr={threshold:.3g} cfs, events={len(events)})")
        else:
            print(f"  {staid8}: skip (no data)", file=sys.stderr)

    print(f"Done: {ok}/{total} stations")


if __name__ == "__main__":
    main()

