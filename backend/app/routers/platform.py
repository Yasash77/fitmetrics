"""/api/* — the FitPulse user platform (Yasash): accounts, onboarding, plans, workout logging, progress.

Responsibilities are split on purpose:
  * this platform COLLECTS the user's data and PRESENTS results;
  * Maajith's processing system ANALYSES the profile and returns the personalised plan — reached only
    through clients/processing.py (live HTTP, a clearly labelled development mock, or an honest 503);
  * Maajith's FitPulse API supplies real energy needs / goal-plan safety (clients/fitpulse.py);
  * FitMetrics' own engine (this repository) analyses logged workouts and training balance.

Every private query is scoped to the user id from the server-side session — never from the request body."""
from __future__ import annotations

import secrets
import smtplib
import ssl
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from .. import config, db, onboarding
from .. import schemas as s
from .. import security as sec
from ..clients import fitpulse, processing
from ..engine import training, workout
from ..engine.workout import MetricError

router = APIRouter(prefix="/api", tags=["FitPulse platform"])

# FitMetrics' MET table knows these activity names; platform disciplines map onto the closest one.
DISCIPLINE_TO_ACTIVITY = {
    "gym": "weight_training", "calisthenics": "weight_training", "bands": "weight_training",
    "swimming": "swimming", "running": "running", "cycling": "cycling", "yoga": "yoga", "mobility": "yoga",
    "hiit": "hiit", "hyrox": "hiit", "circuit": "hiit", "home": "hiit", "sports": "football",
}


def ok(data=None):
    return {"success": True, "data": data}


# ================================================================== password-reset e-mail (optional SMTP)
def mail_configured() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_FROM)


def send_reset(to: str, link: str) -> bool:
    if not mail_configured():
        return False
    msg = EmailMessage()
    msg["Subject"] = "Reset your FitPulse password"
    msg["From"] = config.SMTP_FROM
    msg["To"] = to
    msg.set_content(f"Someone asked to reset the password for this FitPulse account.\n\n"
                    f"Reset it here (valid for {config.RESET_TOKEN_MIN} minutes):\n{link}\n\n"
                    f"If this wasn't you, ignore this e-mail — your password stays the same.")
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as s:
            s.starttls(context=ssl.create_default_context())
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(msg)
        return True
    except Exception:
        return False


# ================================================================== auth & account
GENERIC_LOGIN_ERROR = "E-mail or password is incorrect."


def _norm(email: str) -> str:
    return email.strip().lower()


@router.post("/auth/register", status_code=201)
def register(d: s.RegisterIn, request: Request, response: Response):
    email = _norm(d.email)
    problem = sec.password_problem(d.password, email)
    if problem:
        raise HTTPException(400, problem)
    if db.one("SELECT id FROM users WHERE email = :e", e=email):
        # Account exists: say so plainly (a sign-up form cannot hide this without e-mail verification).
        raise HTTPException(409, "An account with this e-mail already exists. Sign in or reset your password.")
    uid = db.new_id()
    now = db.now()
    db.run("INSERT INTO users (id, email, name, password_hash, created_at, password_changed_at) "
           "VALUES (:i, :e, :n, :p, :c, :c)", i=uid, e=email, n=d.name.strip(), p=sec.hash_password(d.password), c=now)
    db.run("INSERT INTO profiles (user_id, data, onboarding_complete, version, updated_at) VALUES (:u, '{}', 0, 1, :t)",
           u=uid, t=now)
    sec.set_session_cookie(request, response, sec.create_session(uid))
    return ok({"id": uid, "email": email, "name": d.name.strip(), "onboardingComplete": False})


@router.post("/auth/login")
def login(d: s.LoginIn, request: Request, response: Response):
    email = _norm(d.email)
    if sec.login_blocked(request, email):
        raise HTTPException(429, f"Too many failed attempts. Try again in {config.LOGIN_WINDOW_MIN} minutes "
                                 "or reset your password.")
    user = db.one("SELECT id, email, name, password_hash FROM users WHERE email = :e", e=email)
    if not user:
        sec.burn_time(d.password)
        sec.record_failure(request, email)
        raise HTTPException(401, GENERIC_LOGIN_ERROR)
    if not sec.verify_password(d.password, user["password_hash"]):
        sec.record_failure(request, email)
        raise HTTPException(401, GENERIC_LOGIN_ERROR)
    sec.clear_failures(request, email)
    # rotate: a fresh session on every sign-in
    sec.destroy_session(request.cookies.get(config.SESSION_COOKIE))
    sec.set_session_cookie(request, response, sec.create_session(user["id"]))
    prof = db.one("SELECT onboarding_complete FROM profiles WHERE user_id = :u", u=user["id"])
    return ok({"id": user["id"], "email": user["email"], "name": user["name"],
               "onboardingComplete": bool(prof and prof["onboarding_complete"])})


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    sec.destroy_session(request.cookies.get(config.SESSION_COOKIE))
    sec.clear_session_cookie(response)
    return ok({"signedOut": True})


@router.get("/auth/me")
def me(request: Request):
    """Current session. Returns data=null (not 401) when signed out, so the site can load quietly."""
    user = sec.session_user(request)
    if not user:
        return ok(None)
    prof = db.one("SELECT onboarding_complete FROM profiles WHERE user_id = :u", u=user["id"])
    return ok({**user, "onboardingComplete": bool(prof and prof["onboarding_complete"])})


@router.post("/auth/forgot")
def forgot(d: s.ForgotIn, request: Request):
    """Always answers the same way, so the form cannot be used to discover which e-mails have accounts."""
    email = _norm(d.email)
    user = db.one("SELECT id FROM users WHERE email = :e", e=email)
    out = {"message": "If an account exists for that e-mail, a reset link has been sent.",
           "emailDelivery": mail_configured()}
    if user:
        token = secrets.token_urlsafe(32)
        exp = datetime.now(timezone.utc) + timedelta(minutes=config.RESET_TOKEN_MIN)
        db.run("DELETE FROM reset_tokens WHERE user_id = :u", u=user["id"])
        db.run("INSERT INTO reset_tokens (token_hash, user_id, expires_at, used) VALUES (:t, :u, :e, 0)",
               t=sec.sha256(token), u=user["id"], e=exp.isoformat(timespec="seconds"))
        base = config.PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
        link = f"{base}/#/reset?token={token}"
        if mail_configured():
            send_reset(email, link)
        elif config.DEV_SHOW_RESET_LINK:
            out["devResetLink"] = link        # local development only — disabled by default
    if not mail_configured():
        out["message"] = ("E-mail delivery is not configured on this deployment, so no reset e-mail can be sent. "
                          "Please contact the site administrator.")
    return ok(out)


@router.post("/auth/reset")
def reset(d: s.ResetIn):
    row = db.one("SELECT user_id, expires_at, used FROM reset_tokens WHERE token_hash = :t", t=sec.sha256(d.token))
    if not row or row["used"] or datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(400, "This reset link is invalid or has expired. Request a new one.")
    user = db.one("SELECT email FROM users WHERE id = :u", u=row["user_id"])
    problem = sec.password_problem(d.password, user["email"] if user else "")
    if problem:
        raise HTTPException(400, problem)
    db.run("UPDATE users SET password_hash = :p, password_changed_at = :c WHERE id = :u",
           p=sec.hash_password(d.password), c=db.now(), u=row["user_id"])
    db.run("UPDATE reset_tokens SET used = 1 WHERE token_hash = :t", t=sec.sha256(d.token))
    sec.destroy_all_sessions(row["user_id"])          # sign out everywhere
    return ok({"reset": True})


@router.post("/account/password")
def change_password(d: s.ChangePasswordIn, request: Request, response: Response, user: dict = Depends(sec.current_user)):
    row = db.one("SELECT password_hash FROM users WHERE id = :u", u=user["id"])
    if not sec.verify_password(d.currentPassword, row["password_hash"]):
        raise HTTPException(400, "Current password is incorrect.")
    problem = sec.password_problem(d.newPassword, user["email"])
    if problem:
        raise HTTPException(400, problem)
    db.run("UPDATE users SET password_hash = :p, password_changed_at = :c WHERE id = :u",
           p=sec.hash_password(d.newPassword), c=db.now(), u=user["id"])
    sec.destroy_all_sessions(user["id"])
    sec.set_session_cookie(request, response, sec.create_session(user["id"]))   # keep this device signed in
    return ok({"changed": True})


