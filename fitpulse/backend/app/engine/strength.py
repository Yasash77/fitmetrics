"""Domain 3: Strength & Power Analytics (Formulas 11–15)."""
from __future__ import annotations
from collections import defaultdict
from .metabolic import MetricError

STANDARDS = {
    "bench_press": (0.75, 1.0, 1.5, 1.9),
    "squat": (1.0, 1.4, 1.9, 2.4),
    "deadlift": (1.25, 1.7, 2.2, 2.7),
    "overhead_press": (0.5, 0.65, 0.9, 1.15),
}
LEVELS = ["Beginner", "Novice", "Intermediate", "Advanced", "Elite"]
MUSCLE_MAP = {
    "bench_press": "chest",
    "incline_bench_press": "chest",
    "dumbbell_press": "chest",
    "chest_fly": "chest",
    "push_up": "chest",
    "squat": "legs",
    "front_squat": "legs",
    "leg_press": "legs",
    "lunge": "legs",
    "leg_curl": "legs",
    "leg_extension": "legs",
    "calf_raise": "legs",
    "hip_thrust": "glutes",
    "deadlift": "back",
    "barbell_row": "back",
    "pull_up": "back",
    "lat_pulldown": "back",
    "seated_row": "back",
    "overhead_press": "shoulders",
    "lateral_raise": "shoulders",
    "face_pull": "shoulders",
    "bicep_curl": "arms",
    "hammer_curl": "arms",
    "tricep_extension": "arms",
    "tricep_pushdown": "arms",
    "dip": "arms",
    "plank": "core",
    "crunch": "core",
    "hanging_leg_raise": "core",
}


def one_rep_max(weight: float, reps: int) -> dict:
    """Formulas 11 & 12: Epley, Brzycki & Lombardi 1RM Estimations."""
    if reps < 1 or reps > 20:
        raise MetricError("reps must be between 1 and 20 for a reliable 1RM estimate")
    epley = weight * (1 + reps / 30) if reps > 1 else weight
    brzycki = weight * 36 / (37 - reps)
    lombardi = weight * (reps ** 0.10)
    return {
        "oneRepMax": round((epley + brzycki) / 2, 1),
        "epley": round(epley, 1),
        "brzycki": round(brzycki, 1),
        "lombardi": round(lombardi, 1),
    }


def analyse_lift(exercise: str, weight: float, reps: int, bodyweight: float | None = None) -> dict:
    """Formulas 11, 12, 13 & 14: 1RM, Relative Strength Index & Strength Level Classification."""
    est = one_rep_max(weight, reps)
    orm = est["oneRepMax"]
    loads = {f"{p}%": round(orm * p / 100, 1) for p in (95, 90, 85, 80, 75, 70, 60)}
    out = {
        "exercise": exercise,
        **est,
        "trainingLoads": loads,
        "repTargets": {
            "strength (3-5 reps)": loads["85%"],
            "hypertrophy (8-12 reps)": loads["70%"],
            "endurance (15+ reps)": loads["60%"],
        },
    }
    if bodyweight and exercise in STANDARDS:
        ratio = orm / bodyweight
        idx = sum(ratio >= t for t in STANDARDS[exercise])
        out.update(
            {
                "relativeStrength": round(ratio, 2),
                "strengthLevel": LEVELS[idx],
                "nextLevel": None if idx == 4 else LEVELS[idx + 1],
                "nextLevelAt": None if idx == 4 else round(STANDARDS[exercise][idx] * bodyweight, 1),
            }
        )
    return out


def session_volume(sets: list[dict], bodyweight: float | None = None, duration_min: float | None = None) -> dict:
    """Formula 15: Total Training Volume, Exercise Intensity & Muscle-Group Breakdown."""
    if not sets:
        raise MetricError("at least one set is required")
    total_vol = total_reps = 0.0
    per_ex = defaultdict(lambda: {"sets": 0, "reps": 0, "volume": 0.0, "bestE1rm": 0.0, "topWeight": 0.0})
    muscles = defaultdict(lambda: {"sets": 0, "volume": 0.0})
    for s in sets:
        ex, w, r = s["exercise"], s["weight"], s["reps"]
        vol = w * r
        e1 = one_rep_max(w, min(r, 20))["oneRepMax"] if w > 0 else 0
        p = per_ex[ex]
        p["sets"] += 1
        p["reps"] += r
        p["volume"] += vol
        p["bestE1rm"] = max(p["bestE1rm"], e1)
        p["topWeight"] = max(p["topWeight"], w)
        m = muscles[MUSCLE_MAP.get(ex, "other")]
        m["sets"] += 1
        m["volume"] += vol
        total_vol += vol
        total_reps += r

    exercises = []
    intensities = []
    for ex, p in per_ex.items():
        avg_w = p["volume"] / p["reps"] if p["reps"] else 0
        rel = round(avg_w / p["bestE1rm"] * 100, 1) if p["bestE1rm"] else None
        if rel:
            intensities.append(rel)
        exercises.append(
            {
                "exercise": ex,
                "sets": p["sets"],
                "reps": p["reps"],
                "volume": round(p["volume"], 1),
                "topWeight": p["topWeight"],
                "bestE1rm": p["bestE1rm"],
                "avgIntensityPct": rel,
            }
        )
    minutes = duration_min or len(sets) * 3
    kcal = round(6.0 * bodyweight * minutes / 60) if bodyweight else None
    avg_int = round(sum(intensities) / len(intensities), 1) if intensities else None
    focus = "Strength" if avg_int and avg_int >= 80 else "Hypertrophy" if avg_int and avg_int >= 65 else "Endurance"
    return {
        "totalSets": len(sets),
        "totalReps": int(total_reps),
        "totalVolumeKg": round(total_vol, 1),
        "avgIntensityPct": avg_int,
        "trainingFocus": focus,
        "durationMin": minutes,
        "estimatedCalories": kcal,
        "exercises": exercises,
        "muscleGroups": {k: {"sets": v["sets"], "volume": round(v["volume"], 1)} for k, v in muscles.items()},
    }
