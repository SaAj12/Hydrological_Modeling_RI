"""
Export NOAA water level + predictions to JSON for Chart.js.
Reads from noaa/*.csv. Output: frontend/data/water_level_data.json, docs/data/water_level_data.json

Run: python scripts/export_water_level_data.py
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent
DEFAULT_INPUT = PROJECT_ROOT / "noaa"
OUTPUT_FRONTEND = PROJECT_ROOT / "frontend" / "data" / "water_level_data.json"
OUTPUT_DOCS = PROJECT_ROOT / "docs" / "data" / "water_level_data.json"


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
        if str(c).strip().lower() in [x.lower() for x in candidates]:
            return c
    return None


def main():
    try:
        import pandas as pd
    except ImportError:
        print("Install: pip install pandas", file=sys.stderr)
        sys.exit(1)

    noaa_csv = PROJECT_ROOT / "noaa" / "noaa_stations_in_domain.csv"
    if not noaa_csv.exists():
        print(f"Noaa stations not found: {noaa_csv}", file=sys.stderr)
        sys.exit(1)
    df_sta = pd.read_csv(noaa_csv)
    col_id = next((c for c in df_sta.columns if str(c).lower().strip() == "id"), df_sta.columns[0])
    stations = [str(v).strip() for v in df_sta[col_id].dropna().unique() if str(v).strip().isdigit()]

    series = {}
    for sta in stations:
        wl_path = DEFAULT_INPUT / f"{sta}_water_level.csv"
        pred_path = DEFAULT_INPUT / f"{sta}_predictions.csv"
        if not wl_path.exists():
            continue

        df = pd.read_csv(wl_path)
        if df.empty or len(df.columns) < 2:
            continue
        time_col = _find_col(df, ["Date Time", "DateTime", "date time"]) or df.columns[0]
        value_col = _find_col(df, ["Water Level", " water level"]) or df.columns[1]
        quality_col = _find_col(df, ["Quality", " quality"])
        df["dt"] = df[time_col].apply(parse_dt)
        df["value"] = pd.to_numeric(df[value_col], errors="coerce")
        df["quality"] = df[quality_col].astype(str).str.strip().str.lower() if quality_col else "v"
        df = df.dropna(subset=["dt", "value"])

        verified = []
        preliminary = []
        for _, r in df.iterrows():
            d = r["dt"].strftime("%Y-%m-%d") if hasattr(r["dt"], "strftime") else str(r["dt"])[:10]
            v = float(r["value"])
            if (r["quality"] if quality_col else "v").strip().lower() == "p":
                preliminary.append({"date": d, "value": v})
            else:
                verified.append({"date": d, "value": v})

        predictions = []
        if pred_path.exists():
            pdf = pd.read_csv(pred_path)
            if not pdf.empty and len(pdf.columns) >= 2:
                tcol = _find_col(pdf, ["Date Time", "DateTime"]) or pdf.columns[0]
                vcol = pdf.columns[1]
                pdf["dt"] = pdf[tcol].apply(parse_dt)
                pdf["value"] = pd.to_numeric(pdf[vcol], errors="coerce")
                pdf = pdf.dropna(subset=["dt", "value"])
                for _, r in pdf.iterrows():
                    d = r["dt"].strftime("%Y-%m-%d") if hasattr(r["dt"], "strftime") else str(r["dt"])[:10]
                    predictions.append({"date": d, "value": float(r["value"])})

        obs_df = df[["dt", "value"]].copy()
        obs_df.columns = ["dt", "obs"]
        pred_df = pd.DataFrame(predictions)
        if not pred_df.empty:
            pred_df["dt"] = pd.to_datetime(pred_df["date"])
            merged = obs_df.merge(pred_df.rename(columns={"value": "pred"}), left_on="dt", right_on="dt", how="inner")
            residual = [{"date": r["dt"].strftime("%Y-%m-%d") if hasattr(r["dt"], "strftime") else str(r["dt"])[:10],
                        "value": round(float(r["obs"]) - float(r["pred"]), 4)} for _, r in merged.iterrows()]
        else:
            residual = []

        if verified or preliminary or predictions or residual:
            series[sta] = {
                "verified": verified,
                "preliminary": preliminary,
                "predictions": predictions,
                "residual": residual,
            }

    out = {"series": series}
    OUTPUT_FRONTEND.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FRONTEND, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(OUTPUT_DOCS, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Exported water level data for {len(series)} stations")


if __name__ == "__main__":
    main()
