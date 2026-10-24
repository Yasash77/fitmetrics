"""Training-management engine — ACWR injury risk, monotony/strain and daily readiness."""
from __future__ import annotations
import statistics

from .workout import MetricError, load_rating


def training_balance(daily_loads: list[float]) -> dict:
    """Acute:Chronic Workload Ratio (Gabbett, 2016) + Foster monotony/strain.

    daily_loads: 28 daily training loads (e.g. TRIMP), oldest first, 0 for rest days."""
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
    weekly = [round(sum(daily_loads[i:i + 7])) for i in range(0, 28, 7)]
    return {"acuteLoad": round(acute, 1), "chronicLoad": round(chronic, 1), "acwr": round(ratio, 2),
            "zone": zone, "injuryRisk": risk, "advice": advice, "weeklyLoads": weekly,
            "weekChangePct": round((weekly[3] - weekly[2]) / weekly[2] * 100, 1) if weekly[2] else None,
            "monotony": round(monotony, 2) if monotony else None,
            "strain": round(sum(last7) * monotony) if monotony else None}


def readiness(last_load: float, hours_since: float, resting_hr: int, baseline_resting_hr: int,
              sleep_hours: float | None = None, soreness: int | None = None) -> dict:
    """Readiness score (0-100) and today's session recommendation."""
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
    return {"readinessScore": score, "status": status, "breakdown": parts,
            "recoveryHoursNeeded": needed, "recoveryCompletePct": round(recovery_pct * 100),
            "recommendation": rec, "flags": flags}