@router.put("/account")
def update_account(d: s.AccountIn, user: dict = Depends(sec.current_user)):
    db.run("UPDATE users SET name = :n WHERE id = :u", n=d.name.strip(), u=user["id"])
    return ok({**user, "name": d.name.strip()})


@router.get("/account/export")
def export(user: dict = Depends(sec.current_user)):
    uid = user["id"]
    prof = db.one("SELECT data, onboarding_complete, updated_at FROM profiles WHERE user_id = :u", u=uid)
    plans = db.all_rows("SELECT id, created_at, source, status, response, energy FROM plans WHERE user_id = :u", u=uid)
    wos = db.all_rows("SELECT * FROM workout_logs WHERE user_id = :u ORDER BY date", u=uid)
    ms = db.all_rows("SELECT date, weight, waist, body_fat FROM measurements WHERE user_id = :u ORDER BY date", u=uid)
    return ok({"account": user, "profile": db.loads(prof["data"]) if prof else None,
               "plans": [{**p, "response": db.loads(p["response"]), "energy": db.loads(p["energy"])} for p in plans],
               "workouts": [{k: (db.loads(v) if k in ("details", "analysis") else v) for k, v in w.items() if k != "user_id"}
                            for w in wos],
               "measurements": ms})


@router.delete("/account")
def delete_account(d: s.DeleteAccountIn, response: Response, user: dict = Depends(sec.current_user)):
    row = db.one("SELECT password_hash FROM users WHERE id = :u", u=user["id"])
    if not sec.verify_password(d.password, row["password_hash"]):
        raise HTTPException(400, "Password is incorrect.")
    uid = user["id"]
    for t in ("sessions", "reset_tokens", "profiles", "plans", "workout_logs", "measurements"):
        db.run(f"DELETE FROM {t} WHERE user_id = :u", u=uid)
    db.run("DELETE FROM users WHERE id = :u", u=uid)
    sec.clear_session_cookie(response)
    return ok({"deleted": True})


# ================================================================== profile & onboarding
def load_profile(uid: str) -> dict:
    row = db.one("SELECT data, onboarding_complete, version, updated_at FROM profiles WHERE user_id = :u", u=uid)
    if not row:     # should not happen (created at registration) — create lazily
        db.run("INSERT INTO profiles (user_id, data, onboarding_complete, version, updated_at) VALUES (:u, '{}', 0, 1, :t)",
               u=uid, t=db.now())
        return {"data": {}, "onboardingComplete": False, "version": 1, "updatedAt": None}
    return {"data": db.loads(row["data"]) or {}, "onboardingComplete": bool(row["onboarding_complete"]),
            "version": row["version"], "updatedAt": row["updated_at"]}


@router.get("/config/onboarding")
def onboarding_config():
    return ok(onboarding.load())


@router.get("/profile")
def get_profile(user: dict = Depends(sec.current_user)):
    return ok(load_profile(user["id"]))


@router.put("/profile")
def save_profile(d: s.ProfileIn, user: dict = Depends(sec.current_user)):
    current = load_profile(user["id"])
    if d.version != current["version"]:
        # Someone (another tab/device) saved a newer version. Do not overwrite it silently.
        return JSONResponse(status_code=409, content={
            "success": False, "error": "Your profile was changed somewhere else. Review the latest version and save again.",
            "data": current})
    clean, errors = onboarding.validate(d.data, complete=False)
    if current["onboardingComplete"]:
        _, required_errors = onboarding.validate(clean, complete=True)
        if required_errors:
            return JSONResponse(status_code=400, content={
                "success": False, "error": "Some required answers are missing or invalid.", "fields": required_errors})
    new_version = current["version"] + 1
    db.run("UPDATE profiles SET data = :d, version = :v, updated_at = :t WHERE user_id = :u AND version = :old",
           d=db.dumps(clean), v=new_version, t=db.now(), u=user["id"], old=current["version"])
    saved = load_profile(user["id"])
    if saved["version"] != new_version:          # lost a race with a concurrent save
        return JSONResponse(status_code=409, content={"success": False, "error": "Profile changed while saving. Try again.",
                                                       "data": saved})
    return ok({**saved, "fieldErrors": errors})


