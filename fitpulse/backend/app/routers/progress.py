"""/api/v1/progress/* — the Progress Management System.

Stores body measurements, goals and workouts per profile. Every workout is analysed by the
partner FitMetrics API before it is saved, and injury risk is computed by FitMetrics from the log."""
from __future__ import annotations

import random
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import schemas as s
from .. import store
from ..clients import fitmetrics
from ..engine.metabolic import MetricError
from ..security import require_api_key

router = APIRouter(prefix="/progress", tags=["Progress tracking"], dependencies=[Depends(require_api_key)])
PROFILE_Q = Query("demo", min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_\-]+$")


def ok(data):
    return {"success": True, "data": data}


def _day(d: str | None) -> str:
    if d is None:
        return date.today().isoformat()
    try:
        day = date.fromisoformat(d)
    except ValueError:
        raise MetricError("date must be a real date in YYYY-MM-DD format")
    if day > date.today():
        raise MetricError("date cannot be in the future")
    return day.isoformat()


def _slope_per_week(points: list[tuple[date, float]]) -> float | None:
    """Least-squares trend of weight vs time, in kg per week."""
    if len(points) < 2:
        return None
    xs = [(p[0] - points[0][0]).days for p in points]
    ys = [p[1] for p in points]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den * 7


# ------------------------------------------------------------------ measurements & goal
@router.post("/measurements", summary="Log a body measurement (weight, waist, body fat)", status_code=201)
def add_measurement(d: s.MeasurementIn):
    day = _day(d.date)
    store.add_measurement(d.profile, day, d.weight, d.waist, d.bodyFat)
    return ok({"profile": d.profile, "date": day, "weight": d.weight, "waist": d.waist, "bodyFat": d.bodyFat})


@router.post("/goal", summary="Set a target weight and date")
def set_goal(d: s.GoalIn):
    target = date.fromisoformat(d.targetDate)
    if target <= date.today():
        raise MetricError("targetDate must be in the future")
    ms = store.measurements(d.profile)
    if not ms:
        raise MetricError("log at least one measurement before setting a goal")
    store.set_goal(d.profile, d.targetWeight, d.targetDate, ms[-1]["weight"], ms[-1]["date"])
    return ok(store.goal(d.profile))


@router.get("/summary", summary="Weight trend, weekly rate and goal progress")
def summary(profile: str = PROFILE_Q):
    ms = store.measurements(profile)
    g = store.goal(profile)
    if not ms:
        return ok({"profile": profile, "measurements": [], "count": 0, "goal": g})
    first, last = ms[0], ms[-1]
    rate = _slope_per_week([(date.fromisoformat(m["date"]), m["weight"]) for m in ms])
    out = {"profile": profile, "count": len(ms), "measurements": ms,
           "startWeight": first["weight"], "currentWeight": last["weight"],
           "totalChangeKg": round(last["weight"] - first["weight"], 1),
           "weeklyRateKg": round(rate, 2) if rate is not None else None,
           "since": first["date"], "lastLogged": last["date"], "goal": g}
    if g:
        remaining = round(g["targetWeight"] - last["weight"], 1)
        total = g["targetWeight"] - g["startWeight"]
        done = (last["weight"] - g["startWeight"]) / total * 100 if total else 100
        weeks_left = max((date.fromisoformat(g["targetDate"]) - date.today()).days / 7, 0.1)
        needed = remaining / weeks_left
        if remaining == 0:
            on_track = True
        elif rate is None:
            on_track = False
        else:
            on_track = rate * needed > 0 and abs(rate) >= 0.8 * abs(needed)
        eta = None
        if rate and remaining and (remaining / rate) > 0:
            eta = (date.today() + timedelta(weeks=remaining / rate)).isoformat()
        out["goalProgress"] = {"remainingKg": remaining, "percentComplete": round(max(0, min(100, done)), 1),
                               "requiredWeeklyRateKg": round(needed, 2), "onTrack": bool(on_track),
                               "projectedDate": eta}
    return ok(out)


# ------------------------------------------------------------------ workouts (analysed by FitMetrics)
def _payload(d) -> dict:
    return {"activity": d.activity, "duration": d.duration, "weight": d.weight, "age": d.age,
            "restingHr": d.restingHr, "avgHr": d.avgHr, "gender": d.gender, "climate": d.climate}


