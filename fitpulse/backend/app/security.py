"""API-key authentication, key issuing (SQLite) and per-key rate limiting."""
from __future__ import annotations
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, Response

from . import config

_lock = threading.Lock()
_hits = defaultdict(deque)


def _db():
    con = sqlite3.connect(config.KEY_DB_PATH, check_same_thread=False)
    con.execute("""CREATE TABLE IF NOT EXISTS api_keys(
        key TEXT PRIMARY KEY, name TEXT, email TEXT, tier TEXT,
        created REAL, requests INTEGER DEFAULT 0)""")
    return con


def issue_key(name: str, email: str) -> dict:
    key = "fp_" + secrets.token_hex(16)
    with _lock, _db() as con:
        con.execute(
            "INSERT INTO api_keys(key,name,email,tier,created) VALUES(?,?,?,?,?)",
            (key, name, email, "free", time.time()),
        )
    return {"apiKey": key, "name": name, "tier": "free", "rateLimitPerMin": config.RATE_LIMIT_PER_MIN}


def key_info(key: str) -> dict | None:
    if key == config.DEMO_API_KEY:
        return {"name": "Public demo (website)", "tier": "demo"}
    if key in config.PARTNER_API_KEYS:
        return {"name": "Partner service (FitMetrics 23MIC0060)", "tier": "partner"}
    with _db() as con:
        row = con.execute("SELECT name, tier, requests, created FROM api_keys WHERE key=?", (key,)).fetchone()
    if not row:
        return None
    return {"name": row[0], "tier": row[1], "requests": row[2], "created": row[3]}


def _count(key: str):
    with _lock, _db() as con:
        con.execute("UPDATE api_keys SET requests = requests + 1 WHERE key=?", (key,))


def limit_for(tier: str) -> int:
    return config.RATE_LIMIT_PER_MIN * {"partner": 5, "demo": 10}.get(tier, 1)


def require_api_key(request: Request, response: Response) -> dict:
    """FastAPI dependency: validates X-API-Key and applies a sliding-window rate limit."""
    key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if not config.REQUIRE_API_KEY:
        key = key or config.DEMO_API_KEY
    if not key:
        raise HTTPException(401, "missing API key — send it in the X-API-Key header")
    info = key_info(key)
    if info is None:
        raise HTTPException(401, "invalid API key")

    limit = limit_for(info["tier"])
    now = time.time()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            retry = int(60 - (now - q[0])) + 1
            raise HTTPException(429, f"rate limit of {limit} requests/min exceeded — retry in {retry}s")
        q.append(now)
        remaining = limit - len(q)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    if info["tier"] == "free":
        _count(key)
    return {"key": key, **info}


def optional_partner_key(request: Request, response: Response) -> dict:
    """Allows partner FitMetrics calls even when FITPULSE_API_KEY is not set, while still validating if provided."""
    key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if not key:
        return {"key": "partner_open", "name": "Partner / Public", "tier": "partner"}
    return require_api_key(request, response)
