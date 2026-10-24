"""Workout engine — calories, heart-rate intensity, training load, recovery, hydration."""
from __future__ import annotations
import math


class MetricError(ValueError):
    """Raised for invalid business input; converted to HTTP 400 by the API layer."""


MET_TABLE = {
    "walking": 3.5, "running": 9.8, "cycling": 7.5, "swimming": 8.0,
    "weight_training": 6.0, "yoga": 2.5, "hiit": 8.0, "skipping": 12.3,
    "football": 7.0, "badminton": 5.5,
}
ZONES = [  # name, intensity label, lower %HRR, upper %HRR
    ("Zone 1 · Recovery", "Very Light", 0.50, 0.60),
    ("Zone 2 · Fat Burn", "Light", 0.60, 0.70),
    ("Zone 3 · Aerobic", "Moderate", 0.70, 0.80),
    ("Zone 4 · Threshold", "High", 0.80, 0.90),
    ("Zone 5 · Max Effort", "Maximal", 0.90, 1.00),
]


def calories_burned(activity: str, minutes: float, weight: float) -> int:
    met = MET_TABLE.get(activity)
    if met is None:
        raise MetricError(f"unknown activity '{activity}' — use one of {sorted(MET_TABLE)}")
    return round(met * weight * minutes / 60)


def max_hr(age: int) -> int:
    return round(208 - 0.7 * age)                       # Tanaka et al. (2001)


def hr_zones(age: int, resting_hr: int) -> dict:
    mhr = max_hr(age)
    reserve = mhr - resting_hr
    zones = [{"zone": n, "intensity": lab, "min": round(resting_hr + lo * reserve),
              "max": round(resting_hr + hi * reserve)} for n, lab, lo, hi in ZONES]
    return {"maxHr": mhr, "heartRateReserve": reserve, "zones": zones}


def intensity(age: int, resting_hr: int, avg_hr: int, minutes: float, gender: str = "male") -> dict:
    mhr = max_hr(age)
    if avg_hr > mhr + 10:
        raise MetricError(f"avgHr {avg_hr} is above the estimated max HR {mhr}")
    if resting_hr >= mhr:
        raise MetricError("restingHr must be lower than max HR")
    hrr = max(0.0, min(1.0, (avg_hr - resting_hr) / (mhr - resting_hr)))   # Karvonen
    zone, label = "Below Zone 1", "Very Light"
    for name, lab, lo, _ in ZONES:
        if hrr >= lo:
            zone, label = name, lab
    b, k = (1.92, 0.64) if gender == "male" else (1.67, 0.86)              # Banister TRIMP
    trimp = minutes * hrr * k * math.exp(b * hrr)
    rating, recovery = load_rating(trimp)
    return {"maxHr": mhr, "percentHrr": round(hrr * 100, 1), "zone": zone, "intensity": label,
            "trainingLoad": round(trimp), "loadRating": rating, "recoveryHours": recovery}


def load_rating(trimp: float) -> tuple[str, int]:
    for limit, name, hrs in ((50, "Easy", 12), (100, "Moderate", 24), (180, "Hard", 36)):
        if trimp < limit:
            return name, hrs
    return "Very Hard", 48


def fluid_plan(weight, minutes, level="moderate", climate="normal", pre=None, post=None) -> dict:
    if pre and post:
        if post > pre + 0.5:
            raise MetricError("postWeight cannot be much higher than preWeight")
        sweat, method = max(0.0, pre - post), "measured weight change"
    else:
        rate = {"low": 0.5, "moderate": 0.8, "high": 1.2}[level] * (1.3 if climate == "hot" else 1.0)
        sweat, method = rate * weight / 70 * minutes / 60, "estimated sweat rate"
    drink = sweat * 1.5                                                     # ACSM: 150 % of loss
    return {"sweatLossLitres": round(sweat, 2), "drinkLitres": round(drink, 2),
            "glasses250ml": math.ceil(drink / 0.25),
            "electrolytes": minutes >= 60 or climate == "hot" or level == "high",
            "method": method}


def analyse(activity, minutes, weight, age, resting_hr, avg_hr, gender="male", climate="normal") -> dict:
    kcal = calories_burned(activity, minutes, weight)
    it = intensity(age, resting_hr, avg_hr, minutes, gender)
    level = "high" if it["intensity"] in ("High", "Maximal") else \
            "moderate" if it["intensity"] == "Moderate" else "low"
    fluids = fluid_plan(weight, minutes, level, climate)
    summary = (f"{minutes:g} min of {activity.replace('_', ' ')} burned {kcal} kcal at {it['zone']} "
               f"({it['intensity'].lower()} intensity). Training load {it['trainingLoad']} "
               f"({it['loadRating'].lower()}); recover ~{it['recoveryHours']} h and drink {fluids['drinkLitres']} L.")
    return {"activity": activity, "durationMin": minutes, "caloriesBurned": kcal,
            "caloriesPerMin": round(kcal / minutes, 1), **it, "hydration": fluids, "summary": summary}
