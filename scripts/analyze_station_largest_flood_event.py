"""
Analyze the single largest flood event (rank-1) for a station.

Station: default 01114000
Analysis window: chart_axis_constants.X_MIN .. X_MAX (2010-2025)

Outputs (local only; not used by GitHub Pages):
  analysis_outputs/stations_largest_event/station_<STAID8>_largest_event/
    - report.csv
    - metrics.json
    - hydrograph_event.png
    - ams_2010_2025_rank.png
"""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib
from matplotlib import pyplot as plt

matplotlib.use("Agg")

from chart_axis_constants import X_MIN, X_MAX


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DISCHARGE_JSON = PROJECT_ROOT / "frontend" / "data" / "discharge_data.json"
DEFAULT_OUT_ROOT = PROJECT_ROOT / "analysis_outputs"
LEGEND_FONTSIZE = 10

METHODOLOGY_TEXT = """Largest (rank-1) flood event analysis methodology
=================================================

Data input
---------
- Source: frontend/data/discharge_data.json
- Uses the station's discharge time series stored in the JSON (daily values).

Analysis window
--------------
- Restricted to the project analysis window defined in scripts/chart_axis_constants.py:
  X_MIN = 2010-01-01
  X_MAX = 2025-12-31

Annual Maximum Series (AMS)
---------------------------
- For each calendar year in 2010–2025 with data, compute the annual maximum discharge value (daily max).
- This produces an AMS series with one value per year (where available).

Ranking within 2010–2025
------------------------
- Rank AMS values by magnitude within 2010–2025 only:
  rank=1 is the largest annual maximum, rank=2 is the second-largest, etc.
- “Top-10” and “Top-2” are defined using this ranking within 2010–2025.

Largest event definition (rank-1)
---------------------------------
- The “largest event” is the AMS rank-1 year’s peak day (the day of the annual maximum in 2010–2025).

Event window around the peak
----------------------------
- Default threshold: the 90th percentile (q90) of daily discharge values within 2010–2025.
- Starting from the peak day, the event window expands backward/forward until there are
  3 consecutive days below q90 on each side (a simple separation rule).

Metrics computed
----------------
- Peak timing/magnitude: peak date, peak value, peak year.
- AMS context: number of AMS years in-window; rank of the peak within 2010–2025; empirical return period
  using plotting-position p ≈ rank/(N+1) with N = number of AMS years in-window.
- Separation from #2: Q1/Q2 and Q1−Q2 using the 2nd largest AMS value in 2010–2025.
- Daily thresholds: q50, q90, q95, q99 from all daily values in 2010–2025.
- Event-window timing: start/end date, total duration, rise time (start→peak), recession time (peak→end).
- Duration above thresholds: number of days within the event window with Q ≥ q90/q95/q99.
- Volume proxy: sum over event window of max(Q − q50, 0) (units: discharge·days).
- Antecedent wetness proxies: mean discharge over the 7/14/30 days prior to the peak (and its percentile
  relative to all daily values in 2010–2025).

Outputs written
---------------
- metrics.json: full metrics dictionary.
- report.csv: one-row CSV with the same metrics.
- hydrograph_event.png: hydrograph around the event window (with highlighted window + thresholds).
- ams_2010_2025_rank.png: AMS scatter plot with Top-10 and Top-2 highlighted.
"""


def staid8(v) -> str:
    try:
        return str(int(float(str(v).strip()))).zfill(8)
    except Exception:
        return str(v).strip()


def load_discharge(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def series_to_df(series: List[dict]) -> pd.DataFrame:
    d = pd.DataFrame(series or [])
    if d.empty:
        return pd.DataFrame(columns=["date", "value"])
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    d = d.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)
    return d


def window_df(df: pd.DataFrame, x_min=X_MIN, x_max=X_MAX) -> pd.DataFrame:
    if df.empty:
        return df
    m = (df["date"] >= x_min) & (df["date"] <= x_max)
    return df.loc[m].copy().reset_index(drop=True)


