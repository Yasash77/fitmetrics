"""HTTP client for the partner FitMetrics API (23MIC0060).

FitPulse does NOT compute workout metrics itself — calories burned, heart-rate zone,
training load and injury risk all come from FitMetrics."""
from __future__ import annotations

import asyncio

import httpx

from .. import config


class PartnerUnavailable(Exception):
    pass


def _headers() -> dict:
    return {"X-API-Key": config.FITMETRICS_API_KEY} if config.FITMETRICS_API_KEY else {}


async def _post(client: httpx.AsyncClient, path: str, payload: dict) -> dict:
    r = await client.post(f"{config.FITMETRICS_BASE_URL}{path}", json=payload, headers=_headers())
    if r.status_code in (400, 422):                     # partner rejected the input — surface its message
        body = r.json()
        raise ValueError(body.get("error") or body.get("detail") or "invalid workout data")
    r.raise_for_status()
    body = r.json()
    return body.get("data", body)


async def workout_analysis(payload: dict) -> dict:
    """POST /metrics/workout-analysis on FitMetrics."""
    try:
        async with httpx.AsyncClient(timeout=config.FITMETRICS_TIMEOUT) as client:
            return await _post(client, "/metrics/workout-analysis", payload)
    except ValueError:
        raise
    except Exception as exc:
        raise PartnerUnavailable(str(exc)) from exc


async def workout_analysis_many(payloads: list[dict]) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=config.FITMETRICS_TIMEOUT * 2) as client:
            return await asyncio.gather(*[_post(client, "/metrics/workout-analysis", p) for p in payloads])
    except ValueError:
        raise
    except Exception as exc:
        raise PartnerUnavailable(str(exc)) from exc


async def training_balance(daily_loads: list[float]) -> dict:
    """POST /metrics/training-balance on FitMetrics (ACWR injury risk)."""
    try:
        async with httpx.AsyncClient(timeout=config.FITMETRICS_TIMEOUT) as client:
            return await _post(client, "/metrics/training-balance", {"dailyLoads": daily_loads})
    except ValueError:
        raise
    except Exception as exc:
        raise PartnerUnavailable(str(exc)) from exc


# Backwards-compatible name used by earlier code
fetch_partner_workout = workout_analysis
