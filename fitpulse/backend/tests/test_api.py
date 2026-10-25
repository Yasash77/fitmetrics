"""End-to-end tests for the FitPulse 24-Formula API. Run: pytest -q"""
import os
import tempfile

os.environ["KEY_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "fp_keys.db")
os.environ["RATE_LIMIT_PER_MIN"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402
from app import config  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
H = {"X-API-Key": config.DEMO_API_KEY}


def post(path, body, headers=H):
    return client.post(f"/api/v1{path}", json=body, headers=headers)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["data"]["formulasEngine"] == 24


def test_partner_calories_endpoint():
    # Works both with and without API key for seamless FitMetrics partner integration
    payload = {"age": 21, "gender": "male", "height": 178, "weight": 74, "activityLevel": "moderate"}
    r = client.post("/api/v1/fitness/calories", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["bmr"] == 1752
    assert body["dailyCalories"] == 2716
    assert body["data"]["bmrHarrisBenedict"] > 0


def test_full_24_formula_analysis():
    r = post("/fitness/full-analysis", {"age": 21, "gender": "male", "height": 178, "weight": 74})
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["formulasCount"] == 24
    assert len(d["formulasSummary"]) == 24


def test_pdf_report_sheet():
    r = post("/reports/fitness-sheet", {"athlete": "Majit", "age": 21, "gender": "male", "height": 178, "weight": 74})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
