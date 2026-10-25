"""Domain 1: Metabolic & Energy Expenditure Analytics (Formulas 1–4)."""
from __future__ import annotations


class MetricError(ValueError):
    """Raised for invalid business input; converted to HTTP 400 by the API layer."""


ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

GOAL_DELTAS = {
    "lose": -500,
    "weight_loss": -500,
    "maintain": 0,
    "maintenance": 0,
    "gain": 350,
    "muscle_gain": 350,
}

MACRO_SPLITS = {
    "lose": (0.35, 0.35, 0.30),
    "weight_loss": (0.35, 0.35, 0.30),
    "maintain": (0.30, 0.40, 0.30),
    "maintenance": (0.30, 0.40, 0.30),
    "gain": (0.30, 0.45, 0.25),
    "muscle_gain": (0.30, 0.45, 0.25),
}

MET_TABLE = {
    "walking": 3.5,
    "running": 9.8,
    "cycling": 7.5,
    "swimming": 8.0,
    "weight_training": 6.0,
    "yoga": 2.5,
    "hiit": 8.0,
    "skipping": 12.3,
    "football": 7.0,
    "badminton": 5.5,
    "rowing": 7.0,
    "boxing": 7.8,
}


def bmr_mifflin(weight: float, height: float, age: int, gender: str) -> float:
    """Formula 1: Mifflin-St Jeor BMR equation (kcal/day)."""
    s = 5 if gender == "male" else -161
    return 10 * weight + 6.25 * height - 5 * age + s


def bmr_harris_benedict(weight: float, height: float, age: int, gender: str) -> float:
    """Formula 2: Revised Roza & Shizgal (1984) Harris-Benedict BMR equation (kcal/day)."""
    if gender == "male":
        return 88.362 + 13.397 * weight + 4.799 * height - 5.677 * age
    return 447.593 + 9.247 * weight + 3.098 * height - 4.330 * age


def bmr_katch_mcardle(lean_mass_kg: float) -> float:
    """Formula 3a: Katch-McArdle lean-body-mass BMR equation."""
    return 370 + 21.6 * lean_mass_kg


def energy_profile(
    age: int,
    gender: str,
    height: float,
    weight: float,
    activity_level: str = "moderate",
    goal: str = "maintain",
    body_fat_pct: float | None = None,
) -> dict:
    """Formulas 1, 2 & 3: Multi-model BMR, TDEE, Target Calories & Macronutrient Targets."""
    if activity_level not in ACTIVITY_MULTIPLIERS:
        raise MetricError(f"unknown activityLevel '{activity_level}' — use one of {sorted(ACTIVITY_MULTIPLIERS)}")
    if goal not in GOAL_DELTAS:
        raise MetricError(f"unknown goal '{goal}' — use one of {sorted(GOAL_DELTAS)}")

    mifflin = bmr_mifflin(weight, height, age, gender)
    harris = bmr_harris_benedict(weight, height, age, gender)
    katch = None
    if body_fat_pct is not None and 3 <= body_fat_pct <= 60:
        lean_mass = weight * (1 - body_fat_pct / 100)
        katch = round(bmr_katch_mcardle(lean_mass))

    mult = ACTIVITY_MULTIPLIERS[activity_level]
    tdee = round(mifflin * mult)
    delta = GOAL_DELTAS[goal]
    target_cal = max(1200, tdee + delta)

    p_ratio, c_ratio, f_ratio = MACRO_SPLITS[goal]
    protein_g = round((target_cal * p_ratio) / 4)
    carbs_g = round((target_cal * c_ratio) / 4)
    fat_g = round((target_cal * f_ratio) / 9)

    return {
        "bmr": round(mifflin),
        "bmrMifflinStJeor": round(mifflin),
        "bmrHarrisBenedict": round(harris),
        "bmrKatchMcArdle": katch,
        "activityLevel": activity_level,
        "activityMultiplier": mult,
        "dailyCalories": tdee,
        "tdee": tdee,
        "goal": goal,
        "targetCalories": target_cal,
        "calorieAdjustment": delta,
        "macros": {
            "proteinGrams": protein_g,
            "carbsGrams": carbs_g,
            "fatGrams": fat_g,
            "proteinPct": round(p_ratio * 100),
            "carbsPct": round(c_ratio * 100),
            "fatPct": round(f_ratio * 100),
        },
    }


def activity_calories(activity: str, duration_min: float, weight_kg: float) -> dict:
    """Formula 4: Activity-Specific Calorie Burn (METs-based)."""
    met = MET_TABLE.get(activity)
    if met is None:
        raise MetricError(f"unknown activity '{activity}' — use one of {sorted(MET_TABLE)}")
    burned = round(met * weight_kg * (duration_min / 60))
    return {
        "activity": activity,
        "met": met,
        "durationMin": duration_min,
        "weightKg": weight_kg,
        "caloriesBurned": burned,
        "caloriesPerMin": round(burned / duration_min, 2),
        "formula": "MET × Weight(kg) × Duration(hr)",
    }
