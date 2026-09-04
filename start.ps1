# Starts the backend (FastAPI/uvicorn) and frontend (Vite) dev servers,
# each in its own visible window, and records their PIDs so stop.ps1 can
# find and stop the right processes later.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$pidFile = Join-Path $root ".dev-pids.json"

if (-not (Test-Path $venvPython)) {
    Write-Host "Backend virtualenv not found at backend\.venv" -ForegroundColor Red
    Write-Host "Set it up first:"
    Write-Host "  cd backend"
    Write-Host "  python -m venv .venv"
    Write-Host "  .venv\Scripts\pip install -r requirements.txt"
    Write-Host "  .venv\Scripts\python -m alembic upgrade head"
    Write-Host "  .venv\Scripts\python -m app.db.seed"
    exit 1
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "Frontend dependencies not found. Run 'npm install' in frontend\ first." -ForegroundColor Red
    exit 1
}

if (Test-Path $pidFile) {
    Write-Host "Dev servers already appear to be running (found $pidFile)." -ForegroundColor Yellow
    Write-Host "Run stop.ps1 first if you want to restart them."
    exit 1
}

Write-Host "Starting backend (uvicorn, http://127.0.0.1:8000)..." -ForegroundColor Cyan
$backend = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload" `
    -WorkingDirectory $backendDir `
    -PassThru -WindowStyle Normal

Write-Host "Starting frontend (Vite, http://localhost:5173)..." -ForegroundColor Cyan
$frontend = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory $frontendDir `
    -PassThru -WindowStyle Normal

@{ backend = $backend.Id; frontend = $frontend.Id } | ConvertTo-Json | Set-Content -Encoding utf8 $pidFile

Write-Host ""
Write-Host "Backend:  http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "Run .\stop.ps1 to stop both servers."
