"""Runtime configuration — everything can be overridden with environment variables."""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", BACKEND_DIR.parent / "frontend"))

APP_NAME = "FitPulse API"
VERSION = "3.0.0"
API_PREFIX = "/api/v1"

# Partner service (FitMetrics, 23MIC0060 - Yasash S)
FITMETRICS_BASE_URL = os.getenv("FITMETRICS_BASE_URL", "https://fitmetrics-api.onrender.com/api/v1")
FITMETRICS_API_KEY = os.getenv("FITMETRICS_API_KEY", "fm_partner_23mic0052")
FITMETRICS_TIMEOUT = float(os.getenv("FITMETRICS_TIMEOUT", "8"))

# Security
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"
DEMO_API_KEY = os.getenv("DEMO_API_KEY", "fp_demo_public_key")
PARTNER_API_KEYS = [
    k.strip()
    for k in os.getenv("PARTNER_API_KEYS", "fp_partner_23mic0060,fm_partner_23mic0052,fm_demo_public_key").split(",")
    if k.strip()
]
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
KEY_DB_PATH = os.getenv("KEY_DB_PATH", str(BACKEND_DIR / "fitpulse_keys.db"))

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
