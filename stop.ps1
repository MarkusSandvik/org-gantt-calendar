# Stops the backend/frontend dev servers started by start.ps1.
# Falls back to killing whatever is listening on the known dev ports if
# the PID file is missing or stale, so this stays reliable even if a
# server was started some other way.

$root = $PSScriptRoot
$pidFile = Join-Path $root ".dev-pids.json"
$stoppedAny = $false

function Stop-ProcessTree($processId, $label) {
    try {
        if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
            taskkill /F /PID $processId /T | Out-Null
            Write-Host "Stopped $label (PID $processId)" -ForegroundColor Green
            return $true
        }
    } catch {}
    return $false
}

if (Test-Path $pidFile) {
    $pids = Get-Content $pidFile | ConvertFrom-Json
    if (Stop-ProcessTree $pids.backend "backend") { $stoppedAny = $true }
    if (Stop-ProcessTree $pids.frontend "frontend") { $stoppedAny = $true }
    Remove-Item $pidFile -Force
}

# Fallback: catch anything still listening on the dev ports (e.g. PID
# file was missing, stale, or a child process outlived its parent).
foreach ($port in 8000, 5173) {
    $lines = netstat -ano | Select-String ":$port\s" | Select-String "LISTENING"
    foreach ($line in $lines) {
        $procId = ($line -split "\s+")[-1]
        if ($procId -match '^\d+$') {
            if (Stop-ProcessTree $procId "process on port $port") { $stoppedAny = $true }
        }
    }
}

if (-not $stoppedAny) {
    Write-Host "No running dev servers found." -ForegroundColor Yellow
}
