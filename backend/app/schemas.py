"""Pydantic request models — reject bad input with 422 before it reaches the engine."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

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
