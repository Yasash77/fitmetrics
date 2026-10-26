"""Vercel entry point — exposes the FastAPI app (API + website) as a serverless function."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("KEY_DB_PATH", "/tmp/fitmetrics_keys.db")   # only /tmp is writable on Vercel
os.environ.setdefault("SQLITE_PATH", "/tmp/fitpulse_platform.db")   # fallback only — set DATABASE_URL for Postgres
os.environ.setdefault("FRONTEND_DIR", str(ROOT / "frontend"))

from app.main import app  # noqa: E402,F401
