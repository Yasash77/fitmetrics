"""
FitMetrics — Workout Performance & Training Analytics API  +  FitPulse user platform
Author : Yasash S (23MIC0060)

Two faces, one server:
  /api/v1/*   public FitMetrics API (API-key auth) — also used by Maajith's FitPulse API
  /api/*      FitPulse user platform (session-cookie auth): accounts, onboarding, plans, logging, progress
  /           the FitPulse website (frontend/index.html); the original API console lives at /tools.html

FitPulse (partner, 23MIC0052) answers  "how much energy does this person NEED?"
FitMetrics answers                      "what did this WORKOUT actually do?"

Run locally:  python run.py        → website http://localhost:8000 · API docs http://localhost:8000/docs
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, db
from . import security as sec
from .clients import fitpulse, processing
from .engine.workout import MetricError
from .routers import metrics, platform, system

app = FastAPI(
    title=config.APP_NAME,
    version=config.VERSION,
    description=("Workout performance & training analytics as a service. "
                 "Send your key in the `X-API-Key` header. Get a free key from `POST /api/v1/keys`."),
    contact={"name": "Yasash S · 23MIC0060"},
)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"],
                   allow_headers=["*"], expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"])

app.include_router(system.router, prefix=config.API_PREFIX)
app.include_router(metrics.router, prefix=config.API_PREFIX)
app.include_router(platform.router)

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
SITE_CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def platform_guard(request: Request, call_next):
    path = request.url.path
    is_platform_api = path.startswith("/api/") and not path.startswith(config.API_PREFIX + "/")
    # CSRF: state-changing platform calls must carry our custom header (impossible cross-site without a
    # credentialed CORS pre-flight, which this server never grants).
    if is_platform_api and request.method in UNSAFE and request.headers.get(sec.CSRF_HEADER, "").lower() != sec.CSRF_VALUE:
        return JSONResponse(status_code=403, content={"success": False, "error": "Missing CSRF header."})
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if is_platform_api:
        response.headers["Cache-Control"] = "no-store"
    elif path in ("/", "/index.html"):
        response.headers["Content-Security-Policy"] = SITE_CSP
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/api/health", tags=["FitPulse platform"])
def platform_health():
    return {"success": True, "data": {"service": config.PLATFORM_NAME, "version": config.PLATFORM_VERSION,
                                      "database": db.ping()}}


@app.get("/api/integrations/status", tags=["FitPulse platform"])
async def integrations():
    """Non-secret status flags so the UI can tell users honestly what is and isn't connected."""
    import os
    serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    return {"success": True, "data": {
        "planService": {"mode": processing.mode(), "contractVersion": processing.CONTRACT_VERSION},
        "fitpulse": {"status": await fitpulse.health(), "label": "FitPulse API (Maajith) — energy & goal analysis"},
        "fitmetrics": {"status": "up", "label": "FitMetrics engine (Yasash) — workout analysis, built in"},
        "database": {"kind": db.database_kind(), "durable": db.database_kind() == "postgres" or not serverless,
                     "up": db.ping()},
        "emailDelivery": platform.mail_configured(),
    }}


@app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def api_not_found(rest: str):
    return JSONResponse(status_code=404, content={"success": False, "error": "Unknown API endpoint."})


# ------------------------------------------------------------- error envelope
@app.exception_handler(MetricError)
async def metric_error(_: Request, exc: MetricError):
    return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.detail},
                        headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    fields = {d["field"] or "request": d["message"] for d in details}      # platform UI reads this map
    return JSONResponse(status_code=422, content={"success": False, "error": "validation failed", "details": details,
                                                  "fields": fields})


@app.exception_handler(Exception)
async def unexpected(request: Request, exc: Exception):
    import logging
    logging.getLogger("fitmetrics").exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"success": False, "error": "internal server error"})


# ------------------------------------------------------------- website
# The same server also serves the frontend, so http://localhost:8000 opens the site
# and the page calls the API on the same origin (no CORS / URL configuration needed).
if config.FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIR), html=True), name="website")
