"""Deployment entrypoint for Flask platforms.

This shim exposes a root-level `app` so hosts that auto-detect Flask
entrypoints can run the project without changing backend package layout.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app  # noqa: E402

application = app
