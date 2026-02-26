"""
Prepare files for GitHub Pages deployment.
Run: python scripts/prepare_gh_pages.py
Creates/updates the 'docs' folder with frontend + exported data for GitHub Pages.
"""
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = PROJECT_ROOT / "frontend"
DOCS = PROJECT_ROOT / "docs"

SKIP_DATA_FILES = {"water_level_data.json", "meteorological_data.json", "precipitation_data.json", "vtec_data.json", "storms_data.json"}

def main():
    DOCS.mkdir(exist_ok=True)
    for name in ["index.html", "css", "js", "vendor", "images"]:
        src = FRONTEND / name
        dst = DOCS / name
        if src.is_file():
            shutil.copy2(src, dst)
        elif src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
    # Copy data/ but skip large JSON files (plots are PNGs, data stays local)
    src_data = FRONTEND / "data"
    dst_data = DOCS / "data"
    dst_data.mkdir(exist_ok=True)
    if src_data.is_dir():
        for f in src_data.iterdir():
            if f.is_file() and f.name not in SKIP_DATA_FILES:
                shutil.copy2(f, dst_data / f.name)
    print(f"Prepared {DOCS} for GitHub Pages.")
    print("In repo Settings > Pages > Source: Deploy from branch 'main', folder: /docs")

if __name__ == "__main__":
    main()
