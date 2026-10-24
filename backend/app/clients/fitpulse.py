"""HTTP client for the partner FitPulse API (23MIC0052)."""
from __future__ import annotations
import httpx

from .. import config


class PartnerUnavailable(Exception):
    pass


async def maintenance_calories(age: int, gender: str, height: float, weight: float, activity_level: str) -> float:
    """POST /fitness/calories on FitPulse. FitMetrics never computes this itself."""
    payload = {"age": age, "gender": gender, "height": height, "weight": weight, "activityLevel": activity_level}
    headers = {"X-API-Key": config.FITPULSE_API_KEY} if config.FITPULSE_API_KEY else {}
    try:
        async with httpx.AsyncClient(timeout=config.FITPULSE_TIMEOUT) as client:
            r = await client.post(f"{config.FITPULSE_BASE_URL}/fitness/calories", json=payload, headers=headers)
            r.raise_for_status()
            body = r.json()
            body = body.get("data", body)              # accept both {data:{...}} and flat responses
            return float(body["dailyCalories"])
    except Exception as exc:                            # network error, timeout, bad status, bad shape
        raise PartnerUnavailable(str(exc)) from exc