@router.post("/profile/complete")
def complete_onboarding(user: dict = Depends(sec.current_user)):
    current = load_profile(user["id"])
    clean, errors = onboarding.validate(current["data"], complete=True)
    if errors:
        return JSONResponse(status_code=400, content={"success": False, "error": "Some answers still need attention.",
                                                       "fields": errors})
    db.run("UPDATE profiles SET data = :d, onboarding_complete = 1, version = version + 1, updated_at = :t WHERE user_id = :u",
           d=db.dumps(clean), t=db.now(), u=user["id"])
    return ok(load_profile(user["id"]))


# ================================================================== plans
FITPULSE_LABEL = "FitPulse API (Maajith)"


async def energy_context(profile: dict) -> dict:
    """Real energy needs + goal-plan safety from Maajith's deployed FitPulse API. Never estimated locally."""
    sex = profile.get("sex")
    if sex not in ("male", "female"):
        return {"source": FITPULSE_LABEL, "status": "skipped",
                "reason": "Energy equations need a sex value; you chose not to share it."}
    age = onboarding.age_from_dob(date.fromisoformat(profile["dateOfBirth"]))
    args = (age, sex, float(profile["heightCm"]), float(profile["weightKg"]), profile.get("activityLevel", "moderate"))
    out = {"source": FITPULSE_LABEL, "status": "ok"}
    try:
        out["calories"] = await fitpulse.energy_needs(*args, profile.get("primaryGoal", ""), profile.get("bodyFatPct"))
    except fitpulse.PartnerUnavailable as exc:
        return {"source": FITPULSE_LABEL, "status": "unavailable", "reason": f"FitPulse API unavailable ({exc})."}
    except fitpulse.PartnerRejected as exc:
        return {"source": FITPULSE_LABEL, "status": "rejected", "reason": str(exc)}
    weeks = onboarding.programme_weeks(profile)
    if profile.get("targetWeightKg") and weeks:
        try:   # optional second call; if it fails the calorie result above is still real and shown
            out["goalPlan"] = await fitpulse.goal_plan(*args, float(profile["targetWeightKg"]), weeks)
        except (fitpulse.PartnerUnavailable, fitpulse.PartnerRejected) as exc:
            out["goalPlanError"] = f"Goal-pace check unavailable ({exc})."
    return out


def view(row: dict) -> dict:
    resp = db.loads(row["response"])
    return {"id": row["id"], "createdAt": row["created_at"], "updatedAt": row["updated_at"], "status": row["status"],
            "source": row["source"], "isMock": bool(resp and resp.get("generatedBy", {}).get("isMock")),
            "profileVersion": row["profile_version"], "plan": resp, "energy": db.loads(row["energy"]),
            "error": row["error"]}


def _get_owned(plan_id: str, uid: str) -> dict:
    row = db.one("SELECT * FROM plans WHERE id = :i AND user_id = :u", i=plan_id, u=uid)
    if not row:
        raise HTTPException(404, "Plan not found.")
    return row


