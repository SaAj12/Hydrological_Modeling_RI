"""
Copy VTEC timeline PNGs into docs/images/vtec for the Hydrological Modeling GitHub Page.
Source: PROJECT_ROOT/data/vtec_figures or --source. If not found, use plot_vtec_timeline_all_stations.py
to generate PNGs from docs/vtec_by_usgs_and_noaa/*.csv (output goes directly to docs/images/vtec/).
"""
import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS = PROJECT_ROOT / "docs"
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "vtec_figures"
VTEC_IMAGES_DIR = DOCS / "images" / "vtec"


def main():
    p = argparse.ArgumentParser(description="Copy VTEC timeline figures into docs for GitHub Pages")
    p.add_argument(
        "--source", "-s",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Folder containing vtec_timeline_<STAID>.png (default: PROJECT_ROOT/data/vtec_figures)",
    )
    args = p.parse_args()
    src_dir = args.source
    if not src_dir.is_dir():
        print(f"Source directory not found: {src_dir}")
        return 1
    VTEC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for f in src_dir.glob("vtec_timeline_*.png"):
        dest = VTEC_IMAGES_DIR / f.name
        shutil.copy2(f, dest)
        count += 1
        print(f"  {f.name} -> {dest}")
    print(f"Copied {count} VTEC figures to {VTEC_IMAGES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
