"""Processing-system adapter — the single boundary between this platform and Maajith's processing system.

The platform COLLECTS and PRESENTS data; Maajith's system ANALYSES it and returns the personalised plan.
UI code never generates plans: it calls /api/plans, which calls this adapter.

Modes (config.plan_mode()):
  live          PLAN_SERVICE_URL is set -> HTTP calls described in docs/PLAN_API_CONTRACT.md
  mock          PLAN_SERVICE_MODE=mock  -> clients/mock_processing.py, an isolated development placeholder.
                Every mock plan is stamped generatedBy.isMock = true and the UI shows a banner.
  unconfigured  neither                 -> ProcessingUnavailable (HTTP 503 to the browser). Nothing is faked.

Method names follow the integration brief: submit_fitness_profile, request_personalized_plan,
get_personalized_plan, log_workout, get_progress."""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Optional

import httpx
from pydantic import ValidationError

from .. import config, onboarding
from ..schemas import PlanResponse
from . import mock_processing

CONTRACT_VERSION = "0.1"


class ProcessingUnavailable(Exception):
    """The processing system is not configured or not reachable."""


class ProcessingRejected(Exception):
    """The processing system refused the request (bad input)."""


class ProcessingInvalidResponse(Exception):
    """The processing system answered with something that does not match the contract."""


# ------------------------------------------------------------------ payload
def pseudonymous_ref(user_id: str) -> str:
    """Stable reference that lets the processing system group requests without receiving the e-mail or name."""
    return hashlib.sha256(f"fitpulse-platform:{user_id}".encode()).hexdigest()[:24]


def build_payload(request_id: str, user_id: str, profile: dict, energy: Optional[dict]) -> dict:
    """Structured, minimal payload: only what is needed to plan training (no name, e-mail or birth date)."""
    dob = profile.get("dateOfBirth")
    age = onboarding.age_from_dob(date.fromisoformat(dob)) if dob else None
    disc_answers = profile.get("disciplineDetails") or {}
    return {
        "contractVersion": CONTRACT_VERSION,
        "requestId": request_id,
        "client": {"system": "fitpulse-platform", "version": config.PLATFORM_VERSION},
        "user": {"ref": pseudonymous_ref(user_id)},
        "athlete": {"ageYears": age, "sex": profile.get("sex"), "heightCm": profile.get("heightCm"),
                    "weightKg": profile.get("weightKg"), "bodyFatPct": profile.get("bodyFatPct"),
                    "restingHr": profile.get("restingHr"), "activityLevel": profile.get("activityLevel")},
        "goals": {"primary": profile.get("primaryGoal"), "secondary": profile.get("secondaryGoals") or [],
                  "targetWeightKg": profile.get("targetWeightKg"), "targetEvent": profile.get("targetEvent"),
                  "notes": profile.get("goalNotes")},
        "timeline": {"weeks": onboarding.programme_weeks(profile), "targetDate": profile.get("targetDate"),
                     "startDate": date.today().isoformat()},
        "experience": {"level": profile.get("experienceLevel"), "breakMonths": profile.get("breakMonths")},
        "disciplines": [{"id": d, "answers": disc_answers.get(d, {})} for d in profile.get("disciplines") or []],
        "availability": {"daysPerWeek": profile.get("daysPerWeek"), "preferredDays": profile.get("preferredDays") or [],
                         "sessionMinutes": int(profile["sessionMinutes"]) if profile.get("sessionMinutes") else None,
                         "timeOfDay": profile.get("timeOfDay")},
        "equipment": {"locations": profile.get("locations") or [], "items": profile.get("equipment") or [],
                      "poolLength": profile.get("poolLength")},
        "constraints": {"healthCheck": profile.get("healthCheck"), "injuries": profile.get("injuries"),
                        "avoidMovements": profile.get("avoidMovements") or [],
                        "intensityPreference": profile.get("intensityPreference"), "enjoys": profile.get("enjoys")},
        "context": {"energy": energy},
    }


