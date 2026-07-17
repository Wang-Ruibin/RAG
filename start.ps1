# CampusQA Launcher - Parallel start
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$ai = Join-Path $root "ai_service"
$dist = Join-Path $frontend "dist"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   CampusQA - HHU Campus Q&A Assistant" -ForegroundColor Cyan
Write-Host "   AI Service:  http://localhost:8003" -ForegroundColor Gray
Write-Host "   Backend:     http://localhost:8002" -ForegroundColor Gray
Write-Host "   Swagger:     http://localhost:8002/docs" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Smart build: only if dist/ missing or src/ has newer files
$buildJob = $null
$distIndex = Join-Path $dist "index.html"
$needsBuild = -not (Test-Path $distIndex)
if (-not $needsBuild -and (Test-Path "$frontend\src")) {
    $latestSrc = (Get-ChildItem "$frontend\src" -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
    $latestDist = (Get-ChildItem $dist -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
    if ($latestSrc -gt $latestDist) { $needsBuild = $true }
}
if ($needsBuild) {
    Write-Host "[Build] Building frontend (background)..." -ForegroundColor Yellow
    $buildJob = Start-Job -ScriptBlock { param($d) Push-Location $d; npm run build 2>&1 | Out-Null; Pop-Location } -ArgumentList $frontend
}

$env:ALL_PROXY = ''
$env:HF_HUB_OFFLINE = '1'

$aiLog = "$env:TEMP\ai_service.log"
$aiErr = "$env:TEMP\ai_service_err.log"
$beLog = "$env:TEMP\backend.log"
$beErr = "$env:TEMP\backend_err.log"

Write-Host "[1/3] Starting AI Service (port 8003)..." -ForegroundColor Yellow
Start-Process -FilePath "python3.11" -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8003 --log-level warning" -WorkingDirectory $ai -WindowStyle Hidden -RedirectStandardOutput $aiLog -RedirectStandardError $aiErr

Write-Host "[2/3] Starting Backend (port 8002)..." -ForegroundColor Yellow
Start-Process -FilePath "python3.11" -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8002 --log-level warning" -WorkingDirectory $backend -WindowStyle Hidden -RedirectStandardOutput $beLog -RedirectStandardError $beErr

Write-Host "[3/3] Waiting for services..." -ForegroundColor Yellow
$aiReady = $false; $beReady = $false
$deadline = [datetime]::Now.AddSeconds(15)
while ([datetime]::Now -lt $deadline -and -not ($aiReady -and $beReady)) {
    if (-not $aiReady) { try { $r = Invoke-WebRequest "http://localhost:8003/health" -TimeoutSec 1 -UseBasicParsing; if ($r.StatusCode -eq 200) { $aiReady = $true; Write-Host "      AI Service ready." -ForegroundColor Green } } catch {} }
    if (-not $beReady) { try { $r = Invoke-WebRequest "http://localhost:8002/api/health" -TimeoutSec 1 -UseBasicParsing; if ($r.StatusCode -eq 200) { $beReady = $true; Write-Host "      Backend ready." -ForegroundColor Green } } catch {} }
    if (-not ($aiReady -and $beReady) -and ([datetime]::Now -lt $deadline)) { Start-Sleep -Milliseconds 300 }
}
if ($aiReady -and $beReady) {
    Write-Host "      Both ready, opening browser." -ForegroundColor Green
} else {
    $still = @(); if (-not $aiReady) { $still += "AI" }; if (-not $beReady) { $still += "Backend" }
    Write-Host "      Timeout: $($still -join ', ') not ready. Opening anyway." -ForegroundColor DarkYellow
}
Start-Process "http://localhost:8002"

if ($buildJob -and ($buildJob.State -eq 'Running')) {
    Write-Host "[Build] Frontend build still in progress..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  CampusQA is running!" -ForegroundColor Green
Write-Host "  Close the two server windows to stop." -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Green