@router.post("/plans", status_code=201)
async def request_plan(d: s.PlanRequestIn, user: dict = Depends(sec.current_user)):
    uid = user["id"]
    existing = db.one("SELECT * FROM plans WHERE user_id = :u AND idempotency_key = :k", u=uid, k=d.idempotencyKey)
    if existing:                                   # double click / retry -> same plan, no second request
        return ok(view(existing))
    prof = load_profile(uid)
    if not prof["onboardingComplete"]:
        raise HTTPException(400, "Finish onboarding before requesting a plan.")
    if processing.mode() == "unconfigured":
        raise HTTPException(503, "Plan generation is not connected on this deployment yet: Maajith's processing "
                                 "system URL is not configured. Your profile is saved and nothing was generated.")
    pid = db.new_id()
    now = db.now()
    energy = await energy_context(prof["data"])
    payload = processing.build_payload(pid, uid, prof["data"], energy if energy.get("status") == "ok" else None)
    try:
        db.run("INSERT INTO plans (id, user_id, idempotency_key, created_at, updated_at, source, status, profile_version, "
               "request, energy) VALUES (:i, :u, :k, :c, :c, :src, 'requesting', :v, :r, :e)",
               i=pid, u=uid, k=d.idempotencyKey, c=now, src=processing.mode(), v=prof["version"],
               r=db.dumps(payload), e=db.dumps(energy))
    except IntegrityError:
        return ok(view(db.one("SELECT * FROM plans WHERE user_id = :u AND idempotency_key = :k", u=uid, k=d.idempotencyKey)))
    try:
        result = await processing.request_personalized_plan(payload)
    except processing.ProcessingUnavailable as exc:
        db.run("DELETE FROM plans WHERE id = :i", i=pid)      # nothing was produced; allow a clean retry
        raise HTTPException(503, str(exc))
    except processing.ProcessingRejected as exc:
        db.run("UPDATE plans SET status = 'failed', error = :e, updated_at = :t WHERE id = :i", e=str(exc), t=db.now(), i=pid)
        raise HTTPException(422, f"The processing system could not use this profile: {exc}")
    except processing.ProcessingInvalidResponse as exc:
        db.run("UPDATE plans SET status = 'failed', error = :e, updated_at = :t WHERE id = :i", e=str(exc), t=db.now(), i=pid)
        raise HTTPException(502, f"The processing system returned an invalid plan, so it was not shown. ({exc})")
    db.run("UPDATE plans SET status = :st, source = :src, external_id = :x, response = :r, updated_at = :t WHERE id = :i",
           st=result["status"], src=result["generatedBy"]["system"], x=result["planId"], r=db.dumps(result),
           t=db.now(), i=pid)
    return ok(view(_get_owned(pid, uid)))


@router.get("/plans")
def list_plans(user: dict = Depends(sec.current_user)):
    rows = db.all_rows("SELECT * FROM plans WHERE user_id = :u ORDER BY created_at DESC", u=user["id"])
    out = []
    for r in rows:
        v = view(r)
        summary = (v["plan"] or {}).get("summary") or {}
        item = {k: v[k] for k in ("id", "createdAt", "status", "source", "isMock", "profileVersion", "error")}
        item.update({"title": summary.get("title"), "weeks": summary.get("weeks")})
        out.append(item)
    return ok(out)


@router.get("/plans/current")
def current_plan(user: dict = Depends(sec.current_user)):
    row = db.one("SELECT * FROM plans WHERE user_id = :u AND status IN ('ready', 'processing') "
                 "ORDER BY created_at DESC LIMIT 1", u=user["id"])
    return ok(view(row) if row else None)


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str, user: dict = Depends(sec.current_user)):
    return ok(view(_get_owned(plan_id, user["id"])))


@router.post("/plans/{plan_id}/refresh")
async def refresh_plan(plan_id: str, user: dict = Depends(sec.current_user)):
    row = _get_owned(plan_id, user["id"])
    if row["status"] != "processing":
        return ok(view(row))
    try:
        result = await processing.get_personalized_plan(row["external_id"])
    except processing.ProcessingUnavailable as exc:
        return JSONResponse(status_code=503, content={"success": False, "error": str(exc), "data": view(row)})
    except (processing.ProcessingRejected, processing.ProcessingInvalidResponse) as exc:
        db.run("UPDATE plans SET status = 'failed', error = :e, updated_at = :t WHERE id = :i", e=str(exc), t=db.now(), i=plan_id)
        return ok(view(_get_owned(plan_id, user["id"])))
    db.run("UPDATE plans SET status = :st, response = :r, updated_at = :t WHERE id = :i",
           st=result["status"], r=db.dumps(result), t=db.now(), i=plan_id)
    return ok(view(_get_owned(plan_id, user["id"])))


