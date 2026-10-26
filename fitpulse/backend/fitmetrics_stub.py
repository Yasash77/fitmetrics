# Minimal local stand-in for the partner FitMetrics API (23MIC0060), used only when the real
# FitMetrics code is not available next to this project. run.py prefers the real ../../backend.
import math

from fastapi import FastAPI

app = FastAPI(title="FitMetrics (local stub)")
METS = {"walking": 3.5, "running": 9.8, "cycling": 7.5, "swimming": 8.0, "weight_training": 6.0, "yoga": 2.5,
        "hiit": 8.0, "skipping": 12.3, "football": 7.0, "badminton": 5.5}


@app.post("/api/v1/metrics/workout-analysis")
def workout_analysis(d: dict):
    act, dur, wt = d.get("activity", "running"), float(d["duration"]), float(d["weight"])
    mhr = round(208 - 0.7 * int(d["age"]))
    hrr = max(0.0, min(1.0, (int(d["avgHr"]) - int(d["restingHr"])) / max(1, mhr - int(d["restingHr"]))))
    trimp = round(dur * hrr * 0.64 * math.exp(1.92 * hrr))
    zone = ["Zone 1 · Recovery", "Zone 2 · Fat Burn", "Zone 3 · Aerobic", "Zone 4 · Threshold", "Zone 5 · Max Effort"][
        max(0, min(4, int((hrr - 0.5) / 0.1)))]
    return {"success": True, "data": {"activity": act, "durationMin": dur, "caloriesBurned": round(METS.get(act, 7) * wt * dur / 60),
            "percentHrr": round(hrr * 100, 1), "zone": zone, "intensity": "High" if hrr >= 0.8 else "Moderate",
            "trainingLoad": trimp, "recoveryHours": 12 if trimp < 50 else 24 if trimp < 100 else 36}}


@app.post("/api/v1/metrics/training-balance")
def training_balance(d: dict):
    loads = d["dailyLoads"]
    acute, chronic = sum(loads[-7:]) / 7, sum(loads) / 28
    r = acute / chronic if chronic else 0
    zone = "Undertraining" if r < 0.8 else "Sweet Spot" if r <= 1.3 else "Caution" if r <= 1.5 else "Danger Zone"
    return {"success": True, "data": {"acuteLoad": round(acute, 1), "chronicLoad": round(chronic, 1), "acwr": round(r, 2),
            "zone": zone, "injuryRisk": {"Undertraining": "Low", "Sweet Spot": "Low", "Caution": "Moderate"}.get(zone, "High"),
            "advice": "stub", "weeklyLoads": [round(sum(loads[i:i + 7])) for i in range(0, 28, 7)]}}
