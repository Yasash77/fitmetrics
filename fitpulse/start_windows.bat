@echo off
REM Double-click this file to start the FitPulse website on http://localhost:8000
cd /d "%~dp0"
set "PY="
if exist "%USERPROFILE%\anaconda3\python.exe" set "PY=%USERPROFILE%\anaconda3\python.exe"
if not defined PY if exist "%USERPROFILE%\miniconda3\python.exe" set "PY=%USERPROFILE%\miniconda3\python.exe"
if not defined PY where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python was not found. Open "Anaconda Prompt", go to this folder and run:  python run.py
  pause
  exit /b 1
)
echo Using Python: %PY%
"%PY%" run.py
pause
