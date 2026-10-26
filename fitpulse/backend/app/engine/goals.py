"""Goal-planning engine — turns a target weight and timeframe into a daily calorie and macro plan."""
from __future__ import annotations

from datetime import date, timedelta

from .metabolic import MetricError, energy_profile

KCAL_PER_KG = 7700          # energy content of 1 kg body mass (fat + water)
MIN_CALORIES = {"male": 1500, "female": 1200}


def goal_plan(age: int, gender: str, height: float, weight: float, activity_level: str,
              target_weight: float, weeks: float) -> dict:
    if weeks <= 0:
        raise MetricError("weeks must be greater than 0")
    energy = energy_profile(age, gender, height, weight, activity_level, "maintain")
    tdee = energy["tdee"]
    change = round(target_weight - weight, 1)
    weekly = change / weeks
    daily_delta = round(weekly * KCAL_PER_KG / 7)
    target = tdee + daily_delta

    floor = MIN_CALORIES[gender]
    capped = target < floor
    if capped:
        target = floor

    pct_week = abs(weekly) / weight * 100
    if change == 0:
        safety, advice = "Maintain", "Eat at maintenance and keep training consistently."
    elif pct_week <= 0.5:
        safety, advice = "Gentle", "Very sustainable — easy to stick to."
    elif pct_week <= 1.0:
        safety, advice = "Safe", "Recommended pace (≤ 1 % of body weight per week)."
    elif pct_week <= 1.5:
        safety, advice = "Aggressive", "Possible short-term, but expect hunger and some muscle loss."
    else:
        safety, advice = "Unsafe", "Too fast — extend the timeframe to protect health and muscle."

    direction = "lose" if change < 0 else "gain" if change > 0 else "maintain"
    protein_per_kg = {"lose": 2.0, "gain": 1.8, "maintain": 1.6}[direction]
    protein_g = round(protein_per_kg * weight)
    fat_g = round(target * 0.25 / 9)
    carbs_g = max(0, round((target - protein_g * 4 - fat_g * 9) / 4))

    recommended_weeks = round(abs(change) / (weight * 0.0075), 1) if change else 0
    return {
        "currentWeight": weight, "targetWeight": target_weight, "changeKg": change,
        "weeks": weeks, "weeklyChangeKg": round(weekly, 2), "weeklyChangePctBodyweight": round(pct_week, 2),
        "maintenanceCalories": tdee, "dailyCalorieTarget": round(target), "dailyAdjustment": daily_delta,
        "cappedAtMinimum": capped, "safety": safety, "advice": advice,
        "recommendedWeeks": recommended_weeks,
        "targetDate": (date.today() + timedelta(weeks=weeks)).isoformat(),
        "macros": {"proteinGrams": protein_g, "carbsGrams": carbs_g, "fatGrams": fat_g,
                   "proteinPerKg": protein_per_kg},
    }
