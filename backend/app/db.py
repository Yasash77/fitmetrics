"""Database layer — SQLAlchemy Core with plain SQL that runs on both Postgres and SQLite.

Every query that touches private data takes the user id from the server-side session, never
from the request body, so one user can never read or change another user's rows."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from . import config

_engine: Optional[Engine] = None


def database_url() -> str:
    url = config.DATABASE_URL
    if not url:
        return f"sqlite:///{config.SQLITE_PATH}"
    # Neon / Vercel / Heroku style URLs -> psycopg 3 driver
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def database_kind() -> str:
    if not config.DATABASE_URL:
        return "sqlite"
    return "postgres"


def engine() -> Engine:
    global _engine
    if _engine is None:
        url = database_url()
        if url.startswith("sqlite"):
            _engine = create_engine(url, connect_args={"check_same_thread": False})
            event.listen(_engine, "connect", lambda con, _rec: con.execute("PRAGMA foreign_keys=ON"))
        else:
            # Serverless + Neon's pooled endpoint (PgBouncer, transaction mode): no client-side pool and no
            # server-side prepared statements, which transaction pooling does not support.
            _engine = create_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None})
        init_schema(_engine)
    return _engine


def reset_engine() -> None:
    """Used by tests to point at a fresh database."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        password_changed_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS reset_tokens (
        token_hash TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        expires_at TEXT NOT NULL,
        used INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS login_attempts (
        id TEXT PRIMARY KEY,
        attempt_key TEXT NOT NULL,
        at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS profiles (
        user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        data TEXT NOT NULL,
        onboarding_complete INTEGER NOT NULL DEFAULT 0,
        version INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS plans (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        idempotency_key TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        source TEXT NOT NULL,
        status TEXT NOT NULL,
        external_id TEXT,
        profile_version INTEGER NOT NULL,
        request TEXT NOT NULL,
        response TEXT,
        energy TEXT,
        error TEXT,
        UNIQUE (user_id, idempotency_key)
    )""",
    """CREATE TABLE IF NOT EXISTS workout_logs (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        client_id TEXT NOT NULL,
        logged_at TEXT NOT NULL,
        date TEXT NOT NULL,
        discipline TEXT NOT NULL,
        title TEXT NOT NULL,
        duration_min REAL NOT NULL,
        rpe INTEGER,
        avg_hr INTEGER,
        notes TEXT,
        details TEXT NOT NULL,
        plan_id TEXT,
        session_id TEXT,
        analysis TEXT,
        analysis_status TEXT NOT NULL,
        UNIQUE (user_id, client_id)
    )""",
    """CREATE TABLE IF NOT EXISTS measurements (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        weight REAL,
        waist REAL,
        body_fat REAL,
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS ix_sessions_user ON sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_plans_user ON plans(user_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_workouts_user ON workout_logs(user_id, date)",
    "CREATE INDEX IF NOT EXISTS ix_meas_user ON measurements(user_id, date)",
    "CREATE INDEX IF NOT EXISTS ix_login_key ON login_attempts(attempt_key, at)",
]


def init_schema(eng: Engine) -> None:
    with eng.begin() as c:
        for stmt in SCHEMA:
            c.execute(text(stmt))


# ------------------------------------------------------------------ helpers
def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex


def dumps(v: Any) -> Optional[str]:
    return None if v is None else json.dumps(v, separators=(",", ":"))


def loads(v: Optional[str]) -> Any:
    return None if v in (None, "") else json.loads(v)


def run(sql: str, **params) -> None:
    with engine().begin() as c:
        c.execute(text(sql), params)


def one(sql: str, **params) -> Optional[dict]:
    with engine().connect() as c:
        row = c.execute(text(sql), params).mappings().first()
        return dict(row) if row else None


def all_rows(sql: str, **params) -> list:
    with engine().connect() as c:
        return [dict(r) for r in c.execute(text(sql), params).mappings().all()]


def ping() -> bool:
    try:
        with engine().connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
