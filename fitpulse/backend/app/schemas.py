"""Pydantic request models for the FitPulse API — reject bad input with 422 before it reaches the engine."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Gender = Literal["male", "female"]
Climate = Literal["normal", "hot"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
GoalType = Literal["lose", "weight_loss", "maintain", "maintenance", "gain", "muscle_gain"]
def Profile():
    return Field("demo", min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_\-]+$",
                 description="progress profile name (e.g. your name)")


def Day():
    return Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD (defaults to today)")


# ------------------------------------------------------------------ energy & body
class CaloriesIn(BaseModel):
    age: int = Field(..., ge=10, le=100)
    gender: Gender = "male"
    height: float = Field(..., gt=50, lt=260, description="cm")
    weight: float = Field(..., gt=20, lt=400, description="kg")
    activityLevel: ActivityLevel = "moderate"
    goal: GoalType = "maintain"
    bodyFatPct: Optional[float] = Field(None, ge=3, le=60)


class BmiIn(BaseModel):
    weight: float = Field(..., gt=20, lt=400)
    height: float = Field(..., gt=50, lt=260)


class BodyFatIn(BaseModel):
    gender: Gender = "male"
    height: float = Field(..., gt=50, lt=260)
    neck: float = Field(..., gt=10, lt=80)
    waist: float = Field(..., gt=30, lt=250)
    hip: Optional[float] = Field(None, gt=30, lt=250)
    weight: Optional[float] = Field(None, gt=20, lt=400)


class IdealWeightIn(BaseModel):
    height: float = Field(..., gt=50, lt=260)
    gender: Gender = "male"


class GoalPlanIn(BaseModel):
    age: int = Field(..., ge=10, le=100)
    gender: Gender = "male"
    height: float = Field(..., gt=50, lt=260)
    weight: float = Field(..., gt=20, lt=400)
    activityLevel: ActivityLevel = "moderate"
    targetWeight: float = Field(..., gt=20, lt=400)
    weeks: float = Field(..., gt=0, le=104)


class ProfileReportIn(BaseModel):
    athlete: str = Field("Athlete", max_length=80)
    age: int = Field(..., ge=10, le=100)
    gender: Gender = "male"
    height: float = Field(..., gt=50, lt=260)
    weight: float = Field(..., gt=20, lt=400)
    activityLevel: ActivityLevel = "moderate"
    goal: GoalType = "maintain"
    neck: Optional[float] = Field(None, gt=10, lt=80)
    waist: Optional[float] = Field(None, gt=30, lt=250)
    hip: Optional[float] = Field(None, gt=30, lt=250)
    targetWeight: Optional[float] = Field(None, gt=20, lt=400)
    weeks: Optional[float] = Field(None, gt=0, le=104)
    profile: Optional[str] = Field(None, max_length=40, pattern=r"^[A-Za-z0-9_\-]+$")


class PartnerSyncIn(BaseModel):
    age: int = Field(..., ge=10, le=100)
    gender: Gender = "male"
    height: float = Field(..., gt=50, lt=260)
    weight: float = Field(..., gt=20, lt=400)
    activityLevel: ActivityLevel = "moderate"
    activity: str = Field("running")
    duration: float = Field(..., gt=0, le=600)
    avgHr: int = Field(..., ge=40, le=230)
    restingHr: int = Field(..., ge=30, le=120)
    climate: Climate = "normal"


# ------------------------------------------------------------------ progress tracking
class MeasurementIn(BaseModel):
    profile: str = Profile()
    date: Optional[str] = Day()
    weight: float = Field(..., gt=20, lt=400)
    waist: Optional[float] = Field(None, gt=30, lt=250)
    bodyFat: Optional[float] = Field(None, ge=2, le=70)


class GoalIn(BaseModel):
    profile: str = Profile()
    targetWeight: float = Field(..., gt=20, lt=400)
    targetDate: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


class WorkoutLogIn(BaseModel):
    profile: str = Profile()
    date: Optional[str] = Day()
    activity: str = Field(..., examples=["running"])
    duration: float = Field(..., gt=0, le=600)
    avgHr: int = Field(..., ge=40, le=230)
    restingHr: int = Field(..., ge=30, le=120)
    age: int = Field(..., ge=10, le=100)
    weight: float = Field(..., gt=20, lt=400)
    gender: Gender = "male"
    climate: Climate = "normal"


class SeedIn(BaseModel):
    profile: str = Profile()
    age: int = Field(21, ge=10, le=100)
    restingHr: int = Field(62, ge=30, le=120)


class KeyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
