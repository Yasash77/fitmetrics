"""Cardio engine — pace/speed analysis, race prediction and VO2max estimation."""
from __future__ import annotations
from .workout import MetricError, max_hr

RUN_DISTANCES = {"5K": 5.0, "10K": 10.0, "Half Marathon": 21.0975, "Marathon": 42.195}
RIDE_DISTANCES = {"20 km": 20.0, "40 km": 40.0, "100 km": 100.0}


def _fmt(minutes: float) -> str:
    s = round(minutes * 60)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def pace(activity: str, distance_km: float, duration_min: float) -> dict:
    if activity not in ("running", "cycling", "walking", "swimming"):
        raise MetricError("activity must be running, cycling, walking or swimming")
    speed = distance_km / (duration_min / 60)
    pace_min = duration_min / distance_km
    if activity == "running" and not 4 <= speed <= 30 or activity == "cycling" and not 5 <= speed <= 70:
        raise MetricError(f"speed {speed:.1f} km/h is unrealistic for {activity}")
    out = {"activity": activity, "distanceKm": distance_km, "durationMin": duration_min,
           "speedKmh": round(speed, 2), "paceMinPerKm": _fmt(pace_min)}
    if activity == "swimming":
        out["pacePer100m"] = _fmt(pace_min / 10)
    targets = RUN_DISTANCES if activity == "running" else RIDE_DISTANCES if activity == "cycling" else {}
    preds = {}
    for name, d in targets.items():
        t = duration_min * (d / distance_km) ** 1.06                         # Riegel (1981)
        preds[name] = {"time": _fmt(t), "paceMinPerKm": _fmt(t / d)}
    if preds:
        out["predictions"] = preds
        out["predictionModel"] = "Riegel T2 = T1 × (D2/D1)^1.06"
    return out


# VO2max norms (ml/kg/min): lower bounds for Fair, Good, Excellent, Superior by age band
_NORMS = {
    "male":   [(29, (38, 43, 49, 55)), (39, (36, 41, 47, 52)), (49, (34, 39, 44, 49)), (59, (31, 35, 40, 45)), (200, (28, 32, 37, 41))],
    "female": [(29, (32, 37, 43, 48)), (39, (30, 34, 40, 45)), (49, (28, 32, 37, 42)), (59, (25, 29, 34, 38)), (200, (23, 26, 31, 35))],
}
_RATINGS = ["Poor", "Fair", "Good", "Excellent", "Superior"]


def vo2max(age: int, gender: str, resting_hr: int, measured_max_hr: int | None = None,
           cooper_distance_m: float | None = None) -> dict:
    if cooper_distance_m:
        if not 800 <= cooper_distance_m <= 5000:
            raise MetricError("cooperDistance must be between 800 and 5000 m")
        v = (cooper_distance_m - 504.9) / 44.73                              # Cooper 12-min test
        method = "Cooper 12-minute run test"
    else:
        mhr = measured_max_hr or max_hr(age)
        if resting_hr >= mhr:
            raise MetricError("restingHr must be lower than max HR")
        v = 15.3 * mhr / resting_hr                                          # Uth et al. (2004)
        method = "Uth heart-rate ratio (15.3 × HRmax / HRrest)"
    bands = next(b for a, b in _NORMS[gender] if age <= a)
    idx = sum(v >= t for t in bands)
    return {"vo2max": round(v, 1), "unit": "ml/kg/min", "rating": _RATINGS[idx], "method": method,
            "nextRating": None if idx == 4 else _RATINGS[idx + 1],
            "nextRatingAt": None if idx == 4 else bands[idx],
            "fitnessAge": _fitness_age(v, gender)}


def _fitness_age(v: float, gender: str) -> int:
    """Youngest age band in which this VO2max still rates 'Good' (band midpoint)."""
    for (_, bands), mid in zip(_NORMS[gender], (25, 35, 45, 55, 65)):
        if v >= bands[1]:
            return mid
    return 70
