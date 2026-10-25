"""Domain 2: Cardiovascular Fitness & Performance (Formulas 5–10)."""
from __future__ import annotations
from .metabolic import MetricError

ZONES = [
    ("Zone 1 · Recovery", "Very Light", 0.50, 0.60, "Active recovery & warm-up"),
    ("Zone 2 · Fat Burn", "Light", 0.60, 0.70, "Aerobic base & fat oxidation"),
    ("Zone 3 · Aerobic", "Moderate", 0.70, 0.80, "Cardiovascular endurance"),
    ("Zone 4 · Threshold", "High", 0.80, 0.90, "Lactate threshold & pace"),
    ("Zone 5 · Max Effort", "Maximal", 0.90, 1.00, "VO2max & anaerobic power"),
]

RUN_DISTANCES = {"5K": 5.0, "10K": 10.0, "Half Marathon": 21.0975, "Marathon": 42.195}
RIDE_DISTANCES = {"20 km": 20.0, "40 km": 40.0, "100 km": 100.0}
SWIM_DISTANCES = {"400m": 0.4, "1500m": 1.5, "3.8km Ironman": 3.8}

_NORMS = {
    "male": [
        (29, (38, 43, 49, 55)),
        (39, (36, 41, 47, 52)),
        (49, (34, 39, 44, 49)),
        (59, (31, 35, 40, 45)),
        (200, (28, 32, 37, 41)),
    ],
    "female": [
        (29, (32, 37, 43, 48)),
        (39, (30, 34, 40, 45)),
        (49, (28, 32, 37, 42)),
        (59, (25, 29, 34, 38)),
        (200, (23, 26, 31, 35)),
    ],
}
_RATINGS = ["Poor", "Fair", "Good", "Excellent", "Superior"]


def max_hr_models(age: int) -> dict:
    """Formula 5: Maximum Heart Rate (MHR) Estimation (Tanaka, Fox, Gellish)."""
    tanaka = round(208 - 0.7 * age)
    fox = 220 - age
    gellish = round(207 - 0.7 * age)
    return {
        "maxHr": tanaka,
        "tanaka": tanaka,
        "fox": fox,
        "gellish": gellish,
        "primaryFormula": "Tanaka (208 - 0.7 × age)",
    }


def hr_zones(age: int, resting_hr: int) -> dict:
    """Formula 6: Heart Rate Training Zones (Karvonen HRR Method)."""
    mhr_info = max_hr_models(age)
    mhr = mhr_info["maxHr"]
    if resting_hr >= mhr:
        raise MetricError("restingHr must be lower than estimated max HR")
    reserve = mhr - resting_hr
    zones = [
        {
            "zone": name,
            "intensity": label,
            "min": round(resting_hr + lo * reserve),
            "max": round(resting_hr + hi * reserve),
            "benefit": benefit,
        }
        for name, label, lo, hi, benefit in ZONES
    ]
    return {
        **mhr_info,
        "restingHr": resting_hr,
        "heartRateReserve": reserve,
        "zones": zones,
    }


def _fmt_time(minutes: float) -> str:
    s = round(minutes * 60)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def pace_and_predictions(activity: str, distance_km: float, duration_min: float) -> dict:
    """Formulas 9 & 10: Pace/Speed Calculation & Riegel Race Time Prediction."""
    if activity not in ("running", "cycling", "walking", "swimming"):
        raise MetricError("activity must be running, cycling, walking or swimming")
    speed = distance_km / (duration_min / 60)
    pace_min = duration_min / distance_km
    if activity == "running" and not 3.5 <= speed <= 30:
        raise MetricError(f"speed {speed:.1f} km/h is unrealistic for running")
    if activity == "cycling" and not 5 <= speed <= 75:
        raise MetricError(f"speed {speed:.1f} km/h is unrealistic for cycling")

    out = {
        "activity": activity,
        "distanceKm": distance_km,
        "durationMin": duration_min,
        "speedKmh": round(speed, 2),
        "paceMinPerKm": _fmt_time(pace_min),
    }
    if activity == "swimming":
        out["pacePer100m"] = _fmt_time(pace_min / 10)

    targets = (
        RUN_DISTANCES
        if activity == "running"
        else RIDE_DISTANCES
        if activity == "cycling"
        else SWIM_DISTANCES
        if activity == "swimming"
        else {}
    )
    preds = {}
    for name, d in targets.items():
        t = duration_min * (d / distance_km) ** 1.06
        preds[name] = {"time": _fmt_time(t), "paceMinPerKm": _fmt_time(t / d)}
    if preds:
        out["predictions"] = preds
        out["predictionModel"] = "Riegel T2 = T1 × (D2/D1)^1.06"
    return out


def fitness_age(vo2: float, gender: str) -> int:
    """Formula 24a: Physiological Fitness Age from VO2max norms."""
    for (_, bands), mid in zip(_NORMS[gender], (22, 34, 44, 54, 64)):
        if vo2 >= bands[1]:
            return mid
    return 70


def vo2max_analysis(
    age: int,
    gender: str,
    resting_hr: int,
    measured_max_hr: int | None = None,
    cooper_distance_m: float | None = None,
) -> dict:
    """Formulas 7 & 8: VO2max via Cooper 12-min Test and Uth HR-Ratio Regression."""
    mhr = measured_max_hr or max_hr_models(age)["maxHr"]
    if resting_hr >= mhr:
        raise MetricError("restingHr must be lower than max HR")

    uth_vo2 = round(15.3 * mhr / resting_hr, 1)
    cooper_vo2 = None
    if cooper_distance_m is not None:
        if not 800 <= cooper_distance_m <= 5000:
            raise MetricError("cooperDistance must be between 800 and 5000 m")
        cooper_vo2 = round((cooper_distance_m - 504.9) / 44.73, 1)

    primary = cooper_vo2 if cooper_vo2 is not None else uth_vo2
    method = "Cooper 12-minute run test" if cooper_vo2 is not None else "Uth heart-rate ratio (15.3 × HRmax / HRrest)"

    bands = next(b for a, b in _NORMS[gender] if age <= a)
    idx = sum(primary >= t for t in bands)
    return {
        "vo2max": primary,
        "vo2maxUth": uth_vo2,
        "vo2maxCooper": cooper_vo2,
        "unit": "ml/kg/min",
        "rating": _RATINGS[idx],
        "method": method,
        "nextRating": None if idx == 4 else _RATINGS[idx + 1],
        "nextRatingAt": None if idx == 4 else bands[idx],
        "fitnessAge": fitness_age(primary, gender),
    }