# ================================================================== workouts, measurements, progress
FITMETRICS_LABEL = "FitMetrics engine (Yasash)"


def _check_date(d: str) -> str:
    try:
        day = date.fromisoformat(d)
    except ValueError:
        raise HTTPException(400, "Date must be a real date (YYYY-MM-DD).")
    if day > date.today():
        raise HTTPException(400, "Date cannot be in the future.")
    if day < date.today() - timedelta(days=366):
        raise HTTPException(400, "Date must be within the last year.")
    return day.isoformat()


def workout_view(r: dict) -> dict:
    return {"id": r["id"], "date": r["date"], "loggedAt": r["logged_at"], "discipline": r["discipline"],
            "title": r["title"], "durationMin": r["duration_min"], "rpe": r["rpe"], "avgHr": r["avg_hr"],
            "notes": r["notes"], "details": db.loads(r["details"]) or {}, "planId": r["plan_id"],
            "sessionId": r["session_id"], "analysis": db.loads(r["analysis"]), "analysisStatus": r["analysis_status"]}


async def _analyse(profile: dict, discipline: str, duration: float, avg_hr: Optional[int]):
    """Returns (analysis | None, status). Only real FitMetrics output is stored."""
    if not avg_hr:
        return None, "skipped_no_heart_rate"
    if not profile.get("restingHr"):
        return None, "skipped_no_resting_hr"
    if profile.get("sex") not in ("male", "female"):
        return None, "skipped_sex_not_shared"
    if not profile.get("dateOfBirth") or not profile.get("weightKg"):
        return None, "skipped_profile_incomplete"
    age = onboarding.age_from_dob(date.fromisoformat(profile["dateOfBirth"]))
    try:   # FitMetrics' own engine, called in-process (this app IS FitMetrics)
        a = workout.analyse(DISCIPLINE_TO_ACTIVITY.get(discipline, "hiit"), duration, float(profile["weightKg"]), age,
                            int(profile["restingHr"]), int(avg_hr), profile["sex"], "normal")
    except MetricError as exc:
        return {"error": str(exc)}, "analysis_rejected"
    return {**a, "analysedBy": FITMETRICS_LABEL}, "analysed"


@router.post("/workouts", status_code=201)
async def log_workout(d: s.WorkoutIn, user: dict = Depends(sec.current_user)):
    uid = user["id"]
    dup = db.one("SELECT * FROM workout_logs WHERE user_id = :u AND client_id = :c", u=uid, c=d.clientId)
    if dup:
        return ok({**workout_view(dup), "duplicate": True})
    day = _check_date(d.date)
    external_plan = None
    if d.planId:
        plan = db.one("SELECT id, external_id FROM plans WHERE id = :i AND user_id = :u", i=d.planId, u=uid)
        if not plan:
            raise HTTPException(404, "Plan not found.")
        external_plan = plan["external_id"]
    profile = load_profile(uid)["data"]
    analysis, status = await _analyse(profile, d.discipline, d.durationMin, d.avgHr)
    details = {"distanceKm": d.distanceKm, "exercises": [e.model_dump(exclude_none=True) for e in d.exercises]}
    wid = db.new_id()
    try:
        db.run("INSERT INTO workout_logs (id, user_id, client_id, logged_at, date, discipline, title, duration_min, rpe, "
               "avg_hr, notes, details, plan_id, session_id, analysis, analysis_status) VALUES (:i, :u, :c, :la, :d, :disc, "
               ":t, :dur, :rpe, :hr, :n, :det, :p, :sid, :a, :as)",
               i=wid, u=uid, c=d.clientId, la=db.now(), d=day, disc=d.discipline, t=d.title.strip(), dur=d.durationMin,
               rpe=d.rpe, hr=d.avgHr, n=(d.notes or "").strip() or None, det=db.dumps(details), p=d.planId,
               sid=d.sessionId, a=db.dumps(analysis), **{"as": status})
    except IntegrityError:
        return ok({**workout_view(db.one("SELECT * FROM workout_logs WHERE user_id = :u AND client_id = :c",
                                         u=uid, c=d.clientId)), "duplicate": True})
    forwarded = await processing.log_workout(external_plan, {"sessionId": d.sessionId, "date": day,
                                                             "durationMin": d.durationMin, "rpe": d.rpe,
                                                             "completed": True}) if external_plan else "local_only"
    row = db.one("SELECT * FROM workout_logs WHERE id = :i", i=wid)
    return ok({**workout_view(row), "processingFeedback": forwarded})


