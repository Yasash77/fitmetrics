"""Health check, API-key issuing and PDF profile report."""
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from .. import config, report
from .. import schemas as s
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


@router.post("/reports/profile", tags=["Reports"], summary="Download a PDF profile & progress report",
             response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def profile_report_pdf(d: s.ProfileReportIn, _: dict = Depends(require_api_key)):
    from .fitness import build_profile_report
    pdf = report.profile_pdf(build_profile_report(d))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="fitpulse-profile-report.pdf"'})
