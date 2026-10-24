# Local stand-in for partner FitPulse API (23MIC0052) used only for offline testing.
from fastapi import FastAPI
app = FastAPI(title="FitPulse (local stub)")
@app.post("/api/v1/fitness/calories")
def calories(d: dict):
    s = 5 if d["gender"] == "male" else -161
    bmr = 10*d["weight"] + 6.25*d["height"] - 5*d["age"] + s
    m = {"sedentary":1.2,"light":1.375,"moderate":1.55,"active":1.725,"very_active":1.9}[d["activityLevel"]]
    return {"bmr": round(bmr), "dailyCalories": round(bmr*m)}