@router.get("/workouts")
def list_workouts(limit: int = Query(50, ge=1, le=200), user: dict = Depends(sec.current_user)):
    rows = db.all_rows("SELECT * FROM workout_logs WHERE user_id = :u ORDER BY date DESC, logged_at DESC LIMIT :l",
                       u=user["id"], l=limit)
    return ok([workout_view(r) for r in rows])


def _owned_workout(wid: str, uid: str) -> dict:
    row = db.one("SELECT * FROM workout_logs WHERE id = :i AND user_id = :u", i=wid, u=uid)
    if not row:
        raise HTTPException(404, "Workout not found.")
    return row


@router.get("/workouts/{wid}")
def get_workout(wid: str, user: dict = Depends(sec.current_user)):
    return ok(workout_view(_owned_workout(wid, user["id"])))


@router.post("/workouts/{wid}/analyse")
async def reanalyse(wid: str, user: dict = Depends(sec.current_user)):
    row = _owned_workout(wid, user["id"])
    profile = load_profile(user["id"])["data"]
    analysis, status = await _analyse(profile, row["discipline"], row["duration_min"], row["avg_hr"])
    db.run("UPDATE workout_logs SET analysis = :a, analysis_status = :s WHERE id = :i", a=db.dumps(analysis), s=status, i=wid)
    return ok(workout_view(_owned_workout(wid, user["id"])))


@router.delete("/workouts/{wid}")
def delete_workout(wid: str, user: dict = Depends(sec.current_user)):
    _owned_workout(wid, user["id"])
    db.run("DELETE FROM workout_logs WHERE id = :i AND user_id = :u", i=wid, u=user["id"])
    return ok({"deleted": True})


# ------------------------------------------------------------------ measurements
@router.post("/measurements", status_code=201)
def add_measurement(d: s.MeasurementIn, user: dict = Depends(sec.current_user)):
    if d.weight is None and d.waist is None and d.bodyFat is None:
        raise HTTPException(400, "Enter at least one measurement.")
    day = _check_date(d.date)
    mid = db.new_id()
    db.run("INSERT INTO measurements (id, user_id, date, weight, waist, body_fat, created_at) VALUES (:i, :u, :d, :w, :wa, :b, :c)",
           i=mid, u=user["id"], d=day, w=d.weight, wa=d.waist, b=d.bodyFat, c=db.now())
    return ok({"id": mid, "date": day, "weight": d.weight, "waist": d.waist, "bodyFat": d.bodyFat})


@router.get("/measurements")
def list_measurements(user: dict = Depends(sec.current_user)):
    rows = db.all_rows("SELECT id, date, weight, waist, body_fat FROM measurements WHERE user_id = :u ORDER BY date, created_at",
                       u=user["id"])
    return ok([{"id": r["id"], "date": r["date"], "weight": r["weight"], "waist": r["waist"], "bodyFat": r["body_fat"]}
               for r in rows])


@router.delete("/measurements/{mid}")
def delete_measurement(mid: str, user: dict = Depends(sec.current_user)):
    if not db.one("SELECT id FROM measurements WHERE id = :i AND user_id = :u", i=mid, u=user["id"]):
        raise HTTPException(404, "Measurement not found.")
    db.run("DELETE FROM measurements WHERE id = :i AND user_id = :u", i=mid, u=user["id"])
    return ok({"deleted": True})


# ------------------------------------------------------------------ progress
def _planned_sessions(plan_resp: Optional[dict]) -> list:
    out = []
    for w in (plan_resp or {}).get("weeks", []):
        for sess in w.get("sessions", []):
            out.append((w["week"], sess["id"]))
    return out


