"""Body-composition engine (secondary feature) — US Navy body-fat method."""
from __future__ import annotations
import math

from .workout import MetricError


def body_fat(gender: str, height: float, neck: float, waist: float,
             hip: float | None = None, weight: float | None = None) -> dict:
    if gender == "male":
        if waist <= neck:
            raise MetricError("waist must be larger than neck")
        bf = 495 / (1.0324 - 0.19077 * math.log10(waist - neck) + 0.15456 * math.log10(height)) - 450
        bands = [(6, "Essential"), (14, "Athletic"), (18, "Fitness"), (25, "Average")]
    else:
        if hip is None:
            raise MetricError("hip is required for female body-fat calculation")
        bf = 495 / (1.29579 - 0.35004 * math.log10(waist + hip - neck) + 0.22100 * math.log10(height)) - 450
        bands = [(14, "Essential"), (21, "Athletic"), (25, "Fitness"), (32, "Average")]
    bf = round(bf, 1)
    out = {"bodyFat": bf, "category": next((n for lim, n in bands if bf < lim), "Above Average"),
           "method": "US Navy"}
    if weight:
        out["fatMass"] = round(weight * bf / 100, 1)
        out["leanMass"] = round(weight - out["fatMass"], 1)
    return out
