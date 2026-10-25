"""Domain 4: Training Load & Recovery Management (Formulas 16–20)."""
from __future__ import annotations
import math
import statistics
from .cardio import ZONES, max_hr_models
from .metabolic import MetricError, activity_calories


def load_rating(trimp: float) -> tuple[str, int]:
    for limit, name, hrs in ((50, "Easy", 12), (100, "Moderate", 24), (180, "Hard", 36)):
        if trimp < limit:
            return name, hrs
    return "Very Hard", 48


def workout_intensity(age: int, resting_hr: int, avg_hr: int, minutes: float, gender: str = "male") -> dict:
    """Formula 16: Training Impulse (Banister & Edwards TRIMP) and %HRR Intensity."""
    mhr = max_hr_models(age)["maxHr"]
    if avg_hr > mhr + 10:
        raise MetricError(f"avgHr {avg_hr} is above the estimated max HR {mhr}")
    if resting_hr >= mhr:
        raise MetricError("restingHr must be lower than max HR")
    hrr = max(0.0, min(1.0, (avg_hr - resting_hr) / (mhr - resting_hr)))
    zone, label, zone_num = "Below Zone 1", "Very Light", 1
    for idx, (name, lab, lo, _, _) in enumerate(ZONES, start=1):
        if hrr >= lo:
            zone, label, zone_num = name, lab, idx

    b, k = (1.92, 0.64) if gender == "male" else (1.67, 0.86)
    banister_trimp = minutes * hrr * k * math.exp(b * hrr)
    edwards_trimp = minutes * zone_num
    rating, recovery = load_rating(banister_trimp)
    return {
        "maxHr": mhr,
        "percentHrr": round(hrr * 100, 1),
        "zone": zone,
        "intensity": label,
        "trainingLoad": round(banister_trimp),
        "edwardsTrimp": round(edwards_trimp),
        "loadRating": rating,
        "recoveryHours": recovery,
    }


def fluid_plan(
    weight: float,
    minutes: float,
    level: str = "moderate",
    climate: str = "normal",
    pre: float | None = None,
    post: float | None = None,
) -> dict:
    """Formula 20a: ACSM Post-Workout Sweat Loss & Hydration Plan."""
    if pre and post:
        if post > pre + 0.5:
            raise MetricError("postWeight cannot be much higher than preWeight")
        sweat, method = max(0.0, pre - post), "measured weight change"
    else:
        rate = {"low": 0.5, "moderate": 0.8, "high": 1.2}.get(level, 0.8) * (1.3 if climate == "hot" else 1.0)
        sweat, method = rate * weight / 70 * minutes / 60, "estimated sweat rate"
    drink = sweat * 1.5
    return {
        "sweatLossLitres": round(sweat, 2),
        "drinkLitres": round(drink, 2),
        "glasses250ml": math.ceil(drink / 0.25),
        "electrolytes": minutes >= 60 or climate == "hot" or level == "high",
        "method": method,
    }


def analyse_workout(
    activity: str,
    minutes: float,
    weight: float,
    age: int,
    resting_hr: int,
    avg_hr: int,
    gender: str = "male",
    climate: str = "normal",
) -> dict:
    """Combines Formula 4 (MET calories), Formula 16 (TRIMP/Intensity), and Formula 20 (Hydration/Recovery)."""
    cal_info = activity_calories(activity, minutes, weight)
    kcal = cal_info["caloriesBurned"]
    it = workout_intensity(age, resting_hr, avg_hr, minutes, gender)
    level = "high" if it["intensity"] in ("High", "Maximal") else "moderate" if it["intensity"] == "Moderate" else "low"
    fluids = fluid_plan(weight, minutes, level, climate)
    summary = (
        f"{minutes:g} min of {activity.replace('_', ' ')} burned {kcal} kcal at {it['zone']} "
        f"({it['intensity'].lower()} intensity). Training load {it['trainingLoad']} TRIMP "
        f"({it['loadRating'].lower()}); recover ~{it['recoveryHours']} h and drink {fluids['drinkLitres']} L."
    )
    return {
        "activity": activity,
        "durationMin": minutes,
        "caloriesBurned": kcal,
        "caloriesPerMin": round(kcal / minutes, 1),
        **it,
        "hydration": fluids,
        "summary": summary,
    }