# ------------------------------------------------------------------ live HTTP
def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if config.PLAN_SERVICE_KEY:
        h["X-API-Key"] = config.PLAN_SERVICE_KEY
    return h


async def _live(method: str, path: str, payload: Optional[dict] = None) -> dict:
    try:
        async with httpx.AsyncClient(timeout=config.PLAN_SERVICE_TIMEOUT) as client:
            r = await client.request(method, f"{config.PLAN_SERVICE_URL}{path}", json=payload, headers=_headers())
    except Exception as exc:
        raise ProcessingUnavailable(f"Processing system unreachable ({type(exc).__name__}).") from exc
    if r.status_code in (400, 422):
        raise ProcessingRejected(_error_text(r))
    if r.status_code == 404:
        raise ProcessingRejected("Processing system does not know this plan (404).")
    if r.status_code >= 300:
        raise ProcessingUnavailable(f"Processing system returned HTTP {r.status_code}.")
    try:
        return r.json()
    except ValueError as exc:
        raise ProcessingInvalidResponse("Processing system returned non-JSON content.") from exc


def _error_text(r: httpx.Response) -> str:
    try:
        b = r.json()
        return str(b.get("error") or b.get("detail") or b)[:300]
    except Exception:
        return f"HTTP {r.status_code}"


def _validate(body: dict) -> dict:
    data = body.get("data", body) if isinstance(body, dict) else body
    try:
        plan = PlanResponse.model_validate(data)
    except ValidationError as exc:
        raise ProcessingInvalidResponse(f"Plan did not match contract v{CONTRACT_VERSION}: "
                                        f"{exc.errors()[0]['loc']} {exc.errors()[0]['msg']}") from exc
    if plan.status == "ready" and (not plan.weeks or plan.summary is None):
        raise ProcessingInvalidResponse("Plan marked ready but contains no weeks/summary.")
    if config.plan_mode() == "live" and plan.generatedBy.isMock:
        raise ProcessingInvalidResponse("Live processing system returned a plan flagged as mock.")
    return plan.model_dump(exclude_none=True)


# ------------------------------------------------------------------ public adapter API
def mode() -> str:
    return config.plan_mode()


async def submit_fitness_profile(payload: dict) -> dict:
    """Send the structured profile. In contract v0.1 the profile travels inside the plan request,
    so this is the same call as request_personalized_plan (kept as a separate name for clarity)."""
    return await request_personalized_plan(payload)


async def request_personalized_plan(payload: dict) -> dict:
    m = mode()
    if m == "live":
        return _validate(await _live("POST", "/plans", payload))
    if m == "mock":
        return _validate(mock_processing.generate(payload))
    raise ProcessingUnavailable("Plan generation is not connected on this deployment yet: Maajith's processing "
                                "system URL is not configured (PLAN_SERVICE_URL).")


async def get_personalized_plan(external_id: str) -> dict:
    m = mode()
    if m == "live":
        return _validate(await _live("GET", f"/plans/{external_id}"))
    if m == "mock":
        raise ProcessingRejected("Development mock plans are generated synchronously and cannot be re-fetched.")
    raise ProcessingUnavailable("Processing system not configured.")


async def log_workout(external_plan_id: str, feedback: dict) -> str:
    """Forward completed-session feedback so the processing system can adapt future plans.
    Returns 'forwarded', 'not_supported' or 'local_only'. Workouts are always stored locally first."""
    if mode() != "live" or not external_plan_id:
        return "local_only"
    try:
        await _live("POST", f"/plans/{external_plan_id}/feedback", feedback)
        return "forwarded"
    except ProcessingRejected:
        return "not_supported"
    except (ProcessingUnavailable, ProcessingInvalidResponse):
        return "failed"


async def get_progress(local_summary: dict) -> dict:
    """Progress is computed from the user's own logged data in this platform (plus FitMetrics analysis).
    Contract v0.1 defines no processing-side progress endpoint, so nothing is requested remotely."""
    return {"source": "platform", **local_summary}
