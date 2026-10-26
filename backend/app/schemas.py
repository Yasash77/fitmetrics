"""Pydantic request models — reject bad input with 422 before it reaches the engine."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Gender = Literal["male", "female"]
Climate = Literal["normal", "hot"]


class CaloriesBurnedIn(BaseModel):
    activity: str = Field(..., examples=["running"])
    duration: float = Field(..., gt=0, le=600, description="minutes")
    weight: float = Field(..., gt=20, lt=400, description="kg")


class HeartRateIn(BaseModel):
    age: int = Field(..., ge=10, le=100)
    restingHr: int = Field(..., ge=30, le=120)


class IntensityIn(HeartRateIn):
    avgHr: int = Field(..., ge=40, le=230)
    duration: float = Field(..., gt=0, le=600)
    gender: Gender = "male"


class WorkoutAnalysisIn(IntensityIn):
    activity: str
    weight: float = Field(..., gt=20, lt=400)
    climate: Climate = "normal"


class StrengthIn(BaseModel):
    exercise: Literal["bench_press", "squat", "deadlift", "overhead_press"] = "bench_press"
    weight: float = Field(..., gt=0, lt=1000)
    reps: int = Field(..., ge=1, le=20)
    bodyweight: Optional[float] = Field(None, gt=20, lt=400)


class SetIn(BaseModel):
    exercise: str = Field(..., examples=["bench_press"])
    weight: float = Field(..., ge=0, lt=1000)
    reps: int = Field(..., ge=1, le=100)


class SessionVolumeIn(BaseModel):
    sets: List[SetIn] = Field(..., min_length=1, max_length=100)
    bodyweight: Optional[float] = Field(None, gt=20, lt=400)
    duration: Optional[float] = Field(None, gt=0, le=300)


class HydrationIn(BaseModel):
    weight: float = Field(..., gt=20, lt=400)
    duration: float = Field(..., gt=0, le=600)
    intensity: Literal["low", "moderate", "high"] = "moderate"
    climate: Climate = "normal"
    preWeight: Optional[float] = Field(None, gt=20, lt=400)
    postWeight: Optional[float] = Field(None, gt=20, lt=400)


class TrainingBalanceIn(BaseModel):
    dailyLoads: List[float] = Field(..., min_length=28, max_length=28,
                                    description="28 daily training loads (TRIMP), oldest first")


class ReadinessIn(BaseModel):
    lastLoad: float = Field(..., ge=0, le=1000, description="training load of the last session")
    hoursSince: float = Field(..., ge=0, le=240)
    restingHr: int = Field(..., ge=30, le=120, description="this morning's resting HR")
    baselineRestingHr: int = Field(..., ge=30, le=120)
    sleepHours: Optional[float] = Field(None, ge=0, le=16)
    soreness: Optional[int] = Field(None, ge=1, le=5, description="1 = none, 5 = very sore")


class PaceIn(BaseModel):
    activity: Literal["running", "cycling", "walking", "swimming"] = "running"
    distance: float = Field(..., gt=0.1, le=300, description="km")
    duration: float = Field(..., gt=1, le=1440, description="minutes")


class Vo2maxIn(BaseModel):
    age: int = Field(..., ge=10, le=100)
    gender: Gender
    restingHr: int = Field(..., ge=30, le=120)
    maxHr: Optional[int] = Field(None, ge=120, le=230, description="measured max HR (optional)")
    cooperDistance: Optional[float] = Field(None, description="metres covered in a 12-min run (optional)")


class EnergyBalanceIn(BaseModel):
    age: int = Field(..., ge=10, le=100)
    gender: Gender
    height: float = Field(..., gt=50, lt=260)
    weight: float = Field(..., gt=20, lt=400)
    activityLevel: Literal["sedentary", "light", "moderate", "active", "very_active"]
    caloriesEaten: float = Field(..., ge=0, le=10000)
    workouts: List[CaloriesBurnedIn] = []


class KeyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class WorkoutReportIn(WorkoutAnalysisIn):
    athlete: str = Field("Athlete", max_length=60)
    strength: Optional[StrengthIn] = None


# ============================================================================================
# FitPulse user platform — request models and the plan-contract response model
# ============================================================================================
EMAIL_RE = r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$"


def Email():
    return Field(..., max_length=254, pattern=EMAIL_RE)


# ------------------------------------------------------------------ auth
class RegisterIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    email: str = Email()
    password: str = Field(..., min_length=1, max_length=200)


class LoginIn(BaseModel):
    email: str = Email()
    password: str = Field(..., min_length=1, max_length=200)


class ForgotIn(BaseModel):
    email: str = Email()


class ResetIn(BaseModel):
    token: str = Field(..., min_length=20, max_length=200)
    password: str = Field(..., min_length=1, max_length=200)


class ChangePasswordIn(BaseModel):
    currentPassword: str = Field(..., min_length=1, max_length=200)
    newPassword: str = Field(..., min_length=1, max_length=200)


class DeleteAccountIn(BaseModel):
    password: str = Field(..., min_length=1, max_length=200)


class AccountIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


# ------------------------------------------------------------------ profile
class ProfileIn(BaseModel):
    data: Dict[str, Any]
    version: int = Field(..., ge=0, description="version you last loaded — protects against overwriting newer edits")


# ------------------------------------------------------------------ plans
class PlanRequestIn(BaseModel):
    idempotencyKey: str = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")


# ------------------------------------------------------------------ workouts & measurements
Discipline = Literal["gym", "swimming", "hiit", "hyrox", "running", "cycling", "calisthenics", "yoga",
                     "mobility", "sports", "circuit", "bands", "home", "other"]


class ExerciseLog(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    sets: Optional[int] = Field(None, ge=0, le=50)
    reps: Optional[str] = Field(None, max_length=20)
    loadKg: Optional[float] = Field(None, ge=0, le=1000)
    distanceM: Optional[float] = Field(None, ge=0, le=500000)
    durationSec: Optional[int] = Field(None, ge=0, le=86400)
    notes: Optional[str] = Field(None, max_length=200)


class WorkoutIn(BaseModel):
    clientId: str = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$",
                          description="random id from the browser — retries with the same id never create duplicates")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    discipline: Discipline
    title: str = Field(..., min_length=1, max_length=80)
    durationMin: float = Field(..., gt=0, le=600)
    rpe: Optional[int] = Field(None, ge=1, le=10, description="session effort 1-10")
    avgHr: Optional[int] = Field(None, ge=40, le=230)
    distanceKm: Optional[float] = Field(None, ge=0, le=1000)
    notes: Optional[str] = Field(None, max_length=1000)
    exercises: List[ExerciseLog] = Field(default_factory=list, max_length=40)
    planId: Optional[str] = Field(None, max_length=64)
    sessionId: Optional[str] = Field(None, max_length=64)


class MeasurementIn(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    weight: Optional[float] = Field(None, gt=30, lt=300, description="kg")
    waist: Optional[float] = Field(None, gt=40, lt=250, description="cm")
    bodyFat: Optional[float] = Field(None, ge=3, le=60, description="%")


# ------------------------------------------------------------------ plan contract (response side)
# Mirrors docs/PLAN_API_CONTRACT.md. Unknown extra properties are allowed (forward compatible), but the
# core structure must be present or the plan is rejected rather than rendered half-broken.
class _Loose(BaseModel):
    model_config = ConfigDict(extra="allow")


class PlanItem(_Loose):
    name: str
    sets: Optional[int] = None
    reps: Optional[str] = None
    load: Optional[str] = None
    restSec: Optional[int] = None
    distanceM: Optional[float] = None
    durationSec: Optional[int] = None
    pace: Optional[str] = None
    zone: Optional[str] = None
    stroke: Optional[str] = None
    notes: Optional[str] = None


class PlanBlock(_Loose):
    name: str
    type: Literal["warmup", "main", "accessory", "intervals", "circuit", "stations", "skill", "flow", "cooldown", "other"] = "main"
    rounds: Optional[int] = None
    workSec: Optional[int] = None
    restSec: Optional[int] = None
    items: List[PlanItem] = Field(default_factory=list)


class PlanSession(_Loose):
    id: str
    day: Optional[str] = None
    discipline: str
    title: str
    durationMin: Optional[float] = None
    intensity: Optional[str] = None
    blocks: List[PlanBlock] = Field(default_factory=list)
    notes: Optional[str] = None


class PlanWeek(_Loose):
    week: int
    focus: Optional[str] = None
    sessions: List[PlanSession]


class PlanSummary(_Loose):
    title: str
    overview: Optional[str] = None
    weeks: int
    sessionsPerWeek: Optional[float] = None
    primaryDiscipline: Optional[str] = None


class GeneratedBy(_Loose):
    system: str
    version: Optional[str] = None
    isMock: bool = False


class PlanResponse(_Loose):
    planId: str
    status: Literal["ready", "processing", "failed"]
    generatedBy: GeneratedBy
    summary: Optional[PlanSummary] = None
    weeks: List[PlanWeek] = Field(default_factory=list)
    guidance: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None
