"""Security for both faces of the app.

1. Public FitMetrics API: API-key authentication, key issuing (SQLite) and per-key rate limiting.
2. FitPulse user platform: scrypt password hashing, httpOnly session cookies (only the token's SHA-256
   is stored), a CSRF header on every state-changing /api request, and database-backed login throttling."""
from __future__ import annotations
import base64
import hashlib
import hmac
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Request, Response

from . import config, db

_lock = threading.Lock()
_hits = defaultdict(deque)


# ------------------------------------------------------------------ key store
def _db():
    con = sqlite3.connect(config.KEY_DB_PATH, check_same_thread=False)
    con.execute("""CREATE TABLE IF NOT EXISTS api_keys(
        key TEXT PRIMARY KEY, name TEXT, email TEXT, tier TEXT,
        created REAL, requests INTEGER DEFAULT 0)""")
    return con


def issue_key(name: str, email: str) -> dict:
    key = "fm_" + secrets.token_hex(16)
    with _lock, _db() as con:
        con.execute("INSERT INTO api_keys(key,name,email,tier,created) VALUES(?,?,?,?,?)",
                    (key, name, email, "free", time.time()))
    return {"apiKey": key, "name": name, "tier": "free", "rateLimitPerMin": config.RATE_LIMIT_PER_MIN}


def key_info(key: str) -> dict | None:
    if key == config.DEMO_API_KEY:
        return {"name": "Public demo (website)", "tier": "demo"}
    if key in config.PARTNER_API_KEYS:
        return {"name": "Partner service (23MIC0052)", "tier": "partner"}
    with _db() as con:
        row = con.execute("SELECT name, tier, requests, created FROM api_keys WHERE key=?", (key,)).fetchone()
    if not row:
        return None
    return {"name": row[0], "tier": row[1], "requests": row[2], "created": row[3]}


def _count(key: str):
    with _lock, _db() as con:
        con.execute("UPDATE api_keys SET requests = requests + 1 WHERE key=?", (key,))


# --------------------------------------------------------------- dependency
def limit_for(tier: str) -> int:
    # The website itself makes ~25 calls when a page loads, so the shared demo key gets a bigger budget.
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


# ============================================================================================
# FitPulse user platform — passwords, sessions, brute-force protection
# ============================================================================================
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
MIN_PASSWORD = 10
CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "fitpulse"


# ------------------------------------------------------------------ passwords
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return "scrypt${}${}${}${}${}".format(SCRYPT_N, SCRYPT_R, SCRYPT_P,
                                          base64.b64encode(salt).decode(), base64.b64encode(dk).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, dk_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        dk = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64), n=int(n), r=int(r), p=int(p),
                            dklen=len(base64.b64decode(dk_b64)))
        return hmac.compare_digest(dk, base64.b64decode(dk_b64))
    except Exception:
        return False


_DUMMY_HASH = None


def burn_time(password: str) -> None:
    """Spend the same time as a real check so response timing does not reveal whether an e-mail exists."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("timing-equaliser")
    verify_password(password, _DUMMY_HASH)


def password_problem(password: str, email: str = "") -> Optional[str]:
    if len(password) < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters."
    if len(password) > 200:
        return "Password is too long."
    if password.lower() in {"password123", "qwertyuiop", "1234567890", "password1234"}:
        return "That password is too common."
    if email and password.lower() == email.lower():
        return "Password must not be your e-mail address."
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        return "Include at least one letter and one number."
    return None


# ------------------------------------------------------------------ tokens & sessions
def sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _utc(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str)


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    exp = datetime.now(timezone.utc) + timedelta(days=config.SESSION_DAYS)
    db.run("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (:t, :u, :c, :e)",
           t=sha256(token), u=user_id, c=db.now(), e=exp.isoformat(timespec="seconds"))
    return token


def set_session_cookie(request: Request, response: Response, token: str) -> None:
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    if config.COOKIE_SECURE in ("true", "1"):
        secure = True
    elif config.COOKIE_SECURE in ("false", "0"):
        secure = False
    response.set_cookie(config.SESSION_COOKIE, token, max_age=config.SESSION_DAYS * 86400, httponly=True,
                        secure=secure, samesite="lax", path="/")


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(config.SESSION_COOKIE, path="/")


def destroy_session(token: Optional[str]) -> None:
    if token:
        db.run("DELETE FROM sessions WHERE token_hash = :t", t=sha256(token))


def destroy_all_sessions(user_id: str) -> None:
    db.run("DELETE FROM sessions WHERE user_id = :u", u=user_id)


def session_user(request: Request) -> Optional[dict]:
    token = request.cookies.get(config.SESSION_COOKIE)
    if not token:
        return None
    row = db.one("SELECT u.id, u.email, u.name, u.created_at, s.expires_at FROM sessions s "
                 "JOIN users u ON u.id = s.user_id WHERE s.token_hash = :t", t=sha256(token))
    if not row:
        return None
    if _utc(row["expires_at"]) < datetime.now(timezone.utc):
        destroy_session(token)
        return None
    return {"id": row["id"], "email": row["email"], "name": row["name"], "createdAt": row["created_at"]}


def current_user(request: Request) -> dict:
    """FastAPI dependency: the signed-in user, from the session cookie only."""
    user = session_user(request)
    if not user:
        raise HTTPException(401, "Please sign in to continue.")
    return user


# ------------------------------------------------------------------ brute-force protection
def _attempt_keys(request: Request, email: str) -> list:
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
    return [f"email:{email.lower()}", f"ip:{ip}"]


def login_blocked(request: Request, email: str) -> bool:
    since = (datetime.now(timezone.utc) - timedelta(minutes=config.LOGIN_WINDOW_MIN)).isoformat(timespec="seconds")
    for key in _attempt_keys(request, email):
        limit = config.LOGIN_MAX_FAILURES if key.startswith("email:") else config.LOGIN_MAX_FAILURES * 4
        row = db.one("SELECT COUNT(*) AS n FROM login_attempts WHERE attempt_key = :k AND at >= :s", k=key, s=since)
        if row and row["n"] >= limit:
            return True
    return False


def record_failure(request: Request, email: str) -> None:
    for key in _attempt_keys(request, email):
        db.run("INSERT INTO login_attempts (id, attempt_key, at) VALUES (:i, :k, :a)", i=db.new_id(), k=key, a=db.now())


def clear_failures(request: Request, email: str) -> None:
    db.run("DELETE FROM login_attempts WHERE attempt_key = :k", k=f"email:{email.lower()}")
