"""
Publish-ready export: copy PNGs from analysis_outputs/figs into USGS analysis image folders.

Source (local):
  analysis_outputs/figs/
    - fig{1,2,3,5,7,8}_station_<STAID8>.png
    - ams_2010_2025_rank_<STAID8>.png
    - hydrograph_event_<STAID8>.png

Destinations (for GitHub Pages + local frontend):
  docs/images/usgs_analysis/
  frontend/images/usgs_analysis/

Filename mapping:
  - figX_station_<STAID8>.png  -> (same name)
  - ams_2010_2025_rank_<STAID8>.png -> ams_rank_2010_2025_<STAID8>.png
  - hydrograph_event_<STAID8>.png   -> largest_event_hydrograph_2010_2025_<STAID8>.png

Run:
  python scripts/export_analysis_outputs_figs_to_usgs_analysis.py
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "analysis_outputs" / "figs"
DOCS_OUT = PROJECT_ROOT / "docs" / "images" / "usgs_analysis"
FRONT_OUT = PROJECT_ROOT / "frontend" / "images" / "usgs_analysis"

RE_STATIONWISE = re.compile(r"^(fig[123578]_station_(\d{8})\.png)$")
RE_AMS = re.compile(r"^ams_2010_2025_rank_(\d{8})\.png$")
RE_HYD = re.compile(r"^hydrograph_event_(\d{8})\.png$")


def _copy(src: Path, dst_name: str):
    for out_dir in (DOCS_OUT, FRONT_OUT):
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out_dir / dst_name)


def main():
    if not SRC_DIR.exists():
        raise SystemExit(f"Missing {SRC_DIR}")

    ok = 0
    for p in sorted(SRC_DIR.glob("*.png")):
        name = p.name

        m = RE_STATIONWISE.match(name)
        if m:
            _copy(p, m.group(1))
            ok += 1
            continue

        m = RE_AMS.match(name)
        if m:
            staid8 = m.group(1)
            _copy(p, f"ams_rank_2010_2025_{staid8}.png")
            ok += 1
            continue

        m = RE_HYD.match(name)
        if m:
            staid8 = m.group(1)
            _copy(p, f"largest_event_hydrograph_2010_2025_{staid8}.png")
            ok += 1
            continue

    print(f"Copied {ok} PNGs from {SRC_DIR}")
    print(f"  -> {DOCS_OUT}")
    print(f"  -> {FRONT_OUT}")


if __name__ == "__main__":
    main()

