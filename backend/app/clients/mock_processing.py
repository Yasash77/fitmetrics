"""DEVELOPMENT MOCK — NOT Maajith's processing system.

Used only when PLAN_SERVICE_MODE=mock and no PLAN_SERVICE_URL is configured. It fills fixed session
templates into the requested schedule so the plan screens can be built and tested end-to-end before
the real processing endpoint exists. It performs no personalised analysis and must never be presented
as a real recommendation: every response carries generatedBy.isMock = true and a warning, and the UI
shows a "Development mock" banner on any plan produced here.

Its output follows docs/PLAN_API_CONTRACT.md exactly, so swapping in the live service needs no UI change."""
from __future__ import annotations

from typing import List

MOCK_SYSTEM = "development-mock"
DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
SPREAD = {1: ["wed"], 2: ["tue", "fri"], 3: ["mon", "wed", "fri"], 4: ["mon", "tue", "thu", "sat"],
          5: ["mon", "tue", "wed", "fri", "sat"], 6: ["mon", "tue", "wed", "thu", "fri", "sat"], 7: DAY_ORDER}


def _i(name, **kw):
    return {"name": name, **kw}


def _warm(minutes: int) -> dict:
    return {"name": "Warm-up", "type": "warmup", "items": [_i("Easy movement + dynamic mobility", durationSec=minutes * 60)]}


def _cool() -> dict:
    return {"name": "Cool-down", "type": "cooldown", "items": [_i("Easy movement and breathing", durationSec=300)]}


# Fixed templates (placeholders). Keys are discipline ids from onboarding_config.json.
def _gym(m, lvl, wk):
    sets = 2 if lvl == "beginner" else 3
    return [_warm(8), {"name": "Main lifts", "type": "main", "items": [
        _i("Goblet or back squat", sets=sets, reps="8-10", load="RPE 7", restSec=120),
        _i("Dumbbell bench press", sets=sets, reps="8-10", load="RPE 7", restSec=90),
        _i("Seated cable row", sets=sets, reps="10-12", load="RPE 7", restSec=90)]},
        {"name": "Accessories", "type": "accessory", "items": [
            _i("Romanian deadlift", sets=2, reps="10", load="RPE 6", restSec=90),
            _i("Plank", sets=2, durationSec=30, restSec=45)]}, _cool()]


def _swim(m, lvl, wk):
    return [{"name": "Warm-up", "type": "warmup", "items": [_i("Easy swim", distanceM=200, stroke="choice")]},
            {"name": "Drills", "type": "skill", "items": [_i("Catch-up drill", sets=4, distanceM=25, restSec=20, stroke="freestyle")]},
            {"name": "Main set", "type": "intervals", "items": [
                _i("Steady freestyle", sets=6 if lvl != "beginner" else 4, distanceM=50, restSec=20, pace="moderate")]},
            {"name": "Cool-down", "type": "cooldown", "items": [_i("Easy backstroke", distanceM=100, stroke="backstroke")]}]


def _run(m, lvl, wk):
    if wk % 2:
        return [_warm(10), {"name": "Easy run", "type": "main",
                            "items": [_i("Conversational pace run", durationSec=max(m - 15, 10) * 60, zone="Zone 2")]}, _cool()]
    return [_warm(10), {"name": "Intervals", "type": "intervals", "rounds": 5, "workSec": 120, "restSec": 90,
                        "items": [_i("Brisk run", zone="Zone 4"), _i("Walk / jog recovery", zone="Zone 1")]}, _cool()]


def _cycle(m, lvl, wk):
    return [_warm(10), {"name": "Endurance ride", "type": "main",
                        "items": [_i("Steady cadence 85-95 rpm", durationSec=max(m - 15, 10) * 60, zone="Zone 2")]}, _cool()]


def _hiit(m, lvl, wk):
    return [_warm(6), {"name": "Intervals", "type": "circuit", "rounds": 3 if lvl == "beginner" else 4, "workSec": 30, "restSec": 30,
                       "items": [_i("Squat to reach"), _i("Mountain climbers"), _i("Reverse lunges"), _i("Push-ups (incline ok)")]}, _cool()]


def _hyrox(m, lvl, wk):
    return [_warm(8), {"name": "Station practice", "type": "stations", "rounds": 2, "items": [
        _i("Run", distanceM=500), _i("SkiErg", distanceM=250), _i("Run", distanceM=500), _i("Wall balls", reps="15"),
        _i("Run", distanceM=500), _i("Farmers carry", distanceM=50, load="moderate")]}, _cool()]


def _cali(m, lvl, wk):
    return [_warm(8), {"name": "Skill practice", "type": "skill", "items": [_i("Dead hang / scapular pulls", sets=3, durationSec=20, restSec=60)]},
            {"name": "Strength", "type": "main", "items": [
                _i("Pull-up progression", sets=3, reps="3-6", restSec=120), _i("Push-up progression", sets=3, reps="6-10", restSec=90),
                _i("Split squat", sets=3, reps="8 each", restSec=60)]}, _cool()]


