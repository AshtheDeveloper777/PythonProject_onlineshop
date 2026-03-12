import sys
from pathlib import Path

# Add the project root (parent of `api/`) to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app  # Flask instance defined in app.py