@router.get("/progress")
async def progress(user: dict = Depends(sec.current_user)):
    uid = user["id"]
    today = date.today()
    wos = db.all_rows("SELECT * FROM workout_logs WHERE user_id = :u AND date >= :s ORDER BY date",
                      u=uid, s=(today - timedelta(weeks=12)).isoformat())
    # weekly totals for the last 8 weeks (Monday-based), from logged workouts only
    weekly = []
    for i in range(7, -1, -1):
        start = today - timedelta(days=today.weekday() + 7 * i)
        end = start + timedelta(days=6)
        sel = [w for w in wos if start.isoformat() <= w["date"] <= end.isoformat()]
        weekly.append({"weekStart": start.isoformat(), "sessions": len(sel),
                       "minutes": round(sum(w["duration_min"] for w in sel))})
    by_disc: dict = {}
    for w in wos:
        by_disc[w["discipline"]] = by_disc.get(w["discipline"], 0) + 1
    # adherence against the current plan (only sessions logged against that plan count)
    adherence = None
    plan_row = db.one("SELECT * FROM plans WHERE user_id = :u AND status = 'ready' ORDER BY created_at DESC LIMIT 1", u=uid)
    if plan_row:
        planned = _planned_sessions(db.loads(plan_row["response"]))
        started = date.fromisoformat(plan_row["created_at"][:10])
        week_now = (today - started).days // 7 + 1
        due = [p for p in planned if p[0] <= week_now]
        done_ids = {r["session_id"] for r in db.all_rows(
            "SELECT DISTINCT session_id FROM workout_logs WHERE user_id = :u AND plan_id = :p AND session_id IS NOT NULL",
            u=uid, p=plan_row["id"])}
        adherence = {"planId": plan_row["id"], "currentWeek": week_now, "sessionsDue": len(due),
                     "sessionsCompleted": len([p for p in due if p[1] in done_ids]),
                     "sessionsCompletedTotal": len(done_ids), "sessionsPlannedTotal": len(planned)}
    ms = db.all_rows("SELECT date, weight, waist, body_fat FROM measurements WHERE user_id = :u ORDER BY date, created_at", u=uid)
    # training balance (ACWR) — computed by FitMetrics from analysed training loads, never locally
    days = [(today - timedelta(days=27 - i)).isoformat() for i in range(28)]
    loads = []
    for dd in days:
        tot = 0.0
        for w in wos:
            a = db.loads(w["analysis"]) if w["date"] == dd else None
            if a and isinstance(a.get("trainingLoad"), (int, float)):
                tot += a["trainingLoad"]
        loads.append(round(tot, 1))
    analysed = sum(1 for w in wos if w["analysis_status"] == "analysed")
    first_load_day = next((i for i, v in enumerate(loads) if v > 0), None)
    if first_load_day is not None and first_load_day > 7:
        # ACWR compares the last 7 days with the 28-day average; with under ~3 weeks of history the ratio is
        # mathematically inflated and would wrongly flag a beginner as "high risk". Don't show it yet.
        balance = {"status": "insufficient_data", "source": FITMETRICS_LABEL,
                   "reason": "Training balance needs about 3–4 weeks of analysed workouts. Keep logging sessions "
                             "with average heart rate and it will appear here."}
    elif sum(loads) == 0:
        balance = {"status": "insufficient_data", "source": FITMETRICS_LABEL,
                   "reason": "Log workouts with average heart rate (and set resting heart rate in your profile) to get "
                             "a training-balance check from FitMetrics."}
    else:
        try:
            balance = {"status": "ok", "source": FITMETRICS_LABEL, **training.training_balance(loads)}
        except MetricError as exc:
            balance = {"status": "rejected", "source": FITMETRICS_LABEL, "reason": str(exc)}
    summary = {"totalWorkouts12w": len(wos), "analysedWorkouts12w": analysed, "weekly": weekly, "byDiscipline": by_disc,
               "adherence": adherence, "measurements": [{"date": m["date"], "weight": m["weight"], "waist": m["waist"],
                                                         "bodyFat": m["body_fat"]} for m in ms],
               "trainingBalance": balance}
    return ok(await processing.get_progress(summary))
