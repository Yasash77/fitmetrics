"""Body-composition engine — BMI, US Navy body fat and ideal body weight."""
from __future__ import annotations
import math
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
