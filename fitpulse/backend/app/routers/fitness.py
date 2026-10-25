"""/api/v1/fitness/* — All 24 FitPulse Analytical Formulas & Partner Integration Endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from .. import schemas as s
from ..clients import fitmetrics
from ..engine import body, cardio, metabolic, strength, training
from ..security import optional_partner_key, require_api_key

router = APIRouter(prefix="/fitness", tags=["Fitness Analytics (24 Formulas)"])


def ok(data: dict):
    return {"success": True, "data": data}


# ------------------------------------------------------------------ 1. Metabolic & Energy (Formulas 1-4)
@router.post(
    "/calories",
    summary="Formulas 1–3: BMR (Mifflin, Harris-Benedict, Katch-McArdle), TDEE & Macros (Partner Endpoint)",
    dependencies=[Depends(optional_partner_key)],
)
def calories(d: s.CaloriesIn):
    res = metabolic.energy_profile(d.age, d.gender, d.height, d.weight, d.activityLevel, d.goal, d.bodyFatPct)
    # Include top-level bmr & dailyCalories for direct compatibility with partner FitMetrics
    return {"success": True, "bmr": res["bmr"], "dailyCalories": res["dailyCalories"], "data": res}


@router.post("/activity-burn", summary="Formula 4: Activity-Specific Calorie Burn (METs)", dependencies=[Depends(require_api_key)])
def activity_burn(d: s.ActivityBurnIn):
    return ok(metabolic.activity_calories(d.activity, d.duration, d.weight))


# ------------------------------------------------------------------ 2. Cardiovascular & Endurance (Formulas 5-10)
@router.post("/heart-rate-zones", summary="Formulas 5–6: Max HR Models & 5 Karvonen HR Zones", dependencies=[Depends(require_api_key)])
def heart_rate_zones(d: s.HeartRateIn):
    return ok(cardio.hr_zones(d.age, d.restingHr))


@router.post("/vo2max", summary="Formulas 7, 8 & 24: VO2max (Cooper & Uth) + Fitness Age", dependencies=[Depends(require_api_key)])
def vo2max(d: s.Vo2maxIn):
    return ok(cardio.vo2max_analysis(d.age, d.gender, d.restingHr, d.maxHr, d.cooperDistance))


@router.post("/pace", summary="Formulas 9–10: Pace, Speed & Riegel Race Time Predictions", dependencies=[Depends(require_api_key)])
def pace(d: s.PaceIn):
    return ok(cardio.pace_and_predictions(d.activity, d.distance, d.duration))


# ------------------------------------------------------------------ 3. Strength & Power (Formulas 11-15)
@router.post("/strength-analysis", summary="Formulas 11–14: 1RM (Epley/Brzycki), Relative Strength & Level", dependencies=[Depends(require_api_key)])
def strength_analysis(d: s.StrengthIn):
    return ok(strength.analyse_lift(d.exercise, d.weight, d.reps, d.bodyweight))


@router.post("/session-volume", summary="Formula 15: Gym Session Volume & Muscle Breakdown", dependencies=[Depends(require_api_key)])
def session_volume(d: s.SessionVolumeIn):
    return ok(strength.session_volume([x.model_dump() for x in d.sets], d.bodyweight, d.duration))


# ------------------------------------------------------------------ 4. Training Load & Recovery (Formulas 16-20)
@router.post("/workout-analysis", summary="Formulas 4, 16 & 20: Full Workout Load, TRIMP, Intensity & Hydration", dependencies=[Depends(require_api_key)])
def workout_analysis(d: s.WorkoutAnalysisIn):
    return ok(training.analyse_workout(d.activity, d.duration, d.weight, d.age, d.restingHr, d.avgHr, d.gender, d.climate))


@router.post("/training-balance", summary="Formulas 17–18: ACWR Injury Risk, Training Monotony & Strain", dependencies=[Depends(require_api_key)])
def training_balance(d: s.TrainingBalanceIn):
    return ok(training.training_balance(d.dailyLoads))


@router.post("/readiness", summary="Formulas 19–20: Daily Readiness Score & Recovery Recommendation", dependencies=[Depends(require_api_key)])
def readiness(d: s.ReadinessIn):
    return ok(training.readiness(d.lastLoad, d.hoursSince, d.restingHr, d.baselineRestingHr, d.sleepHours, d.soreness))


@router.post("/hydration", summary="Formula 20: ACSM Sweat-Loss & Electrolyte Replacement Plan", dependencies=[Depends(require_api_key)])
def hydration(d: s.HydrationIn):
    return ok(training.fluid_plan(d.weight, d.duration, d.intensity, d.climate, d.preWeight, d.postWeight))


# ------------------------------------------------------------------ 5. Body Composition & Master Synthesis (Formulas 21-24)
@router.post("/bmi", summary="Formula 21: BMI, BMI Prime & Ponderal Index", dependencies=[Depends(require_api_key)])
def bmi(d: s.BmiIn):
    return ok(body.bmi_analysis(d.weight, d.height))


@router.post("/body-fat", summary="Formula 22: U.S. Navy Body Fat %, Fat Mass & Lean Mass", dependencies=[Depends(require_api_key)])
def body_fat(d: s.BodyFatIn):
    return ok(body.body_fat_navy(d.gender, d.height, d.neck, d.waist, d.hip, d.weight))


@router.post("/ideal-weight", summary="Formula 23: Ideal Body Weight (Hamwi, Devine, Robinson, Miller)", dependencies=[Depends(require_api_key)])
def ideal_weight(d: s.IdealWeightIn):
    return ok(body.ideal_body_weight(d.height, d.gender))


@router.post("/full-analysis", summary="All 24 Analytical Formulas & Methods in One Master Report", dependencies=[Depends(require_api_key)])
def full_analysis(d: s.FullAnalysisIn):
    payload = d.model_dump()
    if payload.get("sets"):
        payload["sets"] = [x.model_dump() if hasattr(x, "model_dump") else x for x in payload["sets"]]
    return ok(body.comprehensive_24_analysis(payload))


# ------------------------------------------------------------------ Partner Service Integration (FitMetrics 23MIC0060)
@router.post("/partner-sync", summary="Combined Energy + Workout Sync with Partner FitMetrics API", dependencies=[Depends(require_api_key)])
async def partner_sync(d: s.WorkoutAnalysisIn):
    energy = metabolic.energy_profile(d.age, d.gender, d.height if hasattr(d, "height") else 178, d.weight, "moderate", "maintain")
    try:
        partner_workout = await fitmetrics.fetch_partner_workout(
            {
                "activity": d.activity,
                "duration": d.duration,
                "weight": d.weight,
                "age": d.age,
                "restingHr": d.restingHr,
                "avgHr": d.avgHr,
                "gender": d.gender,
                "climate": d.climate,
            }
        )
    except fitmetrics.PartnerUnavailable:
        raise HTTPException(503, "Partner FitMetrics API unavailable — workout telemetry could not be fetched")

    burned = partner_workout.get("caloriesBurned", 0)
    total_need = energy["tdee"] + burned
    return ok(
        {
            "partnerService": "FitMetrics API (23MIC0060)",
            "baselineTdee": energy["tdee"],
            "bmrMifflin": energy["bmrMifflinStJeor"],
            "workoutBurnFromFitMetrics": burned,
            "workoutZoneFromFitMetrics": partner_workout.get("zone"),
            "trainingLoadFromFitMetrics": partner_workout.get("trainingLoad"),
            "adjustedDailyCalorieTarget": total_need,
        }
    )
