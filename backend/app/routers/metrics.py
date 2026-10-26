"""/api/v1/metrics/* — all FitMetrics calculation endpoints (API key required)."""
from fastapi import APIRouter, Depends, HTTPException

from .. import schemas as s
from ..clients import fitpulse
from ..engine import cardio, strength, training, workout
from ..security import require_api_key

router = APIRouter(prefix="/metrics", tags=["Metrics"], dependencies=[Depends(require_api_key)])


def ok(data):
    return {"success": True, "data": data}


# ---------------------------------------------------------------- workout
@router.post("/workout-analysis", summary="Full workout report (flagship)")
def workout_analysis(d: s.WorkoutAnalysisIn):
    return ok(workout.analyse(d.activity, d.duration, d.weight, d.age, d.restingHr, d.avgHr, d.gender, d.climate))


@router.post("/workout-intensity", summary="%HRR, zone, TRIMP training load")
def workout_intensity(d: s.IntensityIn):
    return ok(workout.intensity(d.age, d.restingHr, d.avgHr, d.duration, d.gender))


@router.post("/calories-burned", summary="Calories burned for an activity (MET)")
def calories_burned(d: s.CaloriesBurnedIn):
    return ok({"activity": d.activity, "met": workout.MET_TABLE.get(d.activity), "durationMin": d.duration,
               "caloriesBurned": workout.calories_burned(d.activity, d.duration, d.weight)})


@router.post("/heart-rate-zones", summary="Five Karvonen heart-rate zones")
def heart_rate_zones(d: s.HeartRateIn):
    return ok(workout.hr_zones(d.age, d.restingHr))


@router.post("/hydration", summary="Post-workout fluid replacement plan")
def hydration(d: s.HydrationIn):
    return ok(workout.fluid_plan(d.weight, d.duration, d.intensity, d.climate, d.preWeight, d.postWeight))


# ---------------------------------------------------------------- training management
@router.post("/training-balance", summary="ACWR injury-risk, monotony & strain")
def training_balance(d: s.TrainingBalanceIn):
    return ok(training.training_balance(d.dailyLoads))


@router.post("/readiness", summary="Readiness score & today's session recommendation")
def readiness(d: s.ReadinessIn):
    return ok(training.readiness(d.lastLoad, d.hoursSince, d.restingHr, d.baselineRestingHr, d.sleepHours, d.soreness))


# ---------------------------------------------------------------- cardio
@router.post("/pace", summary="Pace, speed and race-time predictions")
def pace(d: s.PaceIn):
    return ok(cardio.pace(d.activity, d.distance, d.duration))


@router.post("/vo2max", summary="VO2max estimate, rating and fitness age")
def vo2max(d: s.Vo2maxIn):
    return ok(cardio.vo2max(d.age, d.gender, d.restingHr, d.maxHr, d.cooperDistance))


# ---------------------------------------------------------------- strength
@router.post("/strength-analysis", summary="1RM, training loads, strength level")
def strength_analysis(d: s.StrengthIn):
    return ok(strength.analyse_lift(d.exercise, d.weight, d.reps, d.bodyweight))


@router.post("/session-volume", summary="Strength session volume & muscle breakdown")
def session_volume(d: s.SessionVolumeIn):
    return ok(strength.session_volume([x.model_dump() for x in d.sets], d.bodyweight, d.duration))


# ---------------------------------------------------------------- partner integration
@router.post("/energy-balance", summary="Net calories — maintenance from FitPulse API")
async def energy_balance(d: s.EnergyBalanceIn):
    try:
        maintenance = await fitpulse.maintenance_calories(d.age, d.gender, d.height, d.weight, d.activityLevel)
    except fitpulse.PartnerUnavailable:
        raise HTTPException(503, "FitPulse service unavailable — maintenance calories could not be fetched")
    exercise = sum(workout.calories_burned(w.activity, w.duration, w.weight) for w in d.workouts)
    net = d.caloriesEaten - maintenance - exercise
    return ok({"maintenanceCalories": maintenance, "maintenanceSource": "FitPulse API",
               "exerciseCalories": exercise, "caloriesEaten": d.caloriesEaten, "netBalance": round(net),
               "status": "surplus" if net > 0 else "deficit",
               "projectedWeeklyChangeKg": round(net * 7 / 7700, 2)})
