"""
FitMetrics — one-command launcher.

    python run.py

What it does:
  1. installs the backend requirements if any are missing,
  2. starts the partner FitPulse API from ./fitpulse (or a small stand-in) unless FITPULSE_BASE_URL is set,
  3. starts the FitMetrics API + website on http://localhost:8000,
  4. opens the website in your browser.

Use Maajith's real FitPulse instead of the stand-in:
    Windows (cmd):       set FITPULSE_BASE_URL=https://<his-url>/api/v1 && python run.py
    PowerShell:          $env:FITPULSE_BASE_URL="https://<his-url>/api/v1"; python run.py
    macOS / Linux:       FITPULSE_BASE_URL=https://<his-url>/api/v1 python run.py
Stop with Ctrl+C.
"""
import importlib
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
REQUIRED = {"fastapi": "fastapi", "uvicorn": "uvicorn[standard]", "httpx": "httpx", "sqlalchemy": "sqlalchemy>=2.0",
            "pydantic": "pydantic", "reportlab": "reportlab"}


def check_python():
    if sys.version_info < (3, 8):
        sys.exit(f"Python 3.8 or newer is required (you have {sys.version.split()[0]}).")


def ensure_packages():
    missing = []
    for mod, pkg in REQUIRED.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)
    try:
        import pydantic
        if int(pydantic.VERSION.split(".")[0]) < 2:
            missing.append("pydantic>=2")
    except Exception:
        pass
    if missing:
        print(f"Installing missing packages: {', '.join(missing)} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *missing])
        importlib.invalidate_caches()


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def free_port(start: int) -> int:
    port = start
    while not port_free(port):
        port += 1
    return port


def wait_until_up(port: int, timeout: float = 20) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if not port_free(port):
            return True
        time.sleep(0.3)
    return False


def main():
    check_python()
    ensure_packages()
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))

    port = free_port(int(os.getenv("PORT", "8000")))
    # FitPulse user platform — local development defaults (override with real values to go live):
    os.environ.setdefault("PLAN_SERVICE_MODE", "mock")          # labelled placeholder until Maajith's plan URL is set
    os.environ.setdefault("DEV_SHOW_RESET_LINK", "true")        # show reset links on screen locally (no e-mail server)
    os.environ.setdefault("FITPULSE_API_KEY", "fp_demo_public_key")   # FitPulse's public demo key
    stub = None
    if not os.getenv("FITPULSE_BASE_URL"):
        stub_port = free_port(port + 1)
        partner_dir = ROOT / "fitpulse" / "backend"
        env = dict(os.environ, FITMETRICS_BASE_URL=f"http://127.0.0.1:{port}/api/v1")
        if (partner_dir / "app" / "main.py").exists():
            # real FitPulse project (Maajith, 23MIC0052) lives in this repo — run it as the partner service
            cmd, cwd = [sys.executable, "-m", "uvicorn", "app.main:app"], partner_dir
            partner = f"FitPulse (from ./fitpulse) on port {stub_port}"
        else:
            cmd, cwd = [sys.executable, "-m", "uvicorn", "fitpulse_stub:app"], BACKEND
            partner = f"local FitPulse stand-in on port {stub_port}"
        stub = subprocess.Popen(cmd + ["--host", "127.0.0.1", "--port", str(stub_port), "--log-level", "warning"],
                                cwd=str(cwd), env=env)
        os.environ["FITPULSE_BASE_URL"] = f"http://127.0.0.1:{stub_port}/api/v1"
        wait_until_up(stub_port)
        partner += " — set FITPULSE_BASE_URL to use a deployed FitPulse"
    else:
        partner = os.environ["FITPULSE_BASE_URL"]

    url = f"http://localhost:{port}"
    print("\n" + "=" * 64)
    print(f"  FitPulse app       : {url}")
    print(f"  FitMetrics console : {url}/tools.html")
    print(f"  Plan service       : {os.getenv('PLAN_SERVICE_URL') or 'development mock (labelled)'}")
    print(f"  API docs (Swagger) : {url}/docs")
    print(f"  Partner FitPulse   : {partner}")
    print("  Stop               : Ctrl+C")
    print("=" * 64 + "\n")

    def open_browser():
        if wait_until_up(port):
            webbrowser.open(url)
    if os.getenv("NO_BROWSER") != "1":
        threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    try:
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")
    finally:
        if stub:
            stub.terminate()


if __name__ == "__main__":
    main()
