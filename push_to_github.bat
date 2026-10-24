@echo off
REM Pushes this FitMetrics folder to https://github.com/Yasash77/fitmetrics
REM First create an EMPTY repo named "fitmetrics" at https://github.com/new (no README).
cd /d "%~dp0"
where git >nul 2>nul || (echo Git is not installed. Install it from https://git-scm.com/download/win and run this again. & pause & exit /b 1)
if not exist .git git init
git config user.name >nul 2>nul || git config user.name "Yasash Sanjeet Kumar"
git config user.email >nul 2>nul || git config user.email "sanjeetkumarcanarabank@gmail.com"
git add -A
git commit -m "FitMetrics: workout performance and training analytics API + website"
git branch -M main
git remote get-url origin >nul 2>nul || git remote add origin https://github.com/Yasash77/fitmetrics.git
git push -u origin main
echo.
echo Done. If the push failed, make sure the empty repo exists at https://github.com/Yasash77/fitmetrics
pause
