"""/api/v1/fitness/* — energy needs, body composition, goal planning and partner sync.

FitPulse answers "how much energy does this person NEED, and where is their body heading?".
Workout analytics (calories burned, HR zones, training load, injury risk) come from FitMetrics."""
from fastapi import APIRouter, Depends, HTTPException

from .. import schemas as s
from .. import store
from ..clients import fitmetrics
from ..engine import body, goals, metabolic
from ..security import optional_partner_key, require_api_key

router = APIRouter(prefix="/fitness", tags=["Energy & Body"])


def ok(data: dict):
    return {"success": True, "data": data}


@router.post("/calories", summary="BMR (Mifflin, Harris-Benedict, Katch-McArdle), TDEE & macros — used by FitMetrics",
             dependencies=[Depends(optional_partner_key)])
def calories(d: s.CaloriesIn):
    res = metabolic.energy_profile(d.age, d.gender, d.height, d.weight, d.activityLevel, d.goal, d.bodyFatPct)
    # top-level bmr & dailyCalories kept for direct compatibility with the partner FitMetrics client
    return {"success": True, "bmr": res["bmr"], "dailyCalories": res["dailyCalories"], "data": res}


@router.post("/bmi", summary="BMI, BMI Prime & Ponderal Index", dependencies=[Depends(require_api_key)])
def bmi(d: s.BmiIn):
    return ok(body.bmi_analysis(d.weight, d.height))


@router.post("/body-fat", summary="U.S. Navy body fat %, fat mass & lean mass", dependencies=[Depends(require_api_key)])
def body_fat(d: s.BodyFatIn):
    return ok(body.body_fat_navy(d.gender, d.height, d.neck, d.waist, d.hip, d.weight))


@router.post("/ideal-weight", summary="Ideal body weight (Hamwi, Devine, Robinson, Miller)", dependencies=[Depends(require_api_key)])
def ideal_weight(d: s.IdealWeightIn):
    return ok(body.ideal_body_weight(d.height, d.gender))


@router.post("/goal-plan", summary="Target weight + timeframe → daily calories, macros, safety", dependencies=[Depends(require_api_key)])
def goal_plan(d: s.GoalPlanIn):
    return ok(goals.goal_plan(d.age, d.gender, d.height, d.weight, d.activityLevel, d.targetWeight, d.weeks))


def build_profile_report(d: s.ProfileReportIn) -> dict:
    out = {"athlete": d.athlete,
           "energy": metabolic.energy_profile(d.age, d.gender, d.height, d.weight, d.activityLevel, d.goal),
           "bmi": body.bmi_analysis(d.weight, d.height),
           "idealWeight": body.ideal_body_weight(d.height, d.gender)}
    if d.neck and d.waist:
        out["bodyFat"] = body.body_fat_navy(d.gender, d.height, d.neck, d.waist, d.hip, d.weight)
    if d.targetWeight and d.weeks:
        out["goalPlan"] = goals.goal_plan(d.age, d.gender, d.height, d.weight, d.activityLevel, d.targetWeight, d.weeks)
    if d.profile:
        out["progress"] = {"measurements": store.measurements(d.profile)[-12:], "workouts": store.workouts(d.profile)[-10:]}
    return out


@router.post("/profile-report", summary="Energy + body composition + goal plan in one report", dependencies=[Depends(require_api_key)])
def profile_report(d: s.ProfileReportIn):
    return ok(build_profile_report(d))


@router.post("/partner-sync", summary="Today's energy target adjusted with a workout analysed by FitMetrics",
             dependencies=[Depends(require_api_key)])
async def partner_sync(d: s.PartnerSyncIn):
    energy = metabolic.energy_profile(d.age, d.gender, d.height, d.weight, d.activityLevel, "maintain")
    try:
        w = await fitmetrics.workout_analysis({"activity": d.activity, "duration": d.duration, "weight": d.weight,
                                               "age": d.age, "restingHr": d.restingHr, "avgHr": d.avgHr,
                                               "gender": d.gender, "climate": d.climate})
    except fitmetrics.PartnerUnavailable:
        raise HTTPException(503, "Partner FitMetrics API unavailable — workout could not be analysed")
    except ValueError as exc:
        raise HTTPException(400, f"FitMetrics rejected the workout: {exc}")
    burned = w.get("caloriesBurned", 0)
    return ok({"partnerService": "FitMetrics API (23MIC0060)", "baselineTdee": energy["tdee"],
               "bmrMifflin": energy["bmrMifflinStJeor"], "workoutBurnFromFitMetrics": burned,
               "workoutZoneFromFitMetrics": w.get("zone"), "trainingLoadFromFitMetrics": w.get("trainingLoad"),
               "recoveryHoursFromFitMetrics": w.get("recoveryHours"),
               "adjustedDailyCalorieTarget": energy["tdee"] + burned})
