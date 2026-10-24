# Starts backend (FastAPI :8000) and frontend (Vite :5173) for local development on Windows.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\dev.ps1 [-ApiPort 8000] [-WebPort 5173]
param([int]$ApiPort = 8000, [int]$WebPort = 5173)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$py = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Creating backend virtual environment..."
    python -m venv (Join-Path $root "backend\.venv")
    & $py -m pip install --upgrade pip
    & $py -m pip install -e "$root\backend[dev]"
}
if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
    Push-Location (Join-Path $root "frontend"); npm ci; Pop-Location
}

$env:CORS_ORIGINS = "http://localhost:$WebPort,http://127.0.0.1:$WebPort"
$api = Start-Process -PassThru -NoNewWindow -FilePath $py -ArgumentList "-m", "uvicorn", "safeguard_pq.api.app:app", "--host", "127.0.0.1", "--port", "$ApiPort" -WorkingDirectory (Join-Path $root "backend")
$env:SAFEGUARD_API = "http://127.0.0.1:$ApiPort"
Write-Host "API      http://127.0.0.1:$ApiPort/docs"
Write-Host "Frontend http://127.0.0.1:$WebPort"
Start-Process "http://127.0.0.1:$WebPort"
try {
    Push-Location (Join-Path $root "frontend")
    npm run dev -- --host 127.0.0.1 --port $WebPort
} finally {
    Pop-Location
    Stop-Process -Id $api.Id -ErrorAction SilentlyContinue
}
