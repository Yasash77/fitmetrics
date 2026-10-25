"""Domain 5: Body Composition, Ideal Weight & Comprehensive 24-Metric Synthesis (Formulas 21–24)."""
from __future__ import annotations
import math
from . import cardio, metabolic, strength, training
from .metabolic import MetricError


def bmi_analysis(weight: float, height: float) -> dict:
    """Formula 21: Body Mass Index (BMI), BMI Prime & Rohrer's Ponderal Index."""
    h_m = height / 100
    bmi = round(weight / (h_m ** 2), 1)
    bmi_prime = round(bmi / 25.0, 2)
    ponderal = round(weight / (h_m ** 3), 2)
    if bmi < 18.5:
        cat = "Underweight"
    elif bmi < 25.0:
        cat = "Normal"
    elif bmi < 30.0:
        cat = "Overweight"
    else:
        cat = "Obese"
    return {
        "bmi": bmi,
        "category": cat,
        "bmiPrime": bmi_prime,
        "ponderalIndex": ponderal,
        "healthyWeightMinKg": round(18.5 * (h_m ** 2), 1),
        "healthyWeightMaxKg": round(24.9 * (h_m ** 2), 1),
    }


def body_fat_navy(
    gender: str,
    height: float,
    neck: float,
    waist: float,
    hip: float | None = None,
    weight: float | None = None,
) -> dict:
    """Formula 22: Body Fat Percentage (U.S. Navy Circumference Method) + Fat & Lean Mass."""
    if gender == "male":
        if waist <= neck:
            raise MetricError("waist must be larger than neck")
        bf = 495 / (1.0324 - 0.19077 * math.log10(waist - neck) + 0.15456 * math.log10(height)) - 450
        bands = [(6, "Essential"), (14, "Athletic"), (18, "Fitness"), (25, "Average")]
    else:
        if hip is None:
            raise MetricError("hip is required for female body-fat calculation")
        if waist + hip <= neck:
            raise MetricError("waist + hip must be larger than neck")
        bf = 495 / (1.29579 - 0.35004 * math.log10(waist + hip - neck) + 0.22100 * math.log10(height)) - 450
        bands = [(14, "Essential"), (21, "Athletic"), (25, "Fitness"), (32, "Average")]
    bf = round(max(2.0, bf), 1)
    out = {
        "bodyFat": bf,
        "category": next((n for lim, n in bands if bf < lim), "Above Average"),
        "method": "US Navy Circumference Method",
    }
    if weight:
        out["fatMass"] = round(weight * bf / 100, 1)
        out["leanMass"] = round(weight - out["fatMass"], 1)
    return out


def ideal_body_weight(height: float, gender: str) -> dict:
    """Formula 23: Ideal Body Weight Range (Hamwi, Devine, Robinson & Miller Equations)."""
    inches_over_5ft = max(0.0, (height / 2.54) - 60.0)
    if gender == "male":
        hamwi = 48.0 + 2.7 * inches_over_5ft
        devine = 50.0 + 2.3 * inches_over_5ft
        robinson = 52.0 + 1.9 * inches_over_5ft
        miller = 56.2 + 1.41 * inches_over_5ft
    else:
        hamwi = 45.5 + 2.2 * inches_over_5ft
        devine = 45.5 + 2.3 * inches_over_5ft
        robinson = 49.0 + 1.7 * inches_over_5ft
        miller = 53.1 + 1.36 * inches_over_5ft

    avg_ibw = round((hamwi + devine + robinson + miller) / 4, 1)
    return {
        "idealWeightKg": avg_ibw,
        "hamwiKg": round(hamwi, 1),
        "devineKg": round(devine, 1),
        "robinsonKg": round(robinson, 1),
        "millerKg": round(miller, 1),
        "rangeKg": {"min": round(avg_ibw * 0.9, 1), "max": round(avg_ibw * 1.1, 1)},
    }


