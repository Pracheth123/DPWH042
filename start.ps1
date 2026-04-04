<#
.SYNOPSIS
    GhostGrid — One-Command Full-Stack Launcher
    Starts NLP server (8001), FastAPI backend (8000), and Vite frontend (5173).

.USAGE
    cd "c:\PRACHETH FILES\DP WORLD HACKATHON"
    .\start.ps1

.NOTES
    Stop all servers: close the three terminal windows, or press Ctrl-C in each.
    Run ingest:       python data_scrapper\ingest_pipeline.py
#>

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

# ── Colour helpers ─────────────────────────────────────────────────────────────
function Write-Header($msg) { Write-Host "`n  $msg" -ForegroundColor Cyan }
function Write-OK($msg)     { Write-Host "  ✓  $msg" -ForegroundColor Green }
function Write-Warn($msg)   { Write-Host "  ⚠  $msg" -ForegroundColor Yellow }
function Write-Err($msg)    { Write-Host "  ✗  $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "  ══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "     GhostGrid — Full-Stack Launcher" -ForegroundColor White
Write-Host "  ══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── Locate venv Python ─────────────────────────────────────────────────────────
$VENV_PYTHON = Join-Path $ROOT ".venv\Scripts\python.exe"
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Warn "No .venv found at root. Trying system Python …"
    $VENV_PYTHON = "python"
}
else {
    Write-OK "Virtual-env Python: $VENV_PYTHON"
}

# ── 1. Launch NLP server (port 8001) ──────────────────────────────────────────
Write-Header "Starting NLP inference server on :8001 …"
$nlpDir = Join-Path $ROOT "nlp_model"
$nlpJob = Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$nlpDir'; & '$VENV_PYTHON' -m uvicorn src.api_server:app --host 0.0.0.0 --port 8001"
) -PassThru
Write-OK "NLP server process started (PID $($nlpJob.Id))"

# ── 2. Launch FastAPI backend (port 8000) ─────────────────────────────────────
Write-Header "Starting FastAPI backend on :8000 …"
$backendDir = Join-Path $ROOT "backend"
$backendJob = Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$backendDir'; & '$VENV_PYTHON' -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
) -PassThru
Write-OK "Backend process started (PID $($backendJob.Id))"

# ── 3. Launch Vite frontend (port 5173) ───────────────────────────────────────
Write-Header "Starting Vite frontend on :5173 …"
$frontendDir = Join-Path $ROOT "frontend"
$frontendJob = Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$frontendDir'; npm run dev -- --port 5173"
) -PassThru
Write-OK "Frontend process started (PID $($frontendJob.Id))"

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Service          URL" -ForegroundColor White
Write-Host "  ──────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  NLP server    →  http://localhost:8001/health" -ForegroundColor Green
Write-Host "  Backend API   →  http://localhost:8000/health" -ForegroundColor Green
Write-Host "  Backend docs  →  http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Frontend      →  http://localhost:5173" -ForegroundColor Green
Write-Host "  ══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Wait ~30s for the NLP model to load, then run:" -ForegroundColor Yellow
Write-Host "  cd '$ROOT'" -ForegroundColor DarkGray
Write-Host "  python data_scrapper\ingest_pipeline.py --limit 100" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Press Enter to exit this launcher (servers keep running in their windows)."
Read-Host
