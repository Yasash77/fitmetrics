# FitMetrics — Workout Performance & Training Analytics API
Yasash S · 23MIC0060 · partner project: FitPulse (23MIC0052)

## Start the website (one step)
- **Windows:** double-click `start_windows.bat`
  (or open *Anaconda Prompt*, `cd` into this folder, run `python run.py`)
- **macOS / Linux:** `./start_mac_linux.sh` or `python3 run.py`

Then open **http://localhost:8000** (the browser opens automatically).
API docs (Swagger): http://localhost:8000/docs · Stop with Ctrl+C.

`run.py` installs any missing packages, starts a local stand-in for Majit's FitPulse API,
and starts the FitMetrics API + website on the same server.

## Use Majit's real FitPulse API
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
Push to GitHub → Render → New → Blueprint (uses render.yaml). The backend also serves the
website, so the Render URL alone gives you the full site. Set FITPULSE_BASE_URL to Majit's URL.

## Troubleshooting
| Problem | Fix |
|---|---|
| Orange "backend isn't reachable" banner | The Python server isn't running — start it with start_windows.bat / `python run.py` |
| "Python was not found" | Use Anaconda Prompt: `python run.py` |
| Integration card says "FitPulse unavailable (503)" | Partner API not reachable — check FITPULSE_BASE_URL (expected behaviour, FitMetrics never computes maintenance calories itself) |
| Port 8000 busy | run.py automatically uses the next free port and prints it |
