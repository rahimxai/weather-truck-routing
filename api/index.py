import os
import sys
from pathlib import Path

# Vercel entry point: put backend/ on the path, then expose Django's WSGI app.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.wsgi import application as app  # noqa: E402, F401
