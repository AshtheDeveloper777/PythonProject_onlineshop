"""
Vercel entrypoint for the Flask application.

We ensure the project root (where `app.py` lives) is on `sys.path`,
then import the Flask instance `app` from there so that Vercel
can expose it as the handler.
"""

import os
import sys
from pathlib import Path

# Add project root (parent of `api/`) to Python path so that
# `import app` finds `app.py` in the root of the repo.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app  # `app` is the Flask instance defined in app.py
