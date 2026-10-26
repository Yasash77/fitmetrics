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
FITPULSE_BASE_URL = os.getenv("FITPULSE_BASE_URL", "https://fitpulse-steel.vercel.app/api/v1").strip().rstrip("/")
FITPULSE_API_KEY = os.getenv("FITPULSE_API_KEY", "")          # sent if the partner requires a key
FITPULSE_TIMEOUT = float(os.getenv("FITPULSE_TIMEOUT", "8"))

# Security
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"
DEMO_API_KEY = os.getenv("DEMO_API_KEY", "fm_demo_public_key")   # used by the public website
PARTNER_API_KEYS = [k.strip() for k in os.getenv("PARTNER_API_KEYS", "fm_partner_23mic0052").split(",") if k.strip()]
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
KEY_DB_PATH = os.getenv("KEY_DB_PATH", str(BACKEND_DIR / "fitmetrics_keys.db"))

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ============================================================================================
# FitPulse user platform (accounts, onboarding, plans, workout logging, progress)
# The user-facing app collects the data; Maajith's processing system analyses it and returns plans.
# ============================================================================================
PLATFORM_NAME = "FitPulse"
PLATFORM_VERSION = "1.0.0"
ONBOARDING_CONFIG = Path(__file__).resolve().parent / "onboarding_config.json"
# ------------------------------------------------------------------ database
# Postgres in production (e.g. Neon / Vercel Postgres): set DATABASE_URL.
# Without it the app falls back to a local SQLite file (fine for development; on serverless hosts
# the file lives in /tmp and is NOT durable — the UI says so).
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SQLITE_PATH = os.getenv("SQLITE_PATH", str(BACKEND_DIR / "platform.db"))

# ------------------------------------------------------------------ sessions & auth
SESSION_COOKIE = "fp_session"
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "14"))
# "auto" = Secure flag whenever the request arrived over https (always true on Vercel)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "auto").lower()
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
LOGIN_WINDOW_MIN = int(os.getenv("LOGIN_WINDOW_MIN", "15"))
RESET_TOKEN_MIN = int(os.getenv("RESET_TOKEN_MIN", "30"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")

# Password-reset e-mail delivery (optional). Without SMTP the reset endpoint still works, but the UI
# tells the user honestly that e-mail delivery is not configured on this deployment.
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER).strip()
# Local development only: return the reset link in the API response instead of e-mailing it.
DEV_SHOW_RESET_LINK = os.getenv("DEV_SHOW_RESET_LINK", "false").lower() == "true"

# ------------------------------------------------------------------ processing system (Maajith)
# Plan generation belongs to Maajith's processing system. Modes:
#   PLAN_SERVICE_URL set           -> "live": POST the profile to his plan endpoint (docs/PLAN_API_CONTRACT.md)
#   PLAN_SERVICE_MODE=mock         -> "mock": isolated development placeholder, labelled everywhere
#   neither                        -> "unconfigured": plan generation returns an honest 503
PLAN_SERVICE_URL = os.getenv("PLAN_SERVICE_URL", "").strip().rstrip("/")
PLAN_SERVICE_KEY = os.getenv("PLAN_SERVICE_KEY", "")
PLAN_SERVICE_MODE = os.getenv("PLAN_SERVICE_MODE", "").strip().lower()
PLAN_SERVICE_TIMEOUT = float(os.getenv("PLAN_SERVICE_TIMEOUT", "20"))



def plan_mode() -> str:
    if PLAN_SERVICE_URL:
        return "live"
    if PLAN_SERVICE_MODE == "mock":
        return "mock"
    return "unconfigured"

