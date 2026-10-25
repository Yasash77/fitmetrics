"""Pydantic request models for FitPulse 24-Formula Analytics API."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Gender = Literal["male", "female"]
Climate = Literal["normal", "hot"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
GoalType = Literal["lose", "weight_loss", "maintain", "maintenance", "gain", "muscle_gain"]


class CaloriesIn(BaseModel):
    age: int = Field(..., ge=10, le=100)
    gender: Gender = "male"
    height: float = Field(..., gt=50, lt=260, description="cm")
    weight: float = Field(..., gt=20, lt=400, description="kg")
    activityLevel: ActivityLevel = "moderate"
    goal: GoalType = "maintain"
    bodyFatPct: Optional[float] = Field(None, ge=3, le=60)


class ActivityBurnIn(BaseModel):
    activity: str = Field("running", examples=["running", "swimming", "cycling"])
    duration: float = Field(45, gt=0, le=600, description="minutes")
    weight: float = Field(74, gt=20, lt=400, description="kg")


class HeartRateIn(BaseModel):
    age: int = Field(21, ge=10, le=100)
    restingHr: int = Field(62, ge=30, le=120)


class IntensityIn(HeartRateIn):
    avgHr: int = Field(172, ge=40, le=230)
    duration: float = Field(45, gt=0, le=600)
    gender: Gender = "male"


class WorkoutAnalysisIn(IntensityIn):
    activity: str = "running"
    weight: float = Field(74, gt=20, lt=400)
    climate: Climate = "normal"


class PaceIn(BaseModel):
    activity: Literal["running", "cycling", "walking", "swimming"] = "running"
    distance: float = Field(5.0, gt=0.1, le=300, description="km")
    duration: float = Field(25.0, gt=1, le=1440, description="minutes")


class Vo2maxIn(BaseModel):
    age: int = Field(21, ge=10, le=100)
    gender: Gender = "male"
    restingHr: int = Field(62, ge=30, le=120)
    maxHr: Optional[int] = Field(None, ge=120, le=230)
    cooperDistance: Optional[float] = Field(None, description="metres in 12-min run")


class StrengthIn(BaseModel):
    exercise: Literal["bench_press", "squat", "deadlift", "overhead_press"] = "bench_press"
    weight: float = Field(80, gt=0, lt=1000)
    reps: int = Field(6, ge=1, le=20)
    bodyweight: Optional[float] = Field(74, gt=20, lt=400)


class SetIn(BaseModel):
    exercise: str = Field(..., examples=["bench_press"])
    weight: float = Field(..., ge=0, lt=1000)
    reps: int = Field(..., ge=1, le=100)


class SessionVolumeIn(BaseModel):
    sets: List[SetIn] = Field(..., min_length=1, max_length=100)
    bodyweight: Optional[float] = Field(74, gt=20, lt=400)
    duration: Optional[float] = Field(None, gt=0, le=300)


class TrainingBalanceIn(BaseModel):
    dailyLoads: List[float] = Field(..., min_length=28, max_length=28)


class ReadinessIn(BaseModel):
    lastLoad: float = Field(121, ge=0, le=1000)
    hoursSince: float = Field(40, ge=0, le=240)
    restingHr: int = Field(61, ge=30, le=120)
    baselineRestingHr: int = Field(62, ge=30, le=120)
    sleepHours: Optional[float] = Field(7.5, ge=0, le=16)
    soreness: Optional[int] = Field(2, ge=1, le=5)


class HydrationIn(BaseModel):
    weight: float = Field(74, gt=20, lt=400)
    duration: float = Field(45, gt=0, le=600)
    intensity: Literal["low", "moderate", "high"] = "moderate"
    climate: Climate = "normal"
    preWeight: Optional[float] = Field(None, gt=20, lt=400)
    postWeight: Optional[float] = Field(None, gt=20, lt=400)


class BmiIn(BaseModel):
    weight: float = Field(74, gt=20, lt=400)
    height: float = Field(178, gt=50, lt=260)


class BodyFatIn(BaseModel):
    gender: Gender = "male"
    height: float = Field(178, gt=50, lt=260)
    neck: float = Field(38, gt=10, lt=80)
    waist: float = Field(84, gt=30, lt=250)
    hip: Optional[float] = Field(None, gt=30, lt=250)
    weight: Optional[float] = Field(74, gt=20, lt=400)


class IdealWeightIn(BaseModel):
    height: float = Field(178, gt=50, lt=260)
    gender: Gender = "male"


class FullAnalysisIn(BaseModel):
    athlete: str = Field("Majit · 23MIC0052", max_length=80)
    age: int = Field(21, ge=10, le=100)
    gender: Gender = "male"
    height: float = Field(178, gt=50, lt=260)
    weight: float = Field(74, gt=20, lt=400)
    neck: float = Field(38, gt=10, lt=80)
    waist: float = Field(84, gt=30, lt=250)
    hip: Optional[float] = Field(None, gt=30, lt=250)
    activityLevel: ActivityLevel = "moderate"
    goal: GoalType = "maintain"
    activity: str = "running"
    duration: float = Field(45, gt=0, le=600)
    avgHr: int = Field(172, ge=40, le=230)
    restingHr: int = Field(62, ge=30, le=120)
    baselineRestingHr: int = Field(62, ge=30, le=120)
    climate: Climate = "normal"
    cooperDistance: Optional[float] = Field(2800, ge=800, le=5000)
    paceActivity: Literal["running", "cycling", "walking", "swimming"] = "running"
    distanceKm: float = Field(5.0, gt=0.1, le=300)
    paceDurationMin: float = Field(25.0, gt=1, le=1440)
    exercise: Literal["bench_press", "squat", "deadlift", "overhead_press"] = "bench_press"
    liftWeight: float = Field(80.0, gt=0, lt=1000)
    liftReps: int = Field(6, ge=1, le=20)
    sets: Optional[List[SetIn]] = None
    dailyLoads: Optional[List[float]] = None
    lastLoad: float = Field(121, ge=0, le=1000)
    hoursSince: float = Field(40, ge=0, le=240)
    sleepHours: float = Field(7.5, ge=0, le=16)
    soreness: int = Field(2, ge=1, le=5)


class KeyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
