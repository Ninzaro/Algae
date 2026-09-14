@echo off
echo ======================================================================
echo                STARTING ALPHAFORGE QUANT TERMINAL
echo ======================================================================
echo.

echo Starting AlphaForge FastAPI Backend on http://localhost:8000 ...
start "AlphaForge Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\python -m uvicorn alphaforge.main:app --reload --port 8000"

echo Starting AlphaForge Next.js Frontend on http://localhost:3000 ...
start "AlphaForge Frontend" cmd /k "cd /d %~dp0\frontend && pnpm dev"

echo.
echo ======================================================================
echo Both servers are launching in separate windows!
echo - Frontend: http://localhost:3000
echo - Backend API & Docs: http://localhost:8000/docs
echo ======================================================================
pause
