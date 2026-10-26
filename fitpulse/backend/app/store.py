"""Progress store (SQLite) — body measurements, logged workouts and goals per profile."""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager

from . import config

_lock = threading.Lock()


@contextmanager
def db():
    with _lock:
        con = sqlite3.connect(config.PROGRESS_DB_PATH)
        con.row_factory = sqlite3.Row
        try:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS measurements(
                    id INTEGER PRIMARY KEY, profile TEXT, date TEXT, weight REAL, waist REAL, body_fat REAL);
                CREATE TABLE IF NOT EXISTS workouts(
                    id INTEGER PRIMARY KEY, profile TEXT, date TEXT, activity TEXT, duration REAL, avg_hr INTEGER,
                    calories REAL, zone TEXT, intensity TEXT, load REAL, recovery_hours REAL);
                CREATE TABLE IF NOT EXISTS goals(
                    profile TEXT PRIMARY KEY, target_weight REAL, target_date TEXT, start_weight REAL, start_date TEXT);
            """)
            yield con
            con.commit()
        finally:
            con.close()


def add_measurement(profile, day, weight, waist=None, body_fat=None) -> int:
    with db() as con:
        cur = con.execute("INSERT INTO measurements(profile,date,weight,waist,body_fat) VALUES(?,?,?,?,?)",
                          (profile, day, weight, waist, body_fat))
        return cur.lastrowid


def measurements(profile) -> list[dict]:
    with db() as con:
        rows = con.execute("SELECT date, weight, waist, body_fat FROM measurements WHERE profile=? ORDER BY date, id",
                           (profile,)).fetchall()
    return [{"date": r["date"], "weight": r["weight"], "waist": r["waist"], "bodyFat": r["body_fat"]} for r in rows]


def add_workout(profile, day, activity, duration, avg_hr, a: dict) -> int:
    with db() as con:
        cur = con.execute(
            "INSERT INTO workouts(profile,date,activity,duration,avg_hr,calories,zone,intensity,load,recovery_hours)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (profile, day, activity, duration, avg_hr, a.get("caloriesBurned"), a.get("zone"), a.get("intensity"),
             a.get("trainingLoad"), a.get("recoveryHours")))
        return cur.lastrowid


def workouts(profile) -> list[dict]:
    with db() as con:
        rows = con.execute("SELECT * FROM workouts WHERE profile=? ORDER BY date, id", (profile,)).fetchall()
    return [{"date": r["date"], "activity": r["activity"], "duration": r["duration"], "avgHr": r["avg_hr"],
             "caloriesBurned": r["calories"], "zone": r["zone"], "intensity": r["intensity"],
             "trainingLoad": r["load"], "recoveryHours": r["recovery_hours"]} for r in rows]


def set_goal(profile, target_weight, target_date, start_weight, start_date):
    with db() as con:
        con.execute("INSERT OR REPLACE INTO goals VALUES(?,?,?,?,?)",
                    (profile, target_weight, target_date, start_weight, start_date))


def goal(profile) -> dict | None:
    with db() as con:
        r = con.execute("SELECT * FROM goals WHERE profile=?", (profile,)).fetchone()
    if not r:
        return None
    return {"targetWeight": r["target_weight"], "targetDate": r["target_date"],
            "startWeight": r["start_weight"], "startDate": r["start_date"]}


def reset(profile):
    with db() as con:
        for t in ("measurements", "workouts", "goals"):
            con.execute(f"DELETE FROM {t} WHERE profile=?", (profile,))
