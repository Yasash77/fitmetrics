"""
FitPulse — 24-Formula Fitness Intelligence & Personal Metrics API
Author : Majit (23MIC0052) · Partner Project: FitMetrics (Yasash S, 23MIC0060)

Run locally:  python run.py  → website http://localhost:8000 · API docs http://localhost:8000/docs
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .engine.metabolic import MetricError
from .routers import fitness, system

app = FastAPI(
    title=config.APP_NAME,
    version=config.VERSION,
    description=(
        "24-Formula Fitness Intelligence, Metabolic, Cardio, Strength, Load & Body Composition Analytics API. "
        "Send your key in the `X-API-Key` header. Get a free key from `POST /api/v1/keys`."
    ),
    contact={"name": "Majit · 23MIC0052"},
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

app.include_router(system.router, prefix=config.API_PREFIX)
app.include_router(fitness.router, prefix=config.API_PREFIX)


@app.exception_handler(MetricError)
async def metric_error(_: Request, exc: MetricError):
    return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"success": False, "error": "validation failed", "details": details})


@app.exception_handler(Exception)
async def unexpected(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"success": False, "error": "internal server error"})


if config.FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIR), html=True), name="website")
