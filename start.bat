@echo off
REM ===================================================================
REM          ALPHAFORGE QUANT TERMINAL — ONE-CLICK LAUNCH
REM ===================================================================
REM  Double-click this file to start both backend and frontend.
REM  Requirements:
REM    - Python 3.12+ installed and on PATH
REM    - Node.js 18+ installed and on PATH
REM ===================================================================

setlocal enabledelayedexpansion
set ROOT=%~dp0
set VENV=%ROOT%.venv
set FRONTEND=%ROOT%frontend

echo.
echo ==================================================================
echo           ALPHAFORGE  QUANT  TERMINAL
echo ==================================================================
echo.

REM ── 1. Python virtual environment ──────────────────────────────────
if not exist "%VENV%\Scripts\python.exe" (
    echo [1/3] Creating Python virtual environment...
    python -m venv "%VENV%"
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Could not create virtual environment. Make sure Python 3.12+ is installed.
        pause
        exit /b 1
    )
)

echo [1/3] Installing Python dependencies...
call "%VENV%\Scripts\activate"
pip install -q --upgrade pip >nul 2>&1
pip install -q fastapi "uvicorn[standard]" sqlalchemy asyncpg alembic "pydantic>=2" "pydantic-settings>=2" python-jose "pwdlib[argon2]" python-multipart yfinance structlog "httpx>=0.27" "websockets>=14" "apscheduler>=3.10" "cryptography>=43" "prometheus-client>=0.21" "email-validator>=2" "numpy>=2" "pandas>=2" >nul 2>&1
call deactivate
echo    Python environment ready.

REM ── 2. Frontend dependencies ────────────────────────────────────────
if not exist "%FRONTEND%\node_modules" (
    echo [2/3] Installing frontend dependencies (this may take a minute)...
    cd /d "%FRONTEND%"
    call npm install
    cd /d "%ROOT%"
)
echo    Frontend dependencies ready.

REM ── 3. Launch servers ───────────────────────────────────────────────
echo [3/3] Launching servers...

set PYTHONPATH=%ROOT%backend\src

echo    Starting Backend  on http://localhost:8000 ...
start "AlphaForge Backend" "%VENV%\Scripts\python.exe" -m uvicorn alphaforge.main:app --host 0.0.0.0 --port 8000 --reload

echo    Starting Frontend on http://localhost:3000 ...
start "AlphaForge Frontend" cmd /c "cd /d %FRONTEND% && npm run dev"

echo.
echo ==================================================================
echo   API Docs  : http://localhost:8000/docs
echo   Dashboard : http://localhost:3000
echo ==================================================================
echo.
echo Both servers are launching in separate windows!
echo Close this window when you want to stop the servers.
echo.
pause