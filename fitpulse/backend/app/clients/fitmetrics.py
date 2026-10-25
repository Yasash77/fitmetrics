"""HTTP client for the partner FitMetrics API (23MIC0060)."""
from __future__ import annotations
import httpx
from .. import config


class PartnerUnavailable(Exception):
    pass


async def fetch_partner_workout(payload: dict) -> dict:
    """POST /metrics/workout-analysis on FitMetrics partner API."""
    headers = {"X-API-Key": config.FITMETRICS_API_KEY} if config.FITMETRICS_API_KEY else {}
    try:
        async with httpx.AsyncClient(timeout=config.FITMETRICS_TIMEOUT) as client:
            r = await client.post(f"{config.FITMETRICS_BASE_URL}/metrics/workout-analysis", json=payload, headers=headers)
            r.raise_for_status()
            body = r.json()
            return body.get("data", body)
    except Exception as exc:
        raise PartnerUnavailable(str(exc)) from exc
