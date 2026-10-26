# FitPulse — Personal Fitness Performance & Progress Management System
Majit · 23MIC0052 · Partner project: FitMetrics (Yasash S · 23MIC0060)

FitPulse answers **"what does this person need, and how are they progressing?"**
FitMetrics answers **"what did each workout actually do?"** — FitPulse never computes workout
metrics itself; it asks FitMetrics.

## Features
| Area | Endpoints |
|---|---|
| Energy needs | `POST /fitness/calories` — BMR (Mifflin-St Jeor, Harris-Benedict, Katch-McArdle), TDEE, goal calories, macros *(also used by FitMetrics)* |
| Goal planning | `POST /fitness/goal-plan` — target weight + weeks → daily calories, macros, safety rating, target date |
| Body composition | `POST /fitness/bmi`, `/fitness/body-fat` (US Navy), `/fitness/ideal-weight` (4 formulas) |
| Progress tracking | `POST /progress/measurements`, `POST /progress/goal`, `GET /progress/summary` (trend, weekly rate, on-track check) |
| Workout log **(uses FitMetrics)** | `POST /progress/workouts` → analysed by `FitMetrics /metrics/workout-analysis` before saving; `GET /progress/workouts` weekly totals |
| Injury risk **(uses FitMetrics)** | `GET /progress/training-status` → 28-day loads sent to `FitMetrics /metrics/training-balance` |
| Partner sync **(uses FitMetrics)** | `POST /fitness/partner-sync` — today's energy target + calories burned from FitMetrics |
| Reports & keys | `POST /reports/profile` (PDF), `POST /keys`, `GET /keys/me`, `GET /health` |

## Run (one step)
- **Windows:** double-click `start_windows.bat` (or `python run.py` in this folder)
- **macOS / Linux:** `./start_mac_linux.sh`

Opens **http://localhost:8000** · Swagger: **/docs**. `run.py` also starts the real FitMetrics
project from the parent folder as the partner service (or a small stand-in if it isn't there).

## Tests
    cd backend && pytest -q        # 13 tests

## Deploy on Vercel (free, no card)
vercel.com/new → import the GitHub repo → **Root Directory: `fitpulse`** → Deploy.
Then set environment variable `FITMETRICS_BASE_URL = https://<your-fitmetrics>.vercel.app/api/v1`
and redeploy. (On Vercel the progress database lives in /tmp and can reset when the function
sleeps; the `demo` profile refills itself automatically.)
