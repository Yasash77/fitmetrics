"""Runtime configuration — everything can be overridden with environment variables."""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", BACKEND_DIR.parent / "frontend"))

APP_NAME = "FitMetrics API"
VERSION = "3.0.0"
API_PREFIX = "/api/v1"

# Partner service (FitPulse, 23MIC0052)
# Set this to Maajith's deployed FitPulse URL. run.py points it at the local stand-in (fitpulse_stub.py).
FITPULSE_BASE_URL = os.getenv("FITPULSE_BASE_URL", "https://fitpulse-api.onrender.com/api/v1").strip().rstrip("/")
FITPULSE_API_KEY = os.getenv("FITPULSE_API_KEY", "")          # sent if the partner requires a key
FITPULSE_TIMEOUT = float(os.getenv("FITPULSE_TIMEOUT", "8"))

# Security
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"
DEMO_API_KEY = os.getenv("DEMO_API_KEY", "fm_demo_public_key")   # used by the public website
PARTNER_API_KEYS = [k.strip() for k in os.getenv("PARTNER_API_KEYS", "fm_partner_23mic0052").split(",") if k.strip()]
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
KEY_DB_PATH = os.getenv("KEY_DB_PATH", str(BACKEND_DIR / "fitmetrics_keys.db"))

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