def _yoga(m, lvl, wk):
    return [{"name": "Flow", "type": "flow", "items": [
        _i("Cat-cow", durationSec=60), _i("Downward dog", durationSec=45), _i("Low lunge (each side)", durationSec=60),
        _i("Warrior II (each side)", durationSec=45), _i("Child's pose", durationSec=60), _i("Supine twist", durationSec=60)]}]


def _mob(m, lvl, wk):
    return [{"name": "Mobility circuit", "type": "flow", "items": [
        _i("90/90 hip switches", sets=2, reps="8"), _i("Thoracic open books", sets=2, reps="8 each"),
        _i("Ankle rocks", sets=2, reps="10 each"), _i("Hamstring floss", sets=2, reps="10 each")]}]


def _sport(m, lvl, wk):
    return [_warm(10), {"name": "Speed & agility", "type": "intervals", "rounds": 6, "workSec": 10, "restSec": 50,
                        "items": [_i("Acceleration sprint 20 m")]},
            {"name": "Strength", "type": "main", "items": [_i("Split squat", sets=3, reps="8"), _i("Push press", sets=3, reps="6")]}, _cool()]


def _circuit(m, lvl, wk):
    return [_warm(6), {"name": "Circuit", "type": "circuit", "rounds": 3, "workSec": 40, "restSec": 20,
                       "items": [_i("Step-ups"), _i("Dumbbell row"), _i("Glute bridge"), _i("Dead bug")]}, _cool()]


def _bands(m, lvl, wk):
    return [_warm(5), {"name": "Band strength", "type": "main", "items": [
        _i("Band squat", sets=3, reps="12"), _i("Band row", sets=3, reps="12"), _i("Band chest press", sets=3, reps="12"),
        _i("Band pull-apart", sets=2, reps="15")]}, _cool()]


def _home(m, lvl, wk):
    return [_warm(5), {"name": "Bodyweight circuit", "type": "circuit", "rounds": 3, "workSec": 40, "restSec": 20,
                       "items": [_i("Squats"), _i("Incline push-ups"), _i("Glute bridge"), _i("Side plank")]}, _cool()]


TEMPLATES = {"gym": _gym, "swimming": _swim, "running": _run, "cycling": _cycle, "hiit": _hiit, "hyrox": _hyrox,
             "calisthenics": _cali, "yoga": _yoga, "mobility": _mob, "sports": _sport, "circuit": _circuit,
             "bands": _bands, "home": _home}
TITLES = {"gym": "Strength session", "swimming": "Pool session", "running": "Run", "cycling": "Ride", "hiit": "HIIT",
          "hyrox": "HYROX stations", "calisthenics": "Calisthenics", "yoga": "Yoga flow", "mobility": "Mobility",
          "sports": "Sport conditioning", "circuit": "Circuit", "bands": "Band workout", "home": "Home workout"}


def _days(av: dict) -> List[str]:
    n = int(av.get("daysPerWeek") or 3)
    pref = [d for d in DAY_ORDER if d in (av.get("preferredDays") or [])]
    if len(pref) >= n:
        return pref[:n]
    return SPREAD[max(1, min(7, n))]


def generate(payload: dict) -> dict:
    weeks_total = int(round(payload["timeline"].get("weeks") or 4))
    shown = min(weeks_total, 4)                      # the placeholder only fills the first 4 weeks
    discs = [d["id"] for d in payload["disciplines"]] or ["home"]
    lvl = payload["experience"].get("level") or "beginner"
    minutes = payload["availability"].get("sessionMinutes") or 45
    days = _days(payload["availability"])
    weeks = []
    for w in range(1, shown + 1):
        sessions = []
        for i, day in enumerate(days):
            d = discs[(i + w - 1) % len(discs)]
            sessions.append({"id": f"w{w}s{i + 1}", "day": day, "discipline": d, "title": TITLES[d],
                             "durationMin": minutes, "intensity": "easy" if w == 4 else "moderate",
                             "blocks": TEMPLATES[d](minutes, lvl, w)})
        weeks.append({"week": w, "focus": "Lighter week" if w == 4 else "Template week", "sessions": sessions})
    return {
        "planId": f"mock-{payload['requestId']}",
        "status": "ready",
        "generatedBy": {"system": MOCK_SYSTEM, "version": "0", "isMock": True},
        "summary": {"title": "Development placeholder plan", "weeks": weeks_total, "sessionsPerWeek": len(days),
                    "primaryDiscipline": discs[0],
                    "overview": "Fixed templates arranged into your schedule so the app can be tested. "
                                "This is not a personalised recommendation."},
        "weeks": weeks,
        "guidance": [],
        "warnings": ["Development mock: generated by a local placeholder, not by Maajith's processing system. "
                     "Do not use it as training advice."] +
                    ([f"Only the first {shown} of {weeks_total} weeks are filled in by the placeholder."]
                     if weeks_total > shown else []),
    }
