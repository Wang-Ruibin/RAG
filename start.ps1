# CampusQA Launcher - Single port (8002)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   CampusQA - HHU Campus Q&A Assistant" -ForegroundColor Cyan
Write-Host "   URL: http://localhost:8002" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/2] Building frontend..." -ForegroundColor Yellow
Push-Location $frontend
cmd /c "npm run build 2>&1" | Out-Null
Pop-Location

Write-Host "[2/2] Starting server..." -ForegroundColor Yellow
Write-Host "  Backend + Frontend at http://localhost:8002" -ForegroundColor Gray
Write-Host "  Swagger docs at http://localhost:8002/docs" -ForegroundColor Gray
Write-Host ""
Start-Sleep 2
Start-Process "http://localhost:8002"
Start-Process -FilePath "python3.11" -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8002" -WorkingDirectory $backend