def comprehensive_24_analysis(d: dict) -> dict:
    """Master 24-Formula Synthesis Engine — runs all 5 fitness domains in one call."""
    age = d["age"]
    gender = d["gender"]
    height = d["height"]
    weight = d["weight"]
    activity_level = d.get("activityLevel", "moderate")
    goal = d.get("goal", "maintain")
    neck = d.get("neck", 38.0)
    waist = d.get("waist", 84.0)
    hip = d.get("hip", 96.0 if gender == "female" else None)

    bf = body_fat_navy(gender, height, neck, waist, hip, weight)
    bmi = bmi_analysis(weight, height)
    ibw = ideal_body_weight(height, gender)
    energy = metabolic.energy_profile(age, gender, height, weight, activity_level, goal, bf["bodyFat"])
    workout = training.analyse_workout(
        d.get("activity", "running"),
        d.get("duration", 45),
        weight,
        age,
        d.get("restingHr", 62),
        d.get("avgHr", 172),
        gender,
        d.get("climate", "normal"),
    )
    zones = cardio.hr_zones(age, d.get("restingHr", 62))
    vo2 = cardio.vo2max_analysis(
        age, gender, d.get("restingHr", 62), d.get("maxHr"), d.get("cooperDistance")
    )
    pace_res = cardio.pace_and_predictions(
        d.get("paceActivity", "running"), d.get("distanceKm", 5.0), d.get("paceDurationMin", 25.0)
    )
    lift_res = strength.analyse_lift(
        d.get("exercise", "bench_press"), d.get("liftWeight", 80.0), d.get("liftReps", 6), weight
    )
    vol_res = strength.session_volume(
        d.get("sets") or [{"exercise": "bench_press", "weight": 80, "reps": 6}, {"exercise": "squat", "weight": 100, "reps": 5}],
        weight,
    )
    loads = d.get("dailyLoads") or [55, 0, 70, 0, 60, 85, 0, 60, 0, 75, 0, 65, 90, 0, 65, 0, 80, 0, 70, 95, 0, 121, 0, 68, 0, 47, 95, 0]
    acwr_res = training.training_balance(loads)
    ready_res = training.readiness(
        d.get("lastLoad", workout["trainingLoad"]),
        d.get("hoursSince", 36),
        d.get("restingHr", 62),
        d.get("baselineRestingHr", 62),
        d.get("sleepHours", 7.5),
        d.get("soreness", 2),
    )

    formulas_summary = [
        {"id": 1, "domain": "Metabolic", "name": "BMR (Mifflin-St Jeor)", "value": f"{energy['bmrMifflinStJeor']} kcal/day"},
        {"id": 2, "domain": "Metabolic", "name": "BMR (Harris-Benedict)", "value": f"{energy['bmrHarrisBenedict']} kcal/day"},
        {"id": 3, "domain": "Metabolic", "name": "TDEE & Katch-McArdle BMR", "value": f"{energy['tdee']} kcal/day (Katch: {energy['bmrKatchMcArdle']} kcal)"},
        {"id": 4, "domain": "Metabolic", "name": "Activity Calorie Burn (MET)", "value": f"{workout['caloriesBurned']} kcal ({workout['activity']})"},
        {"id": 5, "domain": "Cardio", "name": "Max Heart Rate (Tanaka / Fox)", "value": f"{zones['tanaka']} bpm / {zones['fox']} bpm"},
        {"id": 6, "domain": "Cardio", "name": "Karvonen HR Reserve & Zones", "value": f"{zones['heartRateReserve']} bpm HRR · {workout['zone']}"},
        {"id": 7, "domain": "Cardio", "name": "VO2max (Cooper 12-min Model)", "value": f"{vo2['vo2maxCooper'] or 'N/A (optional)'} ml/kg/min"},
        {"id": 8, "domain": "Cardio", "name": "VO2max (Uth HR-Ratio Model)", "value": f"{vo2['vo2maxUth']} ml/kg/min ({vo2['rating']})"},
        {"id": 9, "domain": "Cardio", "name": "Pace & Speed Analysis", "value": f"{pace_res['paceMinPerKm']} /km ({pace_res['speedKmh']} km/h)"},
        {"id": 10, "domain": "Cardio", "name": "Riegel Race Prediction (10K)", "value": pace_res.get("predictions", {}).get("10K", {}).get("time", "—")},
        {"id": 11, "domain": "Strength", "name": "One-Rep Max (Epley Formula)", "value": f"{lift_res['epley']} kg"},
        {"id": 12, "domain": "Strength", "name": "One-Rep Max (Brzycki Formula)", "value": f"{lift_res['brzycki']} kg"},
        {"id": 13, "domain": "Strength", "name": "Relative Strength Index", "value": f"{lift_res.get('relativeStrength', '—')} × BW"},
        {"id": 14, "domain": "Strength", "name": "Strength Level Classification", "value": lift_res.get("strengthLevel", "—")},
        {"id": 15, "domain": "Strength", "name": "Total Session Volume", "value": f"{vol_res['totalVolumeKg']} kg ({vol_res['trainingFocus']})"},
        {"id": 16, "domain": "Training Load", "name": "TRIMP Load (Banister & Edwards)", "value": f"{workout['trainingLoad']} TRIMP / {workout['edwardsTrimp']} Edwards"},
        {"id": 17, "domain": "Training Load", "name": "ACWR (Acute:Chronic Ratio)", "value": f"{acwr_res['acwr']} ({acwr_res['zone']})"},
        {"id": 18, "domain": "Training Load", "name": "Training Monotony & Strain", "value": f"{acwr_res['monotony']} · Strain {acwr_res['strain']}"},
        {"id": 19, "domain": "Training Load", "name": "Readiness & Recovery Score", "value": f"{ready_res['readinessScore']}/100 ({ready_res['status']})"},
        {"id": 20, "domain": "Training Load", "name": "Recovery & Hydration Plan", "value": f"~{workout['recoveryHours']}h rest · {workout['hydration']['drinkLitres']} L fluid"},
        {"id": 21, "domain": "Body Comp", "name": "BMI & Ponderal Index", "value": f"{bmi['bmi']} kg/m² ({bmi['category']}) · PI {bmi['ponderalIndex']}"},
        {"id": 22, "domain": "Body Comp", "name": "Body Fat % (U.S. Navy Method)", "value": f"{bf['bodyFat']}% ({bf['category']}) · Lean {bf['leanMass']} kg"},
        {"id": 23, "domain": "Body Comp", "name": "Ideal Body Weight (Hamwi/Devine)", "value": f"{ibw['idealWeightKg']} kg ({ibw['rangeKg']['min']}–{ibw['rangeKg']['max']} kg)"},
        {"id": 24, "domain": "Body Comp", "name": "Physiological Fitness Age", "value": f"{vo2['fitnessAge']} years (Chronological: {age})"},
    ]

    return {
        "athlete": d.get("athlete", "Athlete"),
        "formulasCount": 24,
        "formulasSummary": formulas_summary,
        "metabolic": energy,
        "workout": workout,
        "cardio": {"zones": zones, "vo2max": vo2, "pace": pace_res},
        "strength": {"lift": lift_res, "volume": vol_res},
        "trainingLoad": {"balance": acwr_res, "readiness": ready_res},
        "bodyComposition": {"bmi": bmi, "bodyFat": bf, "idealWeight": ibw, "fitnessAge": vo2["fitnessAge"]},
    }
