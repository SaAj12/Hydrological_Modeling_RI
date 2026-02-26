"""Export NOAA meteorological data per station to JSON for Chart.js."""
import json
import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent
DEFAULT_INPUT = PROJECT_ROOT / "noaa"
OUTPUT_FRONTEND = PROJECT_ROOT / "frontend" / "data" / "meteorological_data.json"
OUTPUT_DOCS = PROJECT_ROOT / "docs" / "data" / "meteorological_data.json"
PRODUCTS = ["air_temperature", "wind", "air_pressure", "water_temperature", "humidity", "visibility"]
COL_CANDIDATES = {
    "air_temperature": ["Air Temperature", "air temperature", "Air Temp", "t"],
    "wind": ["Speed", "speed", "Wind Speed", "Wind", "s"],
    "air_pressure": ["Air Pressure", "air pressure", "Barometric Pressure", "v"],
    "water_temperature": ["Water Temperature", "water temperature", "Water Temp", "v"],
    "humidity": ["Humidity", "humidity", "Relative Humidity", "v"],
    "visibility": ["Visibility", "visibility", "v"],
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
        print("noaa_stations_in_domain.csv not found", file=sys.stderr)
        sys.exit(1)
    df_sta = pd.read_csv(noaa_csv)
    col_id = next((c for c in df_sta.columns if str(c).lower().strip() == "id"), df_sta.columns[0])
    stations = [str(v).strip() for v in df_sta[col_id].dropna().unique() if str(v).strip().isdigit()]
    series = {}
    for sta in stations:
        panels = {}
        for product in PRODUCTS:
            path = DEFAULT_INPUT / f"{sta}_{product}.csv"
            if not path.exists():
                continue
            df = pd.read_csv(path)
            if df.empty or len(df.columns) < 2:
                continue
            tcol = _find_col(df, ["Date Time", "DateTime", "date_time", "t"]) or df.columns[0]
            vcol = _find_col(df, COL_CANDIDATES[product]) or df.columns[1]
            df["dt"] = df[tcol].apply(parse_dt)
            df["value"] = pd.to_numeric(df[vcol], errors="coerce")
            df = df.dropna(subset=["dt", "value"])
            arr = [{"date": r["dt"].strftime("%Y-%m-%d"), "value": round(float(r["value"]), 2)} for _, r in df.iterrows()]
            if arr:
                panels[product] = arr
        wl_path = DEFAULT_INPUT / f"{sta}_water_level.csv"
        pred_path = DEFAULT_INPUT / f"{sta}_predictions.csv"
        if wl_path.exists():
            wl_df = pd.read_csv(wl_path)
            if not wl_df.empty and len(wl_df.columns) >= 2:
                tcol = _find_col(wl_df, ["Date Time", "DateTime"]) or wl_df.columns[0]
                vcol = _find_col(wl_df, ["Water Level", " water level"]) or wl_df.columns[1]
                qcol = _find_col(wl_df, ["Quality", " quality"])
                wl_df["dt"] = wl_df[tcol].apply(parse_dt)
                wl_df["value"] = pd.to_numeric(wl_df[vcol], errors="coerce")
                wl_df["q"] = wl_df[qcol].astype(str).str.strip().str.lower() if qcol else "v"
                wl_df = wl_df.dropna(subset=["dt", "value"])
                verified = [{"date": r["dt"].strftime("%Y-%m-%d"), "value": round(float(r["value"]), 3)} for _, r in wl_df.iterrows() if r["q"] == "v"]
                preliminary = [{"date": r["dt"].strftime("%Y-%m-%d"), "value": round(float(r["value"]), 3)} for _, r in wl_df.iterrows() if r["q"] == "p"]
                predictions = []
                if pred_path.exists():
                    pdf = pd.read_csv(pred_path)
                    if not pdf.empty and len(pdf.columns) >= 2:
                        tcol = _find_col(pdf, ["Date Time", "DateTime"]) or pdf.columns[0]
                        pdf["dt"] = pdf[tcol].apply(parse_dt)
                        pdf["value"] = pd.to_numeric(pdf[pdf.columns[1]], errors="coerce")
                        pdf = pdf.dropna(subset=["dt", "value"])
                        predictions = [{"date": r["dt"].strftime("%Y-%m-%d"), "value": round(float(r["value"]), 3)} for _, r in pdf.iterrows()]
                panels["water_level"] = {"verified": verified, "preliminary": preliminary, "predictions": predictions}
        if panels:
            series[sta] = panels
    out = {"series": series}
    OUTPUT_FRONTEND.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FRONTEND, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(OUTPUT_DOCS, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Exported meteorological for {len(series)} stations")


if __name__ == "__main__":
    main()
