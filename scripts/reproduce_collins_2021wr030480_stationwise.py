"""
Create station-wise products analogous to Collins et al. (2022), Figures 2-8 and Tables 1-3.

Outputs are written to:
  analysis_outputs/collins_2021wr030480_stationwise/

Per station:
  - figs/fig1_station_<STAID8>.png
  - figs/fig2_station_<STAID8>.png
  - figs/fig3_station_<STAID8>.png
  - figs/fig5_station_<STAID8>.png
  - figs/fig7_station_<STAID8>.png
  - figs/fig8_station_<STAID8>.png
  - tables/table1_station_<STAID8>.csv
  - tables/table2_station_<STAID8>.csv
  - tables/table3_station_<STAID8>.csv
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.stats import hypergeom, norm, pearsonr
from scipy.optimize import minimize

matplotlib.use("Agg")

from chart_axis_constants import X_MIN, X_MAX

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DISCHARGE_JSON = PROJECT_ROOT / "frontend" / "data" / "discharge_data.json"
DEFAULT_CLIMATE_CSV = PROJECT_ROOT / "frontend" / "data" / "climate_indices_monthly.csv"
DEFAULT_OUT_ROOT = PROJECT_ROOT / "analysis_outputs" / "collins_2021wr030480_stationwise"

CLIMATE_COLS = ["amo", "nao", "pdo", "pna", "enso_soi", "mei", "ao"]
SEASONS = ["DJF", "MAM", "JJA", "SON"]
MONTHS = np.arange(1, 13, dtype=int)
WY_MONTH_ORDER = np.array([10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9], dtype=int)
WY_MONTH_LABELS = ["O", "N", "D", "J", "F", "M", "A", "M", "J", "J", "A", "S"]
MC_CI_SIMS = 100000


@dataclass
class TopFloodSeries:
    top10: pd.DataFrame
    top2: pd.DataFrame
    annual_max: pd.DataFrame
    all_ams: pd.DataFrame


def staid8(v) -> str:
    try:
        return str(int(float(str(v).strip()))).zfill(8)
    except Exception:
        return str(v).strip()


def season_for_month(m: int) -> str:
    if m in (12, 1, 2):
        return "DJF"
    if m in (3, 4, 5):
        return "MAM"
    if m in (6, 7, 8):
        return "JJA"
    return "SON"


def load_discharge(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_climate(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d["year"] = pd.to_numeric(d["year"], errors="coerce").astype("Int64")
    d["month"] = pd.to_numeric(d["month"], errors="coerce").astype("Int64")
    d = d.dropna(subset=["date", "year", "month"]).copy()
    d["year"] = d["year"].astype(int)
    d["month"] = d["month"].astype(int)
    for c in CLIMATE_COLS:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    # paper-like annual treatment:
    # - NAO: winter (Dec-Mar) lagged by 1 year
    # - others: annual means from monthly values
    # Restrict analyses to project window 2010-2025.
    ann = d.groupby("year")[CLIMATE_COLS].mean(numeric_only=True).reset_index()
    nao_w = d[d["month"].isin([12, 1, 2, 3])].copy()
    nao_w["nao_year"] = np.where(nao_w["month"] == 12, nao_w["year"] + 1, nao_w["year"])
    nao_lag = nao_w.groupby("nao_year")["nao"].mean().reset_index().rename(columns={"nao_year": "year", "nao": "nao_winter_lag1"})
    ann = ann.merge(nao_lag, on="year", how="left")
    ann = ann[(ann["year"] >= int(X_MIN.year)) & (ann["year"] <= int(X_MAX.year))].copy()
    return ann


def series_to_df(series: List[dict]) -> pd.DataFrame:
    d = pd.DataFrame(series or [])
    if d.empty:
        return pd.DataFrame(columns=["date", "value"])
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    d = d.dropna(subset=["date", "value"]).sort_values("date")
    return d


def build_top_flood_series(df_daily: pd.DataFrame) -> TopFloodSeries:
    d = df_daily.copy()
    d["year"] = d["date"].dt.year.astype(int)
    idx = d.groupby("year")["value"].idxmax()
    annual_max = d.loc[idx, ["date", "year", "value"]].sort_values("date").reset_index(drop=True)
    if annual_max.empty:
        empty = pd.DataFrame(columns=["date", "year", "value", "rank"])
        return TopFloodSeries(top10=empty, top2=empty, annual_max=annual_max, all_ams=annual_max)
    ranked = annual_max.sort_values("value", ascending=False).reset_index(drop=True)
    ranked["rank"] = np.arange(1, len(ranked) + 1)
    top10 = ranked.head(10).copy().sort_values("date")
    top2 = ranked.head(2).copy().sort_values("date")
    return TopFloodSeries(top10=top10, top2=top2, annual_max=annual_max, all_ams=annual_max)


def _annual_max_in_window_ranked(ts: TopFloodSeries, start_year: int, end_year: int) -> pd.DataFrame:
    d = ts.annual_max.copy()
    if d.empty:
        return d
    d = d[(d["year"] >= start_year) & (d["year"] <= end_year)].copy()
    if d.empty:
        return d
    r = d.sort_values("value", ascending=False).copy()
    r["rank"] = np.arange(1, len(r) + 1, dtype=int)
    d = d.merge(r[["year", "rank"]], on="year", how="left")
    d["is_top10"] = d["rank"] <= 10
    d["is_top2"] = d["rank"] <= 2
    return d.sort_values("year").reset_index(drop=True)


def fig1_station(ts: TopFloodSeries, out_path: Path, station_id: str):
    """
    Figure 1 analog:
    AMS floods during 2010-2025 (largest annual streamflow each year),
    with top-10 and top-2 identified by ranking AMS values within this period.
    """
    start_year = int(X_MIN.year)
    end_year = int(X_MAX.year)
    d = _annual_max_in_window_ranked(ts, start_year, end_year)
    if d.empty:
        return

    fig, ax = plt.subplots(figsize=(10.2, 4.8))
    # AMS baseline
    ax.plot(d["year"], d["value"], color="#4c78a8", linewidth=1.2, alpha=0.8, zorder=1)
    ax.scatter(d["year"], d["value"], color="#4c78a8", s=26, label="AMS (annual maxima)", zorder=2)

    # Top-10 and Top-2 in period
    d10 = d[d["is_top10"]]
    d2 = d[d["is_top2"]]
    if not d10.empty:
        ax.scatter(
            d10["year"],
            d10["value"],
            facecolors="none",
            edgecolors="#f59e0b",
            s=85,
            linewidths=1.5,
            label="Top-10 in 2010-2025",
            zorder=3,
        )
    if not d2.empty:
        ax.scatter(
            d2["year"],
            d2["value"],
            color="#16a34a",
            s=52,
            label="Top-2 in 2010-2025",
            zorder=4,
        )

    ax.set_title(f"Figure 1 analog — AMS and ranked floods (2010-2025), station {station_id}")
    ax.set_xlabel("Year")
    ax.set_ylabel("Annual maximum streamflow")
    ax.grid(alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def month_freq_percent(df_events: pd.DataFrame) -> np.ndarray:
    if df_events.empty:
        return np.zeros(12, dtype=float)
    m = df_events["date"].dt.month.astype(int).value_counts().to_dict()
    total = float(len(df_events))
    return np.array([100.0 * float(m.get(i, 0)) / total for i in MONTHS], dtype=float)


def fig2_station(ts: TopFloodSeries, out_path: Path, station_id: str):
    f10 = month_freq_percent(ts.top10)
    f2 = month_freq_percent(ts.top2)
    n = max(len(ts.top10), 1)

    # One-sided 95% CIs from empirical monthly-frequency distributions
    # under a non-seasonal circular-uniform model via Monte Carlo.
    # We simulate n floods, each equally likely in any month (1/12),
    # repeat 100,000 times, and take monthwise 5th/95th percentiles.
    rng = np.random.default_rng(20260323 + int(station_id))
    sim_counts = rng.multinomial(n=n, pvals=np.full(12, 1.0 / 12.0), size=MC_CI_SIMS)
    sim_freq = (sim_counts / float(n)) * 100.0
    lo = np.percentile(sim_freq, 5, axis=0)
    hi = np.percentile(sim_freq, 95, axis=0)

    # Figure 2 analog in water-year month order: Oct ... Sep
    f10_wy = np.array([f10[m - 1] for m in WY_MONTH_ORDER], dtype=float)
    f2_wy = np.array([f2[m - 1] for m in WY_MONTH_ORDER], dtype=float)

    fig, ax = plt.subplots(figsize=(10, 4.6))
    x = np.arange(12)
    ax.bar(x, f10_wy, color="#6699cc", edgecolor="#2f4f6f", linewidth=0.5, label="Top-10 monthly frequency")
    ax.scatter(x, f2_wy, color="#2ca02c", s=30, zorder=3, label="Top-2 monthly frequency")
    ax.axhline(100.0 / 12.0, color="gray", linestyle="--", linewidth=1.0, label="Uniform mean")
    lo_wy = np.array([lo[m - 1] for m in WY_MONTH_ORDER], dtype=float)
    hi_wy = np.array([hi[m - 1] for m in WY_MONTH_ORDER], dtype=float)
    ax.fill_between(x, lo_wy, hi_wy, color="gray", alpha=0.12, label=f"95% CI (MC={MC_CI_SIMS})")
    ax.set_xticks(x)
    ax.set_xticklabels(WY_MONTH_LABELS)
    ax.set_ylabel("Relative frequency (%)")
    ax.set_title(
        f"Figure 2 analog — Monthly seasonality (water year Oct-Sep), station {station_id}"
    )
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig3_station(ts: TopFloodSeries, out_path: Path, station_id: str):
    f_all = month_freq_percent(ts.all_ams)
    f10 = month_freq_percent(ts.top10)
    f2 = month_freq_percent(ts.top2)
    fig, ax = plt.subplots(figsize=(10, 4.6))
    x = np.arange(12)
    ax.plot(x, f_all, "-o", color="#444", label="All AMS")
    ax.plot(x, f10, "-o", color="#1f77b4", label="Top-10")
    ax.plot(x, f2, "-o", color="#2ca02c", label="Top-2")
    ax.set_xticks(x)
    ax.set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    ax.set_ylabel("Relative frequency (%)")
    ax.set_title(f"Figure 3 analog — AMS vs top floods seasonality, station {station_id}")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def observed_count_in_last_n_years(df_events: pd.DataFrame, n_last: int) -> int:
    if df_events.empty:
        return 0
    years = sorted(df_events["year"].dropna().astype(int).unique().tolist())
    if not years:
        return 0
    y_max = max(years)
    y_min = y_max - n_last + 1
    return int(((df_events["year"] >= y_min) & (df_events["year"] <= y_max)).sum())


def observed_count_in_years_range(df_events: pd.DataFrame, start_year: int, end_year: int) -> int:
    if df_events.empty:
        return 0
    return int(((df_events["year"] >= start_year) & (df_events["year"] <= end_year)).sum())


def _plot_hypergeom_distribution(N: int, K: int, n: int, observed: int, title: str, out_path: Path):
    xs = np.arange(0, K + 1)
    probs = hypergeom.pmf(xs, N, K, n)
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.bar(xs, probs, color="#7aa6d1", edgecolor="#2f4f6f", linewidth=0.6)
    if 0 <= observed <= K:
        ax.axvline(observed, color="#d62728", linewidth=2, label=f"Observed={observed}")
    ax.set_xlabel("Count in window")
    ax.set_ylabel("Probability")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig4_station(ts: TopFloodSeries, out_path: Path, station_id: str):
    N = int(len(ts.annual_max))
    K = int(min(10, N))
    n = int(min(25, N))
    obs = observed_count_in_last_n_years(ts.top10, 25)
    _plot_hypergeom_distribution(
        N=N,
        K=K,
        n=n,
        observed=obs,
        title=f"Figure 4 analog — Top-10 occurrence in last 25 years, station {station_id}",
        out_path=out_path,
    )


def fig5_station(ts: TopFloodSeries, out_path: Path, station_id: str):
    # Use the full project analysis window for "Figure 5 analog":
    # count the number of top-10 annual maxima that occur within 2010-2025.
    start_year = int(X_MIN.year)
    end_year = int(X_MAX.year)

    N = int(len(ts.annual_max))
    K = int(min(10, N))

    annual_years = ts.annual_max["year"].astype(int).unique().tolist()
    n_window = len([y for y in annual_years if start_year <= int(y) <= end_year])
    n = int(min(n_window, N))

    obs = observed_count_in_years_range(ts.top10, start_year=start_year, end_year=end_year)
    _plot_hypergeom_distribution(
        N=N,
        K=K,
        n=n,
        observed=obs,
        title=f"Figure 5 analog — Top-10 occurrence in {start_year}-{end_year}, station {station_id}",
        out_path=out_path,
    )


def fig6_station(ts: TopFloodSeries, out_path: Path, station_id: str):
    N = int(len(ts.annual_max))
    K = int(min(2, N))
    obs25 = observed_count_in_last_n_years(ts.top2, 25)
    obs10 = observed_count_in_last_n_years(ts.top2, 10)
    xs = np.arange(0, K + 1)
    p25 = hypergeom.pmf(xs, N, K, min(25, N))
    p10 = hypergeom.pmf(xs, N, K, min(10, N))

    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    axs[0].bar(xs, p25, color="#8db9df", edgecolor="#2f4f6f", linewidth=0.6)
    axs[0].axvline(obs25, color="#d62728", linewidth=2, label=f"Observed={obs25}")
    axs[0].set_title("Last 25 years")
    axs[0].set_xlabel("Top-2 count")
    axs[0].set_ylabel("Probability")
    axs[0].legend()
    axs[0].grid(axis="y", alpha=0.25)

    axs[1].bar(xs, p10, color="#8db9df", edgecolor="#2f4f6f", linewidth=0.6)
    axs[1].axvline(obs10, color="#d62728", linewidth=2, label=f"Observed={obs10}")
    axs[1].set_title("Last 10 years")
    axs[1].set_xlabel("Top-2 count")
    axs[1].legend()
    axs[1].grid(axis="y", alpha=0.25)
    fig.suptitle(f"Figure 6 analog — Top-2 occurrence expectations, station {station_id}")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def build_annual_count_series(ts: TopFloodSeries, top: int) -> pd.DataFrame:
    years = sorted(ts.annual_max["year"].astype(int).unique().tolist())
    if not years:
        return pd.DataFrame(columns=["year", "count"])
    base = pd.DataFrame({"year": years})
    if top == 2:
        tdf = ts.top2
    else:
        tdf = ts.top10
    c = tdf["year"].astype(int).value_counts().rename("count").reset_index().rename(columns={"index": "year"})
    out = base.merge(c, on="year", how="left")
    out["count"] = out["count"].fillna(0.0).astype(float)
    return out


def fit_quasi_poisson(y: np.ndarray, x: np.ndarray) -> Dict[str, float]:
    # Poisson log-link MLE, then quasi-dispersion correction for SE.
    X = np.column_stack([np.ones_like(x), x])

    def nll(beta):
        eta = X @ beta
        mu = np.exp(np.clip(eta, -30, 30))
        return float(np.sum(mu - y * eta))

    res = minimize(nll, x0=np.array([np.log(np.maximum(np.mean(y), 1e-6)), 0.0]), method="BFGS")
    beta = res.x
    eta = X @ beta
    mu = np.exp(np.clip(eta, -30, 30))
    denom = np.maximum(mu, 1e-9)
    phi = float(np.sum((y - mu) ** 2 / denom) / max(len(y) - 2, 1))
    W = np.diag(mu)
    info = X.T @ W @ X
    cov = phi * np.linalg.pinv(info)
    se = float(np.sqrt(max(cov[1, 1], 1e-12)))
    z = float(beta[1] / se) if se > 0 else 0.0
    p = float(2.0 * (1.0 - norm.cdf(abs(z))))
    x0 = float(np.min(x))
    x1 = float(np.max(x))
    trend_magnitude = float(np.exp(beta[0] + beta[1] * x1) - np.exp(beta[0] + beta[1] * x0))
    return {
        "beta0": float(beta[0]),
        "beta1": float(beta[1]),
        "phi": phi,
        "p_value": p,
        "trend_magnitude": trend_magnitude,
    }


def _trend_plot(df_counts: pd.DataFrame, top_label: str, station_id: str, out_path: Path, connect_observed: bool = True):
    d = df_counts.copy()
    y = d["count"].to_numpy(dtype=float)
    x = d["year"].to_numpy(dtype=float)
    fit = fit_quasi_poisson(y, x)
    mu = np.exp(fit["beta0"] + fit["beta1"] * x)
    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    if connect_observed:
        ax.plot(d["year"], d["count"], "o-", color="#4c78a8", label="Observed")
    else:
        ax.scatter(d["year"], d["count"], color="#4c78a8", s=30, label="Observed")
    ax.plot(d["year"], mu, "-", color="#e45756", linewidth=2, label="Quasi-Poisson fit")
    ax.set_title(f"{top_label} trend analog — station {station_id} (p={fit['p_value']:.3f})")
    ax.set_xlabel("Year")
    ax.set_ylabel("Flood events/year")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig7_station(ts: TopFloodSeries, out_path: Path, station_id: str):
    d2 = build_annual_count_series(ts, top=2)
    _trend_plot(d2, "Figure 7 analog (Top-2 annual counts)", station_id, out_path, connect_observed=True)


def fig8_station(ts: TopFloodSeries, out_path: Path, station_id: str):
    d10 = build_annual_count_series(ts, top=10)
    _trend_plot(d10, "Figure 8 analog (Top-10 annual counts)", station_id, out_path, connect_observed=False)


def table1_station(ts: TopFloodSeries, station_id: str) -> pd.DataFrame:
    d2 = build_annual_count_series(ts, top=2)
    d10 = build_annual_count_series(ts, top=10)
    f2 = fit_quasi_poisson(d2["count"].to_numpy(float), d2["year"].to_numpy(float))
    f10 = fit_quasi_poisson(d10["count"].to_numpy(float), d10["year"].to_numpy(float))
    return pd.DataFrame(
        [
            {"station_id": station_id, "series": "2_largest", "p_value": f2["p_value"], "trend_magnitude": f2["trend_magnitude"], "dispersion_phi": f2["phi"]},
            {"station_id": station_id, "series": "10_largest", "p_value": f10["p_value"], "trend_magnitude": f10["trend_magnitude"], "dispersion_phi": f10["phi"]},
        ]
    )


def table2_station(ts: TopFloodSeries, climate_annual: pd.DataFrame, station_id: str) -> pd.DataFrame:
    out_rows = []
    for top_name, topn in [("2_largest", 2), ("10_largest", 10)]:
        dc = build_annual_count_series(ts, top=topn)
        merged = dc.merge(climate_annual, on="year", how="inner")
        for idx_col in ["amo", "nao_winter_lag1", "pdo", "pna", "enso_soi", "mei", "ao"]:
            if idx_col not in merged.columns:
                continue
            sub = merged[["count", idx_col]].dropna()
            if len(sub) < 8:
                continue
            fit = fit_quasi_poisson(sub["count"].to_numpy(float), sub[idx_col].to_numpy(float))
            xv = sub[idx_col].to_numpy(float)
            yv = sub["count"].to_numpy(float)
            if np.nanstd(xv) <= 1e-12 or np.nanstd(yv) <= 1e-12:
                r2_pct = float("nan")
            else:
                r, _ = pearsonr(xv, yv)
                r2_pct = float((r ** 2) * 100.0)
            out_rows.append(
                {
                    "station_id": station_id,
                    "series": top_name,
                    "index": idx_col,
                    "p_value": fit["p_value"],
                    "coef": fit["beta1"],
                    "trend_over_index_range": fit["trend_magnitude"],
                    "pearson_r2_percent": r2_pct,
                }
            )
    return pd.DataFrame(out_rows)


def _season_distribution(df_events: pd.DataFrame) -> Dict[str, float]:
    if df_events.empty:
        return {s: 0.0 for s in SEASONS}
    ss = df_events["date"].dt.month.map(season_for_month)
    vc = ss.value_counts(normalize=True).to_dict()
    return {s: float(vc.get(s, 0.0)) for s in SEASONS}


def table3_station(ts: TopFloodSeries, station_id: str) -> pd.DataFrame:
    # Table 3 analog at station scale:
    # compare season proportions across All AMS / Top-10 / Top-2.
    rows = []
    for label, d in [("all_ams", ts.all_ams), ("10_largest", ts.top10), ("2_largest", ts.top2)]:
        dist = _season_distribution(d)
        row = {"station_id": station_id, "group": label}
        for s in SEASONS:
            row[f"{s}_fraction"] = dist[s]
        rows.append(row)
    return pd.DataFrame(rows)


def run_station(
    station: dict,
    series_map: Dict[str, list],
    climate_annual: pd.DataFrame,
    out_root: Path,
) -> bool:
    sid_raw = station.get("id")
    if sid_raw is None:
        return False
    sid8 = staid8(sid_raw)
    series = (
        series_map.get(str(sid_raw))
        or series_map.get(sid8)
        or (series_map.get(str(int(sid8))) if sid8.isdigit() else None)
    )
    if not series:
        return False
    df = series_to_df(series)
    if df.empty:
        return False

    ts = build_top_flood_series(df)
    if ts.annual_max.empty:
        return False

    figs = out_root / "figs"
    tabs = out_root / "tables"
    figs.mkdir(parents=True, exist_ok=True)
    tabs.mkdir(parents=True, exist_ok=True)

    fig2_station(ts, figs / f"fig2_station_{sid8}.png", sid8)
    fig1_station(ts, figs / f"fig1_station_{sid8}.png", sid8)
    fig3_station(ts, figs / f"fig3_station_{sid8}.png", sid8)
    fig5_station(ts, figs / f"fig5_station_{sid8}.png", sid8)
    fig7_station(ts, figs / f"fig7_station_{sid8}.png", sid8)
    fig8_station(ts, figs / f"fig8_station_{sid8}.png", sid8)

    t1 = table1_station(ts, sid8)
    t2 = table2_station(ts, climate_annual, sid8)
    t3 = table3_station(ts, sid8)
    t1.to_csv(tabs / f"table1_station_{sid8}.csv", index=False)
    t2.to_csv(tabs / f"table2_station_{sid8}.csv", index=False)
    t3.to_csv(tabs / f"table3_station_{sid8}.csv", index=False)

    return True


def parse_args():
    p = argparse.ArgumentParser(description="Generate station-wise Figure 2-8 and Table 1-3 analog outputs.")
    p.add_argument("--discharge-json", type=Path, default=DEFAULT_DISCHARGE_JSON)
    p.add_argument("--climate-csv", type=Path, default=DEFAULT_CLIMATE_CSV)
    p.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    p.add_argument("--only", type=str, default="", help="Optional station ID filter.")
    return p.parse_args()


def main():
    args = parse_args()
    data = load_discharge(args.discharge_json)
    climate_annual = load_climate(args.climate_csv)

    stations = data.get("stations", []) or []
    series_map = data.get("series", {}) or {}
    only = args.only.strip()
    only8 = staid8(only) if only else ""

    ok = 0
    total = 0
    for st in stations:
        sid = st.get("id")
        if sid is None:
            continue
        sid8 = staid8(sid)
        if only and sid8 != only8 and str(sid).strip() != only:
            continue
        total += 1
        try:
            if run_station(st, series_map, climate_annual, args.out_root):
                ok += 1
                print(f"{sid8}: done")
            else:
                print(f"{sid8}: skipped (missing/empty series)")
        except Exception as e:
            print(f"{sid8}: failed: {e}")

    print(f"Completed: {ok}/{total} stations.")
    print(f"Output root: {args.out_root}")


if __name__ == "__main__":
    main()

