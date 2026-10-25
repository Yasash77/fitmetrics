"""Health check, API-key issuing and 24-Formula PDF Report Sheet generation."""
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from .. import config, report
from .. import schemas as s
from ..engine import body
from ..security import issue_key, limit_for, require_api_key

router = APIRouter()


@router.get("/health", tags=["System"], summary="Service status (public)")
def health():
    return {
        "success": True,
        "data": {
            "service": config.APP_NAME,
            "status": "up",
            "version": config.VERSION,
            "formulasEngine": 24,
        },
    }


@router.post("/keys", tags=["API Keys"], summary="Issue a free API key (public)", status_code=201)
def create_key(d: s.KeyRequest):
    return {"success": True, "data": issue_key(d.name, d.email)}


@router.get("/keys/me", tags=["API Keys"], summary="Details and usage of the calling key")
def my_key(info: dict = Depends(require_api_key)):
    k = info["key"]
    return {
        "success": True,
        "data": {
            "key": k[:6] + "…" + k[-4:] if len(k) > 10 else k,
            "name": info["name"],
            "tier": info["tier"],
            "rateLimitPerMin": limit_for(info["tier"]),
            "requests": info.get("requests"),
        },
    }


@router.post(
    "/reports/fitness-sheet",
    tags=["Reports"],
    summary="Download a 24-Formula Comprehensive Fitness Report Sheet (PDF)",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def fitness_report_pdf(d: s.FullAnalysisIn, _: dict = Depends(require_api_key)):
    payload = d.model_dump()
    if payload.get("sets"):
        payload["sets"] = [x.model_dump() if hasattr(x, "model_dump") else x for x in payload["sets"]]
    full = body.comprehensive_24_analysis(payload)
    pdf = report.fitness_sheet_pdf(full)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="fitpulse-24-formula-report.pdf"'},
    )
