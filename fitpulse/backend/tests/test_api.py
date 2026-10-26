"""End-to-end tests for the FitPulse API.  Run:  pytest -q"""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["KEY_DB_PATH"] = os.path.join(_tmp, "keys.db")
os.environ["PROGRESS_DB_PATH"] = os.path.join(_tmp, "progress.db")
os.environ["RATE_LIMIT_PER_MIN"] = "1000"

from datetime import date, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.clients import fitmetrics  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
H = {"X-API-Key": config.DEMO_API_KEY}
ME = {"age": 21, "gender": "male", "height": 178, "weight": 74, "activityLevel": "moderate"}


def post(path, body, headers=H):
    return client.post(f"/api/v1{path}", json=body, headers=headers)


def get(path, headers=H):
    return client.get(f"/api/v1{path}", headers=headers)


@pytest.fixture
def partner_up(monkeypatch):
    """Fake FitMetrics: deterministic workout analysis and ACWR."""
    async def wa(p):
        return {"caloriesBurned": round(9.8 * p["weight"] * p["duration"] / 60), "zone": "Zone 4 · Threshold",
                "intensity": "High", "trainingLoad": 100, "recoveryHours": 36}

    async def many(ps):
        return [await wa(p) for p in ps]

    async def tb(loads):
        return {"acwr": 1.1, "zone": "Sweet Spot", "injuryRisk": "Low", "acuteLoad": 1, "chronicLoad": 1}
    monkeypatch.setattr(fitmetrics, "workout_analysis", wa)
    monkeypatch.setattr(fitmetrics, "workout_analysis_many", many)
    monkeypatch.setattr(fitmetrics, "training_balance", tb)


@pytest.fixture
def partner_down(monkeypatch):
    async def down(*a, **k):
        raise fitmetrics.PartnerUnavailable("timeout")
    for n in ("workout_analysis", "workout_analysis_many", "training_balance"):
        monkeypatch.setattr(fitmetrics, n, down)


# ------------------------------------------------------------------ system
def test_health_and_key():
    assert get("/health", {}).json()["data"]["status"] == "up"
    assert post("/fitness/bmi", {"weight": 74, "height": 178}, {}).status_code == 401
    key = post("/keys", {"name": "Maajith", "email": "m@vit.ac.in"}, {}).json()["data"]["apiKey"]
    assert post("/fitness/bmi", {"weight": 74, "height": 178}, {"X-API-Key": key}).status_code == 200


# ------------------------------------------------------------------ energy & body
def test_calories_partner_compatible_without_key():
    r = post("/fitness/calories", ME, {}).json()            # FitMetrics calls this endpoint
    assert r["dailyCalories"] == 2716 and r["data"]["bmrMifflinStJeor"] == 1752


def test_bmi_bodyfat_ideal():
    assert post("/fitness/bmi", {"weight": 74, "height": 178}).json()["data"]["bmi"] == 23.4
    assert post("/fitness/body-fat", {"gender": "male", "height": 178, "neck": 38, "waist": 84, "weight": 74}).json()["data"]["bodyFat"] == 15.7
    assert post("/fitness/body-fat", {"gender": "female", "height": 160, "neck": 32, "waist": 70}).status_code == 400
    assert post("/fitness/ideal-weight", {"height": 178, "gender": "male"}).json()["data"]["idealWeightKg"] > 65


def test_goal_plan_safety():
    g = post("/fitness/goal-plan", {**ME, "targetWeight": 70, "weeks": 8}).json()["data"]
    assert g["weeklyChangeKg"] == -0.5 and g["safety"] == "Safe" and g["dailyCalorieTarget"] == 2166
    crash = post("/fitness/goal-plan", {**ME, "targetWeight": 64, "weeks": 4}).json()["data"]
    assert crash["safety"] == "Unsafe" and crash["cappedAtMinimum"] is True


def test_validation_422():
    r = post("/fitness/bmi", {"weight": 5, "height": 178})
    assert r.status_code == 422 and r.json()["details"][0]["field"] == "weight"


def test_removed_workout_endpoints_are_gone():
    for path in ("/fitness/workout-analysis", "/fitness/training-balance", "/fitness/pace", "/fitness/vo2max"):
        assert post(path, {}).status_code in (404, 405)


# ------------------------------------------------------------------ progress
def test_measurements_summary_and_goal():
    p = "t_meas"
    today = date.today()
    for i, w in enumerate([80, 79.4, 78.9, 78.2]):
        assert post("/progress/measurements", {"profile": p, "date": (today - timedelta(days=21 - 7 * i)).isoformat(), "weight": w}).status_code == 201
    assert post("/progress/goal", {"profile": p, "targetWeight": 75, "targetDate": (today + timedelta(weeks=6)).isoformat()}).status_code == 200
    s = get(f"/progress/summary?profile={p}").json()["data"]
    assert s["totalChangeKg"] == -1.8 and s["weeklyRateKg"] < -0.5
    assert s["goalProgress"]["onTrack"] is True and s["goalProgress"]["remainingKg"] == -3.2


def test_future_date_rejected():
    r = post("/progress/measurements", {"profile": "x1", "date": (date.today() + timedelta(days=3)).isoformat(), "weight": 70})
    assert r.status_code == 400


def test_workout_logged_via_fitmetrics(partner_up):
    r = post("/progress/workouts", {"profile": "t_w", "activity": "running", "duration": 45, "avgHr": 170,
                                    "restingHr": 62, "age": 21, "weight": 74})
    assert r.status_code == 201 and r.json()["data"]["analysedBy"].startswith("FitMetrics")
    h = get("/progress/workouts?profile=t_w").json()["data"]
    assert h["count"] == 1 and h["weekly"][-1]["sessions"] == 1
    st = get("/progress/training-status?profile=t_w").json()["data"]
    assert st["computedBy"].startswith("FitMetrics") and len(st["dailyLoads"]) == 28


def test_workout_not_saved_when_partner_down(partner_down):
    r = post("/progress/workouts", {"profile": "t_down", "activity": "running", "duration": 45, "avgHr": 170,
                                    "restingHr": 62, "age": 21, "weight": 74})
    assert r.status_code == 503
    assert get("/progress/workouts?profile=t_down").json()["data"]["count"] == 0


def test_demo_seed(partner_up):
    d = post("/progress/demo-seed", {"profile": "t_seed"}).json()["data"]
    assert d["measurements"] == 7 and d["workouts"] > 20
    s = get("/progress/summary?profile=t_seed").json()["data"]
    assert s["goal"]["targetWeight"] == 72.0 and s["totalChangeKg"] < 0


def test_partner_sync(partner_up):
    d = post("/fitness/partner-sync", {**ME, "activity": "running", "duration": 45, "avgHr": 172, "restingHr": 62}).json()["data"]
    assert d["baselineTdee"] == 2716 and d["adjustedDailyCalorieTarget"] == 2716 + d["workoutBurnFromFitMetrics"]


def test_pdf_report(partner_up):
    post("/progress/demo-seed", {"profile": "t_pdf"})
    r = post("/reports/profile", {**ME, "athlete": "Maajith", "neck": 38, "waist": 84, "targetWeight": 70, "weeks": 8, "profile": "t_pdf"})
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
