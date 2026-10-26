"""End-to-end tests for the FitMetrics API.  Run:  pytest -q"""
import os
import tempfile

os.environ["KEY_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "keys.db")
os.environ["RATE_LIMIT_PER_MIN"] = "1000"
os.environ["SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "platform.db")
os.environ.setdefault("DATABASE_URL", "")   # empty -> SQLite; set TEST_DATABASE_URL to run against Postgres
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ.pop("PLAN_SERVICE_URL", None)

from datetime import date, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import config, db, security  # noqa: E402
from app.clients import fitpulse, processing  # noqa: E402
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


# ============================================================================================
# FitPulse user platform (/api/*)
# ============================================================================================
CS = {"X-Requested-With": "fitpulse"}
PW = "correct-horse-42"


def new_client():
    return TestClient(app, base_url="https://testserver")


def register(c, email, name="Test User"):
    r = c.post("/api/auth/register", json={"name": name, "email": email, "password": PW}, headers=CS)
    assert r.status_code == 201, r.text
    return r


def full_profile(**over):
    p = {"dateOfBirth": "1998-05-04", "sex": "female", "units": "metric", "heightCm": 165, "weightKg": 62,
         "activityLevel": "moderate", "restingHr": 60, "primaryGoal": "fat_loss", "secondaryGoals": ["strength"],
         "targetWeightKg": 59, "timeline": "12", "experienceLevel": "intermediate",
         "disciplines": ["gym", "running"], "disciplineDetails": {"gym": {"gymFocus": "strength"}, "running": {"runDistance": "10k"}},
         "daysPerWeek": 3, "sessionMinutes": "45", "locations": ["gym"], "equipment": ["barbell", "dumbbells"],
         "healthCheck": "none", "disclaimerAccepted": True}
    p.update(over)
    return p


def onboard(c, **over):
    v = c.get("/api/profile").json()["data"]["version"]
    r = c.put("/api/profile", json={"data": full_profile(**over), "version": v}, headers=CS)
    assert r.status_code == 200, r.text
    r = c.post("/api/profile/complete", headers=CS)
    assert r.status_code == 200, r.text
    return r.json()["data"]


@pytest.fixture
def platform_env(monkeypatch):
    """Fake FitPulse API responses; plan service in labelled mock mode."""
    async def energy(*a, **k):
        return {"tdee": 2077, "targetCalories": 1577, "macros": {"proteinGrams": 138}}

    async def goal(*a, **k):
        return {"weeklyChangeKg": -0.25, "safety": "Safe", "dailyCalorieTarget": 1800}
    monkeypatch.setattr(fitpulse, "energy_needs", energy)
    monkeypatch.setattr(fitpulse, "goal_plan", goal)
    monkeypatch.setattr(config, "PLAN_SERVICE_MODE", "mock")
    monkeypatch.setattr(config, "PLAN_SERVICE_URL", "")


# ------------------------------------------------------------------ auth
@pytest.mark.usefixtures("platform_env")
def test_password_hashing_is_salted_scrypt():
    h1, h2 = security.hash_password(PW), security.hash_password(PW)
    assert h1 != h2 and h1.startswith("scrypt$") and PW not in h1
    assert security.verify_password(PW, h1) and not security.verify_password("wrong-pass-1", h1)


@pytest.mark.usefixtures("platform_env")
def test_register_sets_httponly_cookie_and_stores_no_plaintext():
    c = new_client()
    r = register(c, "cookie@example.com")
    sc = r.headers["set-cookie"].lower()
    assert "httponly" in sc and "samesite=lax" in sc and "secure" in sc
    row = db.one("SELECT password_hash FROM users WHERE email = 'cookie@example.com'")
    assert PW not in row["password_hash"]
    assert c.get("/api/auth/me").json()["data"]["email"] == "cookie@example.com"


@pytest.mark.usefixtures("platform_env")
def test_weak_password_and_duplicate_email():
    c = new_client()
    assert c.post("/api/auth/register", json={"name": "A", "email": "weak@example.com", "password": "short"}, headers=CS).status_code == 400
    register(c, "dupe@example.com")
    r = new_client().post("/api/auth/register", json={"name": "B", "email": "DUPE@example.com", "password": PW}, headers=CS)
    assert r.status_code == 409


@pytest.mark.usefixtures("platform_env")
def test_csrf_header_required():
    c = new_client()
    r = c.post("/api/auth/register", json={"name": "A", "email": "csrf@example.com", "password": PW})
    assert r.status_code == 403


@pytest.mark.usefixtures("platform_env")
def test_login_logout_and_protected_routes():
    c = new_client()
    register(c, "login@example.com")
    c.post("/api/auth/logout", headers=CS)
    assert c.get("/api/auth/me").json()["data"] is None
    assert c.get("/api/profile").status_code == 401
    assert c.post("/api/auth/login", json={"email": "login@example.com", "password": "nope-nope-1"}, headers=CS).status_code == 401
    r = c.post("/api/auth/login", json={"email": "Login@Example.com", "password": PW}, headers=CS)
    assert r.status_code == 200 and c.get("/api/auth/me").json()["data"]["email"] == "login@example.com"


@pytest.mark.usefixtures("platform_env")
def test_login_lockout_after_repeated_failures():
    c = new_client()
    register(c, "lock@example.com")
    for _ in range(config.LOGIN_MAX_FAILURES):
        c.post("/api/auth/login", json={"email": "lock@example.com", "password": "bad-guess-99"}, headers=CS)
    r = c.post("/api/auth/login", json={"email": "lock@example.com", "password": PW}, headers=CS)
    assert r.status_code == 429


@pytest.mark.usefixtures("platform_env")
def test_forgot_is_generic_and_reset_flow(monkeypatch):
    monkeypatch.setattr(config, "DEV_SHOW_RESET_LINK", True)
    c = new_client()
    register(c, "reset@example.com")
    unknown = c.post("/api/auth/forgot", json={"email": "nobody@example.com"}, headers=CS).json()["data"]
    assert "devResetLink" not in unknown and unknown["emailDelivery"] is False
    link = c.post("/api/auth/forgot", json={"email": "reset@example.com"}, headers=CS).json()["data"]["devResetLink"]
    token = link.split("token=")[1]
    assert c.post("/api/auth/reset", json={"token": token, "password": "new-password-77"}, headers=CS).status_code == 200
    assert c.get("/api/auth/me").json()["data"] is None                   # all sessions revoked
    assert c.post("/api/auth/reset", json={"token": token, "password": "another-pass-88"}, headers=CS).status_code == 400
    assert c.post("/api/auth/login", json={"email": "reset@example.com", "password": "new-password-77"}, headers=CS).status_code == 200


# ------------------------------------------------------------------ onboarding & profile
@pytest.mark.usefixtures("platform_env")
def test_onboarding_config_is_served():
    cfg = new_client().get("/api/config/onboarding").json()["data"]
    assert len(cfg["disciplines"]) == 13 and any(s["id"] == "discipline_details" for s in cfg["steps"])


@pytest.mark.usefixtures("platform_env")
def test_profile_validation_and_completion():
    c = new_client()
    register(c, "onb@example.com")
    r = c.post("/api/profile/complete", headers=CS)
    assert r.status_code == 400 and "primaryGoal" in r.json()["fields"]
    v = c.get("/api/profile").json()["data"]["version"]
    bad = c.put("/api/profile", json={"data": full_profile(heightCm=900, sessionMinutes="7", hacker="x"), "version": v}, headers=CS)
    body = bad.json()["data"]
    assert "heightCm" in body["fieldErrors"] and "hacker" not in body["data"] and "heightCm" not in body["data"]
    data = onboard(c)
    assert data["onboardingComplete"] is True and data["data"]["disciplineDetails"]["gym"]["gymFocus"] == "strength"


@pytest.mark.usefixtures("platform_env")
def test_under_16_rejected():
    c = new_client()
    register(c, "young@example.com")
    v = c.get("/api/profile").json()["data"]["version"]
    dob = (date.today() - timedelta(days=365 * 14)).isoformat()
    c.put("/api/profile", json={"data": full_profile(dateOfBirth=dob), "version": v}, headers=CS)
    r = c.post("/api/profile/complete", headers=CS)
    assert r.status_code == 400 and "dateOfBirth" in r.json()["fields"]


@pytest.mark.usefixtures("platform_env")
def test_stale_profile_version_is_not_overwritten():
    c = new_client()
    register(c, "stale@example.com")
    c.put("/api/profile", json={"data": {"heightCm": 170}, "version": 1}, headers=CS)
    r = c.put("/api/profile", json={"data": {"heightCm": 180}, "version": 1}, headers=CS)
    assert r.status_code == 409 and r.json()["data"]["data"]["heightCm"] == 170


# ------------------------------------------------------------------ plans
@pytest.mark.usefixtures("platform_env")
def test_plan_requires_onboarding():
    c = new_client()
    register(c, "noplan@example.com")
    assert c.post("/api/plans", json={"idempotencyKey": "abcdefgh1"}, headers=CS).status_code == 400


@pytest.mark.usefixtures("platform_env")
def test_mock_plan_is_labelled_and_idempotent():
    c = new_client()
    register(c, "plan@example.com")
    onboard(c)
    r1 = c.post("/api/plans", json={"idempotencyKey": "key-12345"}, headers=CS)
    r2 = c.post("/api/plans", json={"idempotencyKey": "key-12345"}, headers=CS)
    p = r1.json()["data"]
    assert r1.status_code == 201 and p["id"] == r2.json()["data"]["id"]
    assert p["isMock"] is True and p["source"] == "development-mock"
    assert p["plan"]["generatedBy"]["isMock"] is True and "Maajith" in p["plan"]["warnings"][0]
    assert p["energy"]["status"] == "ok" and p["energy"]["source"].startswith("FitPulse")
    assert len(c.get("/api/plans").json()["data"]) == 1
    assert c.get("/api/plans/current").json()["data"]["id"] == p["id"]


@pytest.mark.usefixtures("platform_env")
def test_payload_contains_no_direct_identifiers():
    c = new_client()
    register(c, "privacy@example.com", name="Private Person")
    onboard(c)
    pid = c.post("/api/plans", json={"idempotencyKey": "priv-1234"}, headers=CS).json()["data"]["id"]
    req = db.one("SELECT request FROM plans WHERE id = :i", i=pid)["request"]
    assert "privacy@example.com" not in req and "Private Person" not in req and "1998-05-04" not in req


@pytest.mark.usefixtures("platform_env")
def test_unconfigured_plan_service_is_honest(monkeypatch):
    monkeypatch.setattr(config, "PLAN_SERVICE_MODE", "")
    c = new_client()
    register(c, "unconf@example.com")
    onboard(c)
    r = c.post("/api/plans", json={"idempotencyKey": "unconf-123"}, headers=CS)
    assert r.status_code == 503 and "not configured" in r.json()["error"]
    assert c.get("/api/plans").json()["data"] == []


@pytest.mark.usefixtures("platform_env")
def test_live_service_invalid_response_is_rejected(monkeypatch):
    monkeypatch.setattr(config, "PLAN_SERVICE_URL", "https://processing.invalid")

    async def fake_live(method, path, payload=None):
        return {"planId": "x1", "status": "ready", "generatedBy": {"system": "maajith"}}   # no weeks/summary
    monkeypatch.setattr(processing, "_live", fake_live)
    c = new_client()
    register(c, "invalid@example.com")
    onboard(c)
    r = c.post("/api/plans", json={"idempotencyKey": "inv-12345"}, headers=CS)
    assert r.status_code == 502
    assert c.get("/api/plans").json()["data"][0]["status"] == "failed"


@pytest.mark.usefixtures("platform_env")
def test_live_service_valid_plan(monkeypatch):
    monkeypatch.setattr(config, "PLAN_SERVICE_URL", "https://processing.invalid")
    sent = {}

    async def fake_live(method, path, payload=None):
        sent["path"], sent["payload"] = path, payload
        return {"success": True, "data": {
            "planId": "mj-9", "status": "ready", "generatedBy": {"system": "maajith-processing", "version": "1"},
            "summary": {"title": "Real plan", "weeks": 8},
            "weeks": [{"week": 1, "sessions": [{"id": "s1", "discipline": "gym", "title": "Lift", "blocks": [
                {"name": "Main", "type": "main", "items": [{"name": "Squat", "sets": 3, "reps": "5"}]}]}]}]}}
    monkeypatch.setattr(processing, "_live", fake_live)
    c = new_client()
    register(c, "live@example.com")
    onboard(c)
    p = c.post("/api/plans", json={"idempotencyKey": "live-12345"}, headers=CS).json()["data"]
    assert p["isMock"] is False and p["source"] == "maajith-processing" and sent["path"] == "/plans"
    assert sent["payload"]["contractVersion"] == processing.CONTRACT_VERSION


# ------------------------------------------------------------------ access control
@pytest.mark.usefixtures("platform_env")
def test_users_cannot_access_each_others_data():
    a, b = new_client(), new_client()
    register(a, "alice@example.com")
    register(b, "bob@example.com")
    onboard(a)
    pid = a.post("/api/plans", json={"idempotencyKey": "alice-123"}, headers=CS).json()["data"]["id"]
    wid = a.post("/api/workouts", json={"clientId": "alicew-123", "date": date.today().isoformat(), "discipline": "gym",
                                        "title": "Lift", "durationMin": 40}, headers=CS).json()["data"]["id"]
    assert b.get(f"/api/plans/{pid}").status_code == 404
    assert b.get(f"/api/workouts/{wid}").status_code == 404
    assert b.delete(f"/api/workouts/{wid}", headers=CS).status_code == 404
    assert b.post("/api/workouts", json={"clientId": "bobw-1234", "date": date.today().isoformat(), "discipline": "gym",
                                         "title": "x", "durationMin": 10, "planId": pid}, headers=CS).status_code == 404
    assert b.get("/api/workouts").json()["data"] == []


# ------------------------------------------------------------------ workouts & progress
@pytest.mark.usefixtures("platform_env")
def test_workout_dedupe_analysis_and_progress():
    c = new_client()
    register(c, "wo@example.com")
    onboard(c)
    pid = c.post("/api/plans", json={"idempotencyKey": "wo-plan-1"}, headers=CS).json()["data"]["id"]
    body = {"clientId": "wo-client-1", "date": date.today().isoformat(), "discipline": "running", "title": "Run",
            "durationMin": 35, "avgHr": 150, "rpe": 6, "planId": pid, "sessionId": "w1s1"}
    r1 = c.post("/api/workouts", json=body, headers=CS).json()["data"]
    r2 = c.post("/api/workouts", json=body, headers=CS).json()["data"]
    assert r1["id"] == r2["id"] and r2["duplicate"] is True
    assert r1["analysisStatus"] == "analysed" and r1["analysis"]["analysedBy"].startswith("FitMetrics")
    no_hr = c.post("/api/workouts", json={**body, "clientId": "wo-client-2", "avgHr": None}, headers=CS).json()["data"]
    assert no_hr["analysisStatus"] == "skipped_no_heart_rate" and no_hr["analysis"] is None
    prog = c.get("/api/progress").json()["data"]
    assert prog["weekly"][-1]["sessions"] == 2 and prog["trainingBalance"]["status"] == "insufficient_data"
    assert prog["adherence"]["sessionsCompleted"] == 1


@pytest.mark.usefixtures("platform_env")
def test_future_workout_rejected_and_empty_progress_is_empty():
    c = new_client()
    register(c, "empty@example.com")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert c.post("/api/workouts", json={"clientId": "fut-12345", "date": tomorrow, "discipline": "gym", "title": "x",
                                         "durationMin": 10}, headers=CS).status_code == 400
    prog = c.get("/api/progress").json()["data"]
    assert prog["totalWorkouts12w"] == 0 and prog["measurements"] == [] and prog["trainingBalance"]["status"] == "insufficient_data"


@pytest.mark.usefixtures("platform_env")
def test_measurements_and_account_export_delete():
    c = new_client()
    register(c, "acct@example.com")
    assert c.post("/api/measurements", json={"date": date.today().isoformat(), "weight": 70.5}, headers=CS).status_code == 201
    exp = c.get("/api/account/export").json()["data"]
    assert exp["measurements"][0]["weight"] == 70.5 and "password_hash" not in str(exp)
    assert c.request("DELETE", "/api/account", json={"password": "wrong-pass-1"}, headers=CS).status_code == 400
    assert c.request("DELETE", "/api/account", json={"password": PW}, headers=CS).status_code == 200
    assert db.one("SELECT id FROM users WHERE email = 'acct@example.com'") is None


@pytest.mark.usefixtures("platform_env")
def test_integrations_status_exposes_no_secrets(monkeypatch):
    monkeypatch.setattr(config, "PLAN_SERVICE_KEY", "super-secret-key")
    monkeypatch.setattr(config, "FITPULSE_API_KEY", "fp-secret")

    async def up():
        return "up"
    monkeypatch.setattr(fitpulse, "health", up)
    txt = new_client().get("/api/integrations/status").text
    assert "secret" not in txt and '"mode":"mock"' in txt


@pytest.mark.usefixtures("platform_env")
def test_unknown_api_route_is_json_404():
    r = new_client().get("/api/nope")
    assert r.status_code == 404 and r.json()["success"] is False


@pytest.mark.usefixtures("platform_env")
def test_training_balance_from_fitmetrics_engine_after_four_weeks():
    c = new_client()
    register(c, "acwr@example.com")
    onboard(c)
    for i, back in enumerate(range(26, -1, -3)):
        r = c.post("/api/workouts", json={"clientId": f"acwr-{i:04d}", "date": (date.today() - timedelta(days=back)).isoformat(),
                                          "discipline": "running", "title": "Run", "durationMin": 40, "avgHr": 150}, headers=CS)
        assert r.json()["data"]["analysisStatus"] == "analysed"
    tb = c.get("/api/progress").json()["data"]["trainingBalance"]
    assert tb["status"] == "ok" and tb["source"].startswith("FitMetrics") and 0.5 < tb["acwr"] < 1.6


@pytest.mark.usefixtures("platform_env")
def test_energy_kept_when_goal_plan_call_fails(monkeypatch):
    async def denied(*a, **k):
        raise fitpulse.PartnerUnavailable("HTTP 401")
    monkeypatch.setattr(fitpulse, "goal_plan", denied)
    c = new_client()
    register(c, "gp@example.com")
    onboard(c)
    e = c.post("/api/plans", json={"idempotencyKey": "gp-123456"}, headers=CS).json()["data"]["energy"]
    assert e["status"] == "ok" and e["calories"]["tdee"] == 2077 and "goalPlan" not in e and "401" in e["goalPlanError"]
