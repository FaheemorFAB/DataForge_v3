@echo off
title DataForge Ecosystem Launcher
echo ==================================================
echo  Starting DataForge Ecosystem
echo  Backend : http://localhost:5000
echo  Frontend: http://localhost:3000
echo ==================================================

set ROOT_DIR=%~dp0

:: Check for virtual environment in backend
if exist "%ROOT_DIR%backend\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%ROOT_DIR%backend\.venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

:: Start Backend (FastAPI + Uvicorn)
start "DataForge Backend (FastAPI)" cmd /k "cd /d "%ROOT_DIR%backend" && "%PYTHON_CMD%" main.py"

:: Start Frontend (Next.js)
start "DataForge Frontend (Next.js)" cmd /k "cd /d "%ROOT_DIR%frontend" && npm run dev"

echo Both services launched in separate windows!
echo Press any key to exit this launcher window...
pause >nul