def training_balance(daily_loads: list[float]) -> dict:
    """Formulas 17 & 18: Acute:Chronic Workload Ratio (ACWR) + Foster Training Monotony & Strain."""
    if len(daily_loads) != 28:
        raise MetricError("dailyLoads must contain exactly 28 values (oldest first)")
    if any(x < 0 for x in daily_loads):
        raise MetricError("loads cannot be negative")
    last7 = daily_loads[-7:]
    acute = sum(last7) / 7
    chronic = sum(daily_loads) / 28
    if chronic == 0:
        raise MetricError("no training recorded in the last 28 days")
    ratio = acute / chronic
    if ratio < 0.8:
        zone, risk, advice = "Undertraining", "Low", "Load is dropping — gradually increase volume to keep fitness."
    elif ratio <= 1.3:
        zone, risk, advice = "Sweet Spot", "Low", "Load is well balanced — keep progressing at this rate."
    elif ratio <= 1.5:
        zone, risk, advice = "Caution", "Moderate", "Load is rising fast — hold volume steady this week."
    else:
        zone, risk, advice = "Danger Zone", "High", "Spike in load — reduce intensity to lower injury risk."
    sd = statistics.pstdev(last7)
    monotony = (sum(last7) / 7) / sd if sd else None
    weekly = [round(sum(daily_loads[i : i + 7])) for i in range(0, 28, 7)]
    return {
        "acuteLoad": round(acute, 1),
        "chronicLoad": round(chronic, 1),
        "acwr": round(ratio, 2),
        "zone": zone,
        "injuryRisk": risk,
        "advice": advice,
        "weeklyLoads": weekly,
        "weekChangePct": round((weekly[3] - weekly[2]) / weekly[2] * 100, 1) if weekly[2] else None,
        "monotony": round(monotony, 2) if monotony else None,
        "strain": round(sum(last7) * monotony) if monotony else None,
    }


def readiness(
    last_load: float,
    hours_since: float,
    resting_hr: int,
    baseline_resting_hr: int,
    sleep_hours: float | None = None,
    soreness: int | None = None,
) -> dict:
    """Formulas 19 & 20b: Readiness Score (0–100), Recovery Index & Actionable Session Recommendation."""
    _, needed = load_rating(last_load)
    recovery_pct = min(1.0, hours_since / needed)
    rhr_dev = resting_hr - baseline_resting_hr
    parts = {
        "recovery": round(recovery_pct * 50),
        "heartRate": max(0, 25 - max(0, rhr_dev) * 5),
        "sleep": round(min((sleep_hours if sleep_hours is not None else 7.5) / 8, 1) * 15),
        "soreness": round((5 - (soreness if soreness is not None else 2)) / 4 * 10),
    }
    score = sum(parts.values())
    if score >= 80:
        status, rec = "Ready", {"type": "Hard session", "zone": "Zone 4 intervals", "durationMin": "30-45"}
    elif score >= 60:
        status, rec = "Moderate", {"type": "Steady session", "zone": "Zone 3", "durationMin": "40"}
    elif score >= 40:
        status, rec = "Fatigued", {"type": "Easy session", "zone": "Zone 2", "durationMin": "20-30"}
    else:
        status, rec = "Recover", {"type": "Rest / mobility", "zone": "Zone 1 or rest", "durationMin": "0-20"}
    flags = []
    if rhr_dev >= 5:
        flags.append(f"Resting HR is {rhr_dev} bpm above baseline — possible fatigue or illness.")
    if sleep_hours is not None and sleep_hours < 6:
        flags.append("Less than 6 h sleep — avoid maximal efforts.")
    if recovery_pct < 1:
        flags.append(f"Only {round(recovery_pct * 100)}% of the recommended {needed} h recovery completed.")
    return {
        "readinessScore": score,
        "status": status,
        "breakdown": parts,
        "recoveryHoursNeeded": needed,
        "recoveryCompletePct": round(recovery_pct * 100),
        "recommendation": rec,
        "flags": flags,
    }
