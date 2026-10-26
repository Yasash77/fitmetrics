"""End-to-end tests for the FitMetrics API.  Run:  pytest -q"""
import os
import tempfile

os.environ["KEY_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "keys.db")
os.environ["RATE_LIMIT_PER_MIN"] = "1000"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.clients import fitpulse  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
H = {"X-API-Key": config.DEMO_API_KEY}
RUN = {"activity": "running", "duration": 45, "weight": 74, "age": 21, "restingHr": 62, "avgHr": 172}


def post(path, body, headers=H):
    return client.post(f"/api/v1{path}", json=body, headers=headers)


# ------------------------------------------------------------------ system & security
def test_health_is_public():
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["data"]["status"] == "up"


def test_missing_and_invalid_key():
    assert post("/metrics/heart-rate-zones", {"age": 21, "restingHr": 62}, headers={}).status_code == 401
    assert post("/metrics/heart-rate-zones", {"age": 21, "restingHr": 62}, headers={"X-API-Key": "nope"}).status_code == 401


def test_issue_key_and_use_it():
    r = client.post("/api/v1/keys", json={"name": "Tester", "email": "t@vit.ac.in"})
    assert r.status_code == 201
    key = r.json()["data"]["apiKey"]
    assert post("/metrics/heart-rate-zones", {"age": 21, "restingHr": 62}, {"X-API-Key": key}).status_code == 200
    me = client.get("/api/v1/keys/me", headers={"X-API-Key": key}).json()["data"]
    assert me["tier"] == "free" and me["requests"] >= 1


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MIN", 3)
    key = client.post("/api/v1/keys", json={"name": "Spam", "email": "s@x.io"}).json()["data"]["apiKey"]
    codes = [post("/metrics/heart-rate-zones", {"age": 21, "restingHr": 62}, {"X-API-Key": key}).status_code
             for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_rate_limit_headers():
    r = post("/metrics/heart-rate-zones", {"age": 21, "restingHr": 62})
    assert "X-RateLimit-Remaining" in r.headers


# ------------------------------------------------------------------ workout
def test_workout_analysis():
    d = post("/metrics/workout-analysis", RUN).json()["data"]
    assert d["caloriesBurned"] == 544
    assert d["zone"].startswith("Zone 4") and d["intensity"] == "High"
    assert d["loadRating"] == "Hard" and d["recoveryHours"] == 36
    assert d["hydration"]["electrolytes"] is True
    assert "544 kcal" in d["summary"]


def test_unknown_activity_is_400():
    r = post("/metrics/calories-burned", {"activity": "chess", "duration": 30, "weight": 70})
    assert r.status_code == 400 and r.json()["success"] is False


def test_validation_is_422():
    r = post("/metrics/heart-rate-zones", {"age": 5, "restingHr": 62})
    assert r.status_code == 422 and r.json()["details"][0]["field"] == "age"


def test_hr_zones_and_intensity():
    z = post("/metrics/heart-rate-zones", {"age": 21, "restingHr": 62}).json()["data"]
    assert z["maxHr"] == 193 and len(z["zones"]) == 5
    i = post("/metrics/workout-intensity", {"age": 21, "restingHr": 62, "avgHr": 150, "duration": 40}).json()["data"]
    assert i["zone"].startswith("Zone 2")


def test_hydration_measured():
    d = post("/metrics/hydration", {"weight": 74, "duration": 60, "preWeight": 74, "postWeight": 73.2}).json()["data"]
    assert d["sweatLossLitres"] == 0.8 and d["drinkLitres"] == 1.2 and d["method"] == "measured weight change"


# ------------------------------------------------------------------ training management
def test_training_balance_sweet_spot_and_spike():
    steady = [60, 0, 80, 0, 70, 90, 0] * 4
    d = post("/metrics/training-balance", {"dailyLoads": steady}).json()["data"]
    assert d["acwr"] == 1.0 and d["zone"] == "Sweet Spot"
    spike = [40, 0, 40, 0, 40, 40, 0] * 3 + [120, 90, 130, 0, 140, 110, 100]
    d = post("/metrics/training-balance", {"dailyLoads": spike}).json()["data"]
    assert d["zone"] == "Danger Zone" and d["injuryRisk"] == "High"


def test_training_balance_needs_28_days():
    assert post("/metrics/training-balance", {"dailyLoads": [50] * 10}).status_code == 422


def test_readiness():
    fresh = post("/metrics/readiness", {"lastLoad": 60, "hoursSince": 30, "restingHr": 60,
                                        "baselineRestingHr": 62, "sleepHours": 8, "soreness": 1}).json()["data"]
    assert fresh["status"] == "Ready" and fresh["readinessScore"] >= 80
    tired = post("/metrics/readiness", {"lastLoad": 200, "hoursSince": 10, "restingHr": 70,
                                        "baselineRestingHr": 62, "sleepHours": 5, "soreness": 5}).json()["data"]
    assert tired["status"] == "Recover" and len(tired["flags"]) == 3


# ------------------------------------------------------------------ cardio
def test_pace_and_predictions():
    d = post("/metrics/pace", {"activity": "running", "distance": 5, "duration": 25}).json()["data"]
    assert d["paceMinPerKm"] == "5:00" and d["speedKmh"] == 12.0
    assert d["predictions"]["10K"]["time"] == "52:07"


def test_unrealistic_pace_is_400():
    assert post("/metrics/pace", {"activity": "running", "distance": 10, "duration": 10}).status_code == 400


def test_vo2max():
    d = post("/metrics/vo2max", {"age": 21, "gender": "male", "restingHr": 62}).json()["data"]
    assert d["vo2max"] == 47.6 and d["rating"] == "Good"
    c = post("/metrics/vo2max", {"age": 21, "gender": "male", "restingHr": 62, "cooperDistance": 2800}).json()["data"]
    assert c["method"].startswith("Cooper")


# ------------------------------------------------------------------ strength
def test_strength_analysis():
    d = post("/metrics/strength-analysis", {"exercise": "bench_press", "weight": 80, "reps": 6, "bodyweight": 74}).json()["data"]
    assert d["oneRepMax"] == 94.5 and d["strengthLevel"] == "Intermediate" and d["nextLevelAt"] == 111.0


def test_session_volume():
    sets = [{"exercise": "bench_press", "weight": 80, "reps": 6}] * 3 + [{"exercise": "barbell_row", "weight": 60, "reps": 10}] * 3
    d = post("/metrics/session-volume", {"sets": sets, "bodyweight": 74}).json()["data"]
    assert d["totalVolumeKg"] == 3240 and d["muscleGroups"]["chest"]["sets"] == 3
    assert d["estimatedCalories"] == 133




# ------------------------------------------------------------------ partner integration
EB = {"age": 21, "gender": "male", "height": 178, "weight": 74, "activityLevel": "moderate",
      "caloriesEaten": 2300, "workouts": [{"activity": "running", "duration": 45, "weight": 74}]}


def test_energy_balance_uses_fitpulse(monkeypatch):
    async def fake(*a, **k):
        return 2716.0
    monkeypatch.setattr(fitpulse, "maintenance_calories", fake)
    d = post("/metrics/energy-balance", EB).json()["data"]
    assert d["maintenanceSource"] == "FitPulse API" and d["netBalance"] == -960


def test_energy_balance_503_when_partner_down(monkeypatch):
    async def down(*a, **k):
        raise fitpulse.PartnerUnavailable("timeout")
    monkeypatch.setattr(fitpulse, "maintenance_calories", down)
    r = post("/metrics/energy-balance", EB)
    assert r.status_code == 503 and "FitPulse" in r.json()["error"]


# ------------------------------------------------------------------ reports
def test_pdf_report():
    r = post("/reports/workout", {**RUN, "athlete": "Yasash",
                                  "strength": {"exercise": "squat", "weight": 100, "reps": 5}})
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