@router.post("/workouts", summary="Log a workout — analysed by the partner FitMetrics API", status_code=201)
async def log_workout(d: s.WorkoutLogIn):
    day = _day(d.date)
    try:
        a = await fitmetrics.workout_analysis(_payload(d))
    except fitmetrics.PartnerUnavailable:
        raise HTTPException(503, "Partner FitMetrics API unavailable — workout not saved")
    except ValueError as exc:
        raise HTTPException(400, f"FitMetrics rejected the workout: {exc}")
    store.add_workout(d.profile, day, d.activity, d.duration, d.avgHr, a)
    return ok({"profile": d.profile, "date": day, "analysedBy": "FitMetrics API (23MIC0060)", **a})


@router.get("/workouts", summary="Workout history with weekly totals")
def list_workouts(profile: str = PROFILE_Q):
    ws = store.workouts(profile)
    today = date.today()
    weeks = []
    for i in range(3, -1, -1):
        start = today - timedelta(days=today.weekday() + 7 * i)
        end = start + timedelta(days=6)
        sel = [w for w in ws if start.isoformat() <= w["date"] <= end.isoformat()]
        weeks.append({"weekStart": start.isoformat(), "sessions": len(sel),
                      "minutes": round(sum(w["duration"] for w in sel)),
                      "calories": round(sum(w["caloriesBurned"] or 0 for w in sel)),
                      "trainingLoad": round(sum(w["trainingLoad"] or 0 for w in sel))})
    return ok({"profile": profile, "count": len(ws), "workouts": list(reversed(ws))[:30], "weekly": weeks})


@router.get("/training-status", summary="Injury risk from the workout log — ACWR computed by FitMetrics")
async def training_status(profile: str = PROFILE_Q):
    ws = store.workouts(profile)
    today = date.today()
    days = [(today - timedelta(days=27 - i)).isoformat() for i in range(28)]
    loads = [round(sum(w["trainingLoad"] or 0 for w in ws if w["date"] == d), 1) for d in days]
    if sum(loads) == 0:
        raise MetricError("no workouts logged in the last 28 days")
    try:
        tb = await fitmetrics.training_balance(loads)
    except fitmetrics.PartnerUnavailable:
        raise HTTPException(503, "Partner FitMetrics API unavailable — injury risk could not be computed")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return ok({"profile": profile, "days": days, "dailyLoads": loads, "computedBy": "FitMetrics API (23MIC0060)", **tb})


# ------------------------------------------------------------------ demo data
ACTS = [("running", 40, 168), ("cycling", 60, 140), ("weight_training", 50, 125), ("hiit", 25, 176),
        ("swimming", 35, 150), ("running", 30, 158), ("badminton", 45, 145)]


@router.post("/demo-seed", summary="Fill a profile with 6 weeks of realistic sample data")
async def demo_seed(d: s.SeedIn):
    rng = random.Random(d.profile)
    today = date.today()
    store.reset(d.profile)
    start_w = 79.0
    for i in range(7):
        day = today - timedelta(days=42 - i * 7)
        store.add_measurement(d.profile, day.isoformat(), round(start_w - i * 0.55 + rng.uniform(-0.2, 0.2), 1),
                              round(88 - i * 0.6, 1), round(19.5 - i * 0.35, 1))
    plan = []
    for back in range(41, -1, -1):
        day = today - timedelta(days=back)
        if day.weekday() in (0, 2, 4, 5) or (back < 7 and day.weekday() == 3):
            act, dur, hr = ACTS[rng.randrange(len(ACTS))]
            plan.append((day.isoformat(), act, dur + rng.randint(-5, 10), hr + rng.randint(-6, 6)))
    payloads = [{"activity": a, "duration": du, "weight": 76, "age": d.age, "restingHr": d.restingHr,
                 "avgHr": hr, "gender": "male", "climate": "normal"} for _, a, du, hr in plan]
    try:
        results = await fitmetrics.workout_analysis_many(payloads)
    except fitmetrics.PartnerUnavailable:
        raise HTTPException(503, "Partner FitMetrics API unavailable — demo workouts need FitMetrics to analyse them")
    for (day, act, dur, hr), a in zip(plan, results):
        store.add_workout(d.profile, day, act, dur, hr, a)
    store.set_goal(d.profile, 72.0, (today + timedelta(weeks=8)).isoformat(), start_w, (today - timedelta(days=42)).isoformat())
    return ok({"profile": d.profile, "measurements": 7, "workouts": len(plan), "goal": store.goal(d.profile)})


@router.delete("/reset", summary="Delete all data for a profile")
def reset(profile: str = PROFILE_Q):
    store.reset(profile)
    return ok({"profile": profile, "deleted": True})
