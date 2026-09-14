# ====================================================================
#          ALPHAFORGE QUANT TERMINAL — ONE-CLICK LAUNCH
# ====================================================================
#  Right-click this file and select "Run with PowerShell" to start.
#  Requirements:
#    - Python 3.12+ installed and on PATH
#    - Node.js 18+ installed and on PATH
# ====================================================================

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$Venv = Join-Path $Root ".venv"
$Frontend = Join-Path $Root "frontend"
$BackendSrc = Join-Path $Root "backend" "src"

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "           ALPHAFORGE  QUANT  TERMINAL" -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Python virtual environment ────────────────────────────────────
if (-not (Test-Path (Join-Path $Venv "Scripts" "python.exe"))) {
    Write-Host "[1/3] Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv $Venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Could not create virtual environment. Make sure Python 3.12+ is installed." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "[1/3] Installing Python dependencies..." -ForegroundColor Yellow
$Python = Join-Path $Venv "Scripts" "python.exe"
& $Python -m pip install -q --upgrade pip
& $Python -m pip install -q fastapi "uvicorn[standard]" sqlalchemy asyncpg alembic "pydantic>=2" "pydantic-settings>=2" python-jose "pwdlib[argon2]" python-multipart yfinance structlog "httpx>=0.27" "websockets>=14" "apscheduler>=3.10" "cryptography>=43" "prometheus-client>=0.21" "email-validator>=2" "numpy>=2" "pandas>=2"
Write-Host "   Python environment ready." -ForegroundColor Green

# ── 2. Frontend dependencies ─────────────────────────────────────────
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "[2/3] Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $Frontend
    npm install
    Pop-Location
}
Write-Host "   Frontend dependencies ready." -ForegroundColor Green

# ── 3. Launch servers ────────────────────────────────────────────────
Write-Host "[3/3] Launching servers..." -ForegroundColor Yellow

$env:PYTHONPATH = $BackendSrc

Write-Host "   Backend  -> http://localhost:8000" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONPATH='$BackendSrc'; & '$Python' -m uvicorn alphaforge.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "   Frontend -> http://localhost:3000" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Frontend'; npm run dev"

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "   API Docs  : http://localhost:8000/docs" -ForegroundColor White
Write-Host "   Dashboard : http://localhost:3000" -ForegroundColor White
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Both servers are launching in separate windows." -ForegroundColor Yellow
Write-Host "Close this window when you want to stop the servers." -ForegroundColor Yellow
Read-Host "Press Enter to exit"