def annual_max_series(df_window: pd.DataFrame) -> pd.DataFrame:
    d = df_window.copy()
    d["year"] = d["date"].dt.year.astype(int)
    idx = d.groupby("year")["value"].idxmax()
    ams = d.loc[idx, ["year", "date", "value"]].sort_values("year").reset_index(drop=True)
    return ams


def rank_ams(ams: pd.DataFrame) -> pd.DataFrame:
    if ams.empty:
        return ams
    r = ams.sort_values("value", ascending=False).reset_index(drop=True).copy()
    r["rank"] = np.arange(1, len(r) + 1, dtype=int)
    out = ams.merge(r[["year", "rank"]], on="year", how="left")
    return out.sort_values("year").reset_index(drop=True)


def empirical_return_period_years(rank: int, n_years: int) -> float:
    # Simple plotting-position style estimate:
    # exceedance probability p ≈ rank/(N+1) => T ≈ 1/p
    if n_years <= 0:
        return float("nan")
    p = float(rank) / float(n_years + 1)
    return 1.0 / p if p > 0 else float("inf")


def find_event_window(
    df_window: pd.DataFrame,
    peak_date: pd.Timestamp,
    threshold: float,
    consecutive_below: int = 3,
) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    Define an event window as the maximal interval around the peak where discharge is above 'threshold',
    stopping when we see 'consecutive_below' days below threshold on each side.
    """
    d = df_window.set_index("date").sort_index()
    if peak_date not in d.index:
        peak_date = d.index[d.index.get_indexer([peak_date], method="nearest")[0]]

    # walk backward
    below = 0
    start = peak_date
    for dt in reversed(d.loc[:peak_date].index[:-1]):
        if float(d.loc[dt, "value"]) < threshold:
            below += 1
        else:
            below = 0
        start = dt
        if below >= consecutive_below:
            # start at first day after the below-run
            start = d.loc[dt:peak_date].index[consecutive_below]
            break

    # walk forward
    below = 0
    end = peak_date
    for dt in d.loc[peak_date:].index[1:]:
        if float(d.loc[dt, "value"]) < threshold:
            below += 1
        else:
            below = 0
        end = dt
        if below >= consecutive_below:
            # end at day before below-run starts
            end = d.loc[peak_date:dt].index[-(consecutive_below + 1)]
            break

    return (pd.Timestamp(start), pd.Timestamp(end))


def antecedent_stats(df_window: pd.DataFrame, peak_date: pd.Timestamp, days: int) -> Dict[str, float]:
    d = df_window.set_index("date").sort_index()
    end = peak_date - pd.Timedelta(days=1)
    start = peak_date - pd.Timedelta(days=days)
    win = d.loc[start:end]["value"].dropna()
    if win.empty:
        return {"mean": float("nan"), "median": float("nan")}
    return {"mean": float(win.mean()), "median": float(win.median())}


def percentile_of_value(values: np.ndarray, v: float) -> float:
    values = values[np.isfinite(values)]
    if values.size == 0 or not np.isfinite(v):
        return float("nan")
    return float(100.0 * (np.sum(values <= v) / values.size))


def plot_hydrograph(
    df_window: pd.DataFrame,
    peak_date: pd.Timestamp,
    event_start: pd.Timestamp,
    event_end: pd.Timestamp,
    thresholds: Dict[str, float],
    out_path: Path,
    station_id: str,
):
    pad = pd.Timedelta(days=30)
    x0 = max(df_window["date"].min(), event_start - pad)
    x1 = min(df_window["date"].max(), event_end + pad)
    d = df_window[(df_window["date"] >= x0) & (df_window["date"] <= x1)].copy()

    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.plot(d["date"], d["value"], color="#2563eb", linewidth=1.3)
    ax.axvline(peak_date, color="#dc2626", linewidth=1.5, label="Peak day")
    ax.axvspan(event_start, event_end, color="#f59e0b", alpha=0.12, label="Event window")

    for k, thr in thresholds.items():
        ax.axhline(thr, linestyle="--", linewidth=1.0, alpha=0.7, label=f"{k} = {thr:.2f}")

    ax.set_title(f"Station {station_id} — Largest event hydrograph (2010-2025)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Discharge (daily)")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=LEGEND_FONTSIZE, ncol=3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_ams_rank(
    ams_ranked: pd.DataFrame,
    out_path: Path,
    station_id: str,
):
    fig, ax = plt.subplots(figsize=(12, 4.6))
    ax.scatter(ams_ranked["year"], ams_ranked["value"], color="#4c78a8", s=28, label="AMS (2010-2025)")
    top10 = ams_ranked[ams_ranked["rank"] <= 10]
    top2 = ams_ranked[ams_ranked["rank"] <= 2]
    if not top10.empty:
        ax.scatter(top10["year"], top10["value"], facecolors="none", edgecolors="#f59e0b", s=95, linewidths=1.6, label="Top-10")
    if not top2.empty:
        ax.scatter(top2["year"], top2["value"], color="#16a34a", s=55, label="Top-2")
    ax.set_title(f"Station {station_id} — AMS ranking (2010-2025)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Annual maximum discharge")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=LEGEND_FONTSIZE)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def analyze_one_station(
    sid8: str,
    series_map: Dict[str, list],
    out_root: Path,
) -> Optional[Path]:
    out_dir = out_root / "stations_largest_event" / f"station_{sid8}_largest_event"
    out_dir.mkdir(parents=True, exist_ok=True)

    series = series_map.get(sid8) or (series_map.get(str(int(sid8))) if sid8.isdigit() else None) or series_map.get(str(sid8))
    if not series:
        return None

    df = series_to_df(series)
    dfw = window_df(df, X_MIN, X_MAX)
    if dfw.empty:
        return None

    ams = annual_max_series(dfw)
    ams_ranked = rank_ams(ams)
    n_years = int(len(ams_ranked))
    if n_years <= 0:
        return None

    # Largest event (rank 1)
    largest = ams_ranked.sort_values("value", ascending=False).iloc[0]
    peak_year = int(largest["year"])
    peak_date = pd.Timestamp(largest["date"])
    peak_value = float(largest["value"])
    rank1 = int(largest["rank"])

    # Second largest for separation metric
    if len(ams_ranked) >= 2:
        second = ams_ranked.sort_values("value", ascending=False).iloc[1]
        q2 = float(second["value"])
    else:
        q2 = float("nan")

    # Thresholds from the daily series in-window
    vals = dfw["value"].to_numpy(dtype=float)
    q50 = float(np.nanpercentile(vals, 50))
    q90 = float(np.nanpercentile(vals, 90))
    q95 = float(np.nanpercentile(vals, 95))
    q99 = float(np.nanpercentile(vals, 99))

    # Event window around peak (use q90 as a default event threshold)
    event_start, event_end = find_event_window(dfw, peak_date, threshold=q90, consecutive_below=3)
    ev = dfw[(dfw["date"] >= event_start) & (dfw["date"] <= event_end)].copy()
    ev_days = int((event_end - event_start).days) + 1
    rise_days = int((peak_date - event_start).days)
    recession_days = int((event_end - peak_date).days)

    # Duration above thresholds within event window
    dur_q90 = int((ev["value"] >= q90).sum())
    dur_q95 = int((ev["value"] >= q95).sum())
    dur_q99 = int((ev["value"] >= q99).sum())

    # Volume above median within event window (cfs-days)
    vol_above_q50 = float(np.nansum(np.maximum(ev["value"].to_numpy(float) - q50, 0.0)))

    # Antecedent wetness proxies
    ant7 = antecedent_stats(dfw, peak_date, 7)
    ant14 = antecedent_stats(dfw, peak_date, 14)
    ant30 = antecedent_stats(dfw, peak_date, 30)
    ant7_pct = percentile_of_value(vals, ant7["mean"])
    ant14_pct = percentile_of_value(vals, ant14["mean"])
    ant30_pct = percentile_of_value(vals, ant30["mean"])

    # Rarity metrics
    emp_T = empirical_return_period_years(rank=1, n_years=n_years)
    q1_q2_ratio = float(peak_value / q2) if np.isfinite(q2) and q2 > 0 else float("nan")
    q1_minus_q2 = float(peak_value - q2) if np.isfinite(q2) else float("nan")

    metrics = {
        "station_id": sid8,
        "analysis_window_start": str(X_MIN.date()),
        "analysis_window_end": str(X_MAX.date()),
        "ams_years_in_window": n_years,
        "largest_event_year": peak_year,
        "largest_event_date": str(peak_date.date()),
        "largest_event_value": peak_value,
        "largest_event_rank_in_ams_2010_2025": rank1,
        "empirical_return_period_years_rank1": emp_T,
        "second_largest_value": q2,
        "q1_over_q2": q1_q2_ratio,
        "q1_minus_q2": q1_minus_q2,
        "daily_quantiles_in_window": {"q50": q50, "q90": q90, "q95": q95, "q99": q99},
        "event_window": {"start": str(event_start.date()), "end": str(event_end.date())},
        "event_duration_days": ev_days,
        "rise_days_start_to_peak": rise_days,
        "recession_days_peak_to_end": recession_days,
        "duration_days_above_q90_within_event": dur_q90,
        "duration_days_above_q95_within_event": dur_q95,
        "duration_days_above_q99_within_event": dur_q99,
        "volume_cfs_days_above_q50_within_event": vol_above_q50,
        "antecedent_mean_discharge": {
            "7d_mean": ant7["mean"],
            "14d_mean": ant14["mean"],
            "30d_mean": ant30["mean"],
        },
        "antecedent_mean_percentile_within_2010_2025_daily": {
            "7d_mean_pct": ant7_pct,
            "14d_mean_pct": ant14_pct,
            "30d_mean_pct": ant30_pct,
        },
    }

    # Save metrics + methodology
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    pd.DataFrame([metrics]).to_csv(out_dir / "report.csv", index=False)
    (out_dir / "methodology.txt").write_text(METHODOLOGY_TEXT, encoding="utf-8")

    # Plots
    plot_hydrograph(
        df_window=dfw,
        peak_date=peak_date,
        event_start=event_start,
        event_end=event_end,
        thresholds={"q90": q90, "q95": q95, "q99": q99},
        out_path=out_dir / "hydrograph_event.png",
        station_id=sid8,
    )
    plot_ams_rank(ams_ranked, out_dir / "ams_2010_2025_rank.png", station_id=sid8)
    return out_dir


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--station", type=str, default="01114000")
    p.add_argument("--all", action="store_true", help="Run for all stations in discharge_data.json")
    p.add_argument("--discharge-json", type=Path, default=DEFAULT_DISCHARGE_JSON)
    p.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    args = p.parse_args()

    data = load_discharge(args.discharge_json)
    stations = data.get("stations", []) or []
    series_map = data.get("series", {}) or {}

    if args.all:
        ok = 0
        total = 0
        for st in stations:
            sid = st.get("id")
            if sid is None:
                continue
            total += 1
            sid8 = staid8(sid)
            try:
                out = analyze_one_station(sid8, series_map, args.out_root)
                if out is not None:
                    ok += 1
                    print(f"{sid8}: done")
                else:
                    print(f"{sid8}: skipped (missing/empty series in 2010-2025)")
            except Exception as e:
                print(f"{sid8}: failed: {e}")
        print(f"Completed: {ok}/{total} stations.")
    else:
        sid8 = staid8(args.station)
        out = analyze_one_station(sid8, series_map, args.out_root)
        if out is None:
            raise SystemExit(f"Station {sid8}: skipped (missing/empty series in 2010-2025)")
        print(f"Wrote: {out}")


if __name__ == "__main__":
    main()

