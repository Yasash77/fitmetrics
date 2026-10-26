"""Vercel entry point — exposes the FitPulse FastAPI app (API + website) as a serverless function."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("KEY_DB_PATH", "/tmp/fitpulse_keys.db")            # only /tmp is writable on Vercel
os.environ.setdefault("PROGRESS_DB_PATH", "/tmp/fitpulse_progress.db")
os.environ.setdefault("FRONTEND_DIR", str(ROOT / "frontend"))

from app.main import app  # noqa: E402,F401
