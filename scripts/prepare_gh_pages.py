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

def main():
    DOCS.mkdir(exist_ok=True)
    for name in ["index.html", "css", "js", "data"]:
        src = FRONTEND / name
        dst = DOCS / name
        if src.is_file():
            shutil.copy2(src, dst)
        elif src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
    print(f"Prepared {DOCS} for GitHub Pages.")
    print("In repo Settings > Pages > Source: Deploy from branch 'main', folder: /docs")

if __name__ == "__main__":
    main()
