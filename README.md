# FitMetrics — Workout Performance & Training Analytics API
Yasash S · 23MIC0060 · partner project: FitPulse (23MIC0052)

> **This repository holds both team projects**
> - `/` (backend, frontend, api) — **FitMetrics** (Yasash, 23MIC0060): workout analytics
> - `/fitpulse` — **FitPulse** (Maajith, 23MIC0052): energy needs, body composition, goals & progress tracking — see fitpulse/README.md
>
> Each project runs on its own and uses the other's API. Running either launcher starts the other one as its partner.

## Start the website (one step)
- **Windows:** double-click `start_windows.bat`
  (or open *Anaconda Prompt*, `cd` into this folder, run `python run.py`)
- **macOS / Linux:** `./start_mac_linux.sh` or `python3 run.py`

Then open **http://localhost:8000** (the browser opens automatically).
API docs (Swagger): http://localhost:8000/docs · Stop with Ctrl+C.

`run.py` installs any missing packages, starts FitPulse from `./fitpulse` as the partner API,
and starts the FitMetrics API + website on the same server.

## Use a deployed FitPulse API instead
    Windows cmd:   set FITPULSE_BASE_URL=https://<his-url>/api/v1 && python run.py
    PowerShell:    $env:FITPULSE_BASE_URL="https://<his-url>/api/v1"; python run.py
    macOS/Linux:   FITPULSE_BASE_URL=https://<his-url>/api/v1 python3 run.py

## API keys
Every /metrics/* and /reports/* call needs the `X-API-Key` header.
- Website demo key: `fm_demo_public_key`
- Partner key for 23MIC0052: `fm_partner_23mic0052` (change via PARTNER_API_KEYS)
- Free personal key: "Get API Key" button, or `POST /api/v1/keys {"name": "...", "email": "..."}`

## Tests
    cd backend && pytest -q        # 22 tests

## Deploy (optional)
Vercel (no card needed): vercel.com/new → import the repo → Root Directory **`./`** for FitMetrics.
Import the same repo a second time with Root Directory **`fitpulse`** for FitPulse.
Then set `FITPULSE_BASE_URL` on FitMetrics and `FITMETRICS_BASE_URL` on FitPulse to each other's `https://…vercel.app/api/v1` and redeploy both.
Render: New → Web Service, root `backend`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
Either way one URL serves the whole site. Set FITPULSE_BASE_URL (env var) to Maajith's API URL.

## Troubleshooting
| Problem | Fix |
|---|---|
| Orange "backend isn't reachable" banner | The Python server isn't running — start it with start_windows.bat / `python run.py` |
| "Python was not found" | Use Anaconda Prompt: `python run.py` |
| Integration card says "FitPulse unavailable (503)" | Partner API not reachable — check FITPULSE_BASE_URL (expected behaviour, FitMetrics never computes maintenance calories itself) |
| Port 8000 busy | run.py automatically uses the next free port and prints it |
