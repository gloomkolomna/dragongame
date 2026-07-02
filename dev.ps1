param(
    [switch]$NoFrontend,
    [switch]$NoBackend
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$procs = @()

function Write-Step { Write-Host ">>> $args" -ForegroundColor Cyan }
function Write-OK   { Write-Host " OK $args" -ForegroundColor Green }
function Write-Warn { Write-Host " WARN $args" -ForegroundColor Yellow }
function Write-Err  { Write-Host " ERR $args" -ForegroundColor Red }

Write-Host @"

  Lair          Developers
   ___     ____/ (  __
  / _ \   / __ \ _/ /
 / // /  / /_/ //_ /
/____/   \____/  //

"@ -ForegroundColor Magenta

function cleanup {
    if ($procs.Count -gt 0) {
        Write-Host "`nStopping..." -ForegroundColor Yellow
        foreach ($p in $procs) {
            if (-not $p.HasExited) {
                & taskkill /PID $p.Id /T /F 2>$null
            }
            $p.Dispose()
        }
        $procs = @()
        Write-Host "All processes stopped." -ForegroundColor Green
    }
}

if (-not $NoBackend) {
    Write-Step "Starting backend (FastAPI :8001)"

    $venvPython = Join-Path $root "api\venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Err "venv not found at api\venv"
        exit 1
    }

    $apiDir = Join-Path $root "api"
    $env:PYTHONPATH = $apiDir

    $apiProc = Start-Process -FilePath $venvPython `
        -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8001 --reload" `
        -WorkingDirectory $apiDir -NoNewWindow -PassThru
    $procs += $apiProc
    Write-OK "Backend (pid $($apiProc.Id))"
}

if (-not $NoFrontend) {
    Write-Step "Starting frontend (Vite :5173)"

    $frontendDir = Join-Path $root "frontend"
    if (-not (Test-Path (Join-Path $frontendDir "node_modules\.package-lock.json"))) {
        Write-Warn "node_modules not found, installing..."
        Push-Location $frontendDir
        npm install
        Pop-Location
    }

    $feProc = Start-Process -FilePath "cmd" -ArgumentList "/c npm run dev" `
        -WorkingDirectory $frontendDir -NoNewWindow -PassThru
    $procs += $feProc
    Write-OK "Frontend (pid $($feProc.Id))"
}

Write-Host ""
Write-Host "──────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  API:     http://127.0.0.1:8001/api/" -ForegroundColor Green
Write-Host "  Admin:   http://127.0.0.1:5173/dragons/admin/login" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop all" -ForegroundColor DarkGray
Write-Host "──────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

try {
    while ($true) {
        $exited = $procs | Where-Object { $_.HasExited }
        foreach ($p in $exited) {
            Write-Warn "Process $($p.Id) stopped (exit: $($p.ExitCode))"
            $p.Dispose()
            $procs = @($procs | Where-Object { $_.Id -ne $p.Id })
        }
        if ($procs.Count -eq 0) { break }
        Start-Sleep -Seconds 2
    }
} finally {
    cleanup
}
