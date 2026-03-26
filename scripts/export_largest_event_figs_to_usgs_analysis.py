"""
Copy largest-event analysis PNGs into the USGS analysis image folders.

Source (local only):
  analysis_outputs/station_<STAID8>_largest_event/
    - ams_2010_2025_rank.png
    - hydrograph_event.png

Destinations (for GitHub Pages + local frontend):
  docs/images/usgs_analysis/
  frontend/images/usgs_analysis/

Output filenames (per station):
  - ams_rank_2010_2025_<STAID8>.png
  - largest_event_hydrograph_2010_2025_<STAID8>.png

Run:
  python scripts/export_largest_event_figs_to_usgs_analysis.py
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "analysis_outputs"
DOCS_OUT = PROJECT_ROOT / "docs" / "images" / "usgs_analysis"
FRONT_OUT = PROJECT_ROOT / "frontend" / "images" / "usgs_analysis"

STA_RE = re.compile(r"^station_(\d{8})_largest_event$")


def main():
    DOCS_OUT.mkdir(parents=True, exist_ok=True)
    FRONT_OUT.mkdir(parents=True, exist_ok=True)

    ok = 0
    total = 0

    for p in sorted(SRC_ROOT.iterdir()):
        if not p.is_dir():
            continue
        m = STA_RE.match(p.name)
        if not m:
            continue
        staid8 = m.group(1)
        total += 1

        src_ams = p / "ams_2010_2025_rank.png"
        src_hyd = p / "hydrograph_event.png"
        if not src_ams.exists() or not src_hyd.exists():
            continue

        dst_ams = f"ams_rank_2010_2025_{staid8}.png"
        dst_hyd = f"largest_event_hydrograph_2010_2025_{staid8}.png"

        for out_dir in (DOCS_OUT, FRONT_OUT):
            shutil.copyfile(src_ams, out_dir / dst_ams)
            shutil.copyfile(src_hyd, out_dir / dst_hyd)
        ok += 1

    print(f"Copied: {ok}/{total} stations")
    print(f"  -> {DOCS_OUT}")
    print(f"  -> {FRONT_OUT}")


if __name__ == "__main__":
    main()

