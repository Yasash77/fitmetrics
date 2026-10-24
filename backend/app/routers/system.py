"""Health check, API-key issuing and PDF reports."""
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from .. import config, report
from .. import schemas as s
from ..engine import strength, workout
from ..security import issue_key, limit_for, require_api_key

router = APIRouter()


@router.get("/health", tags=["System"], summary="Service status (public)")
def health():
    return {"success": True, "data": {"service": config.APP_NAME, "status": "up", "version": config.VERSION}}


@router.post("/keys", tags=["API Keys"], summary="Issue a free API key (public)", status_code=201)
def create_key(d: s.KeyRequest):
    return {"success": True, "data": issue_key(d.name, d.email)}


@router.get("/keys/me", tags=["API Keys"], summary="Details and usage of the calling key")
def my_key(info: dict = Depends(require_api_key)):
    k = info["key"]
    return {"success": True, "data": {"key": k[:6] + "…" + k[-4:], "name": info["name"], "tier": info["tier"],
                                      "rateLimitPerMin": limit_for(info["tier"]),
                                      "requests": info.get("requests")}}


@router.post("/reports/workout", tags=["Reports"], summary="Download a PDF workout report",
             response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def workout_report(d: s.WorkoutReportIn, _: dict = Depends(require_api_key)):
    analysis = workout.analyse(d.activity, d.duration, d.weight, d.age, d.restingHr, d.avgHr, d.gender, d.climate)
    zones = workout.hr_zones(d.age, d.restingHr)
    lift = strength.analyse_lift(d.strength.exercise, d.strength.weight, d.strength.reps,
                                 d.strength.bodyweight or d.weight) if d.strength else None
    pdf = report.workout_pdf(d.athlete, analysis, zones, lift)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="fitmetrics-workout-report.pdf"'})
