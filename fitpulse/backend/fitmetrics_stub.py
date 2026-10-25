# Local stand-in for partner FitMetrics API (23MIC0060) used only for offline testing.
from fastapi import FastAPI

app = FastAPI(title="FitMetrics (local stub)")

METS = {
    "walking": 3.5, "running": 9.8, "cycling": 7.5, "swimming": 8.0,
    "weight_training": 6.0, "yoga": 2.5, "hiit": 8.0, "skipping": 12.3,
    "football": 7.0, "badminton": 5.5,
}


@app.post("/api/v1/metrics/workout-analysis")
def workout_analysis(d: dict):
    act = d.get("activity", "running")
    dur = float(d.get("duration", 45))
    wt = float(d.get("weight", 74))
    age = int(d.get("age", 21))
    rhr = int(d.get("restingHr", 62))
    ahr = int(d.get("avgHr", 168))
    met = METS.get(act, 7.0)
    kcal = round(met * wt * dur / 60)
    mhr = round(208 - 0.7 * age)
    hrr = max(0.0, min(1.0, (ahr - rhr) / max(1, mhr - rhr)))
    trimp = round(dur * hrr * 0.64 * (2.71828 ** (1.92 * hrr)))
    return {
        "success": True,
        "data": {
            "activity": act,
            "durationMin": dur,
            "caloriesBurned": kcal,
            "percentHrr": round(hrr * 100, 1),
            "zone": "Zone 4 · Threshold" if hrr >= 0.8 else "Zone 3 · Aerobic",
            "trainingLoad": trimp,
            "recoveryHours": 36 if trimp >= 100 else 24,
        },
    }
