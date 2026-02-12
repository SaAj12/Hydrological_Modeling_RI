"""
Run the Hydrological Modeling backend (discharge only).
"""
import importlib.util
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
main_py_path = os.path.join(BACKEND_DIR, "main.py")

if not os.path.isfile(main_py_path):
    print("ERROR: main.py not found at", main_py_path)
    sys.exit(1)

sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

spec = importlib.util.spec_from_file_location("main", main_py_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app = module.app

print("Loaded main.py from:", os.path.abspath(main_py_path), flush=True)
print("Backend: http://127.0.0.1:8000", flush=True)
print("-" * 60, flush=True)

import uvicorn
uvicorn.run(app, host="127.0.0.1", port=8000)
