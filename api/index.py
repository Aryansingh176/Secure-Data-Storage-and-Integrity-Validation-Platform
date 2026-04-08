"""Vercel serverless entrypoint for Flask app."""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app as flask_app  # noqa: E402

# Vercel/Python looks for `app`; keeping `handler` for compatibility.
app = flask_app
handler = app
