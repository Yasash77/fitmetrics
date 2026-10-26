@echo off
REM Pushes this folder to https://github.com/Yasash77/fitmetrics
cd /d "%~dp0"
where git >nul 2>nul || (echo Git is not installed. Install it from https://git-scm.com/download/win and run this again. & pause & exit /b 1)
git add -A
git diff --cached --quiet || git commit -m "Update FitMetrics + FitPulse"
git remote get-url origin >nul 2>nul || git remote add origin https://github.com/Yasash77/fitmetrics.git
git push -u origin main
echo.
echo Done - check https://github.com/Yasash77/fitmetrics
pause
