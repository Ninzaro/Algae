# Launch AlphaForge Backend and Frontend concurrently
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "               STARTING ALPHAFORGE QUANT TERMINAL" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan

$RootPath = $PSScriptRoot

Write-Host "`n[1/2] Starting FastAPI Backend on http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$RootPath'; & '$RootPath\.venv\Scripts\python.exe' -m uvicorn alphaforge.main:app --reload --port 8000"

Write-Host "[2/2] Starting Next.js Frontend on http://localhost:3000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$RootPath\frontend'; pnpm dev"

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "Servers launched in separate windows!" -ForegroundColor Green
Write-Host "  -> Frontend:    http://localhost:3000" -ForegroundColor White
Write-Host "  -> API & Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan
