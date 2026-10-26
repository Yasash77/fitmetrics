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


# ============================================================================================
# Used by the FitPulse user platform (server-side only; the key never reaches the browser).
# Only endpoints that exist in Maajith's FitPulse API are called, with their documented fields.
# ============================================================================================
class PartnerRejected(Exception):
    pass


async def _post(path: str, payload: dict) -> dict:
    if not config.FITPULSE_BASE_URL:
        raise PartnerUnavailable("not configured")
    headers = {"X-API-Key": config.FITPULSE_API_KEY} if config.FITPULSE_API_KEY else {}
    try:
        async with httpx.AsyncClient(timeout=config.FITPULSE_TIMEOUT) as client:
            r = await client.post(f"{config.FITPULSE_BASE_URL}{path}", json=payload, headers=headers)
    except Exception as exc:                            # network error / timeout
        raise PartnerUnavailable(type(exc).__name__) from exc
    if r.status_code in (400, 422):
        try:
            body = r.json()
            msg = body.get("error") or body.get("detail") or "rejected"
        except Exception:
            msg = "rejected"
        raise PartnerRejected(str(msg))
    if r.status_code >= 300:
        raise PartnerUnavailable(f"HTTP {r.status_code}")
    body = r.json()
    if not isinstance(body, dict) or body.get("success") is False:
        raise PartnerUnavailable("unexpected response")
    return body.get("data", body)


GOAL_TO_FITPULSE = {"fat_loss": "lose", "muscle_gain": "gain"}


async def energy_needs(age: int, sex: str, height_cm: float, weight_kg: float, activity: str,
                       primary_goal: str, body_fat: float | None) -> dict:
    """POST /fitness/calories — BMR, TDEE, goal calories and macros (Maajith's analysis)."""
    payload = {"age": age, "gender": sex, "height": height_cm, "weight": weight_kg, "activityLevel": activity,
               "goal": GOAL_TO_FITPULSE.get(primary_goal, "maintain")}
    if body_fat:
        payload["bodyFatPct"] = body_fat
    return await _post("/fitness/calories", payload)


async def goal_plan(age: int, sex: str, height_cm: float, weight_kg: float, activity: str,
                    target_kg: float, weeks: float) -> dict:
    """POST /fitness/goal-plan — weekly rate, calorie target and safety rating for a weight goal."""
    payload = {"age": age, "gender": sex, "height": height_cm, "weight": weight_kg, "activityLevel": activity,
               "targetWeight": target_kg, "weeks": weeks}
    return await _post("/fitness/goal-plan", payload)


async def health() -> str:
    if not config.FITPULSE_BASE_URL:
        return "not_configured"
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            r = await client.get(f"{config.FITPULSE_BASE_URL}/health")
        return "up" if r.status_code == 200 else "down"
    except Exception:
        return "down"
