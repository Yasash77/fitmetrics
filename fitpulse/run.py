"""
FitPulse — one-command launcher.

    python run.py

What it does:
  1. installs the backend requirements if any are missing,
  2. starts a local stand-in for the partner FitMetrics API (only if FITMETRICS_BASE_URL is not set),
  3. starts the FitPulse 24-Formula API + website on http://localhost:8000,
  4. opens the website in your browser.
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
REQUIRED = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "httpx": "httpx",
    "pydantic": "pydantic",
    "reportlab": "reportlab",
}


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
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "--upgrade", *missing])
        except subprocess.CalledProcessError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *missing])
        import site
        importlib.invalidate_caches()
        if hasattr(site, "getusersitepackages"):
            user_site = site.getusersitepackages()
            if user_site not in sys.path:
                sys.path.insert(0, user_site)


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

    stub = None
    if not os.getenv("FITMETRICS_BASE_URL"):
        stub_port = free_port(8001)
        stub = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "fitmetrics_stub:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(stub_port),
                "--log-level",
                "warning",
            ],
            cwd=str(BACKEND),
        )
        os.environ["FITMETRICS_BASE_URL"] = f"http://127.0.0.1:{stub_port}/api/v1"
        wait_until_up(stub_port)
        partner = f"local FitMetrics stand-in on port {stub_port} (set FITMETRICS_BASE_URL to use Yasash's real API)"
    else:
        partner = os.environ["FITMETRICS_BASE_URL"]

    port = free_port(int(os.getenv("PORT", "8000")))
    url = f"http://localhost:{port}"
    print("\n" + "=" * 68)
    print(f"  FitPulse website (24-Formula UI) : {url}")
    print(f"  API docs (Swagger)               : {url}/docs")
    print(f"  Partner FitMetrics               : {partner}")
    print("  Stop                             : Ctrl+C")
    print("=" * 68 + "\n")

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
