<#
.SYNOPSIS
    GhostGrid -- Demo Day Master Launcher  v2  (Live Pipeline Edition)
    ===================================================================
    Orchestrates the full GhostGrid stack in one command:
      Window 1  -->  NLP inference server   (port 8001)
      Window 2  -->  Ngrok tunnel           (exposes 8001)
      Window 3  -->  FastAPI backend        (port 8000)
      Window 4  -->  Vite / React frontend  (port 5173)
      Window 5  -->  Live data pipeline     (60-second scrape loop)

    Then pauses to let you paste the Ngrok URL, auto-patches
    backend/.env with it, and launches Window 5.

.USAGE
    cd "c:\PRACHETH FILES\DP WORLD HACKATHON"
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\start_ghostgrid.ps1

.NOTES
    v2 changes vs v1:
      - Fixed Read-Host prompt encoding crash
      - Fixed ngrok window using full resolved path
      - Added Window 5 live pipeline after .env is patched
      - Explicit UTF-8 output encoding throughout
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────
$ROOT          = $PSScriptRoot
$VENV_PYTHON   = Join-Path $ROOT ".venv\Scripts\python.exe"
$BACKEND_ENV   = Join-Path $ROOT "backend\.env"
$SCRAPPER_DIR  = Join-Path $ROOT "data_scrapper"
$PIPELINE_PS1  = Join-Path $SCRAPPER_DIR "live_pipeline.ps1"
$NLP_PORT      = 8001
$BACKEND_PORT  = 8000
$FRONTEND_PORT = 5173

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR HELPERS  (plain ASCII only -- no Unicode box chars)
# ─────────────────────────────────────────────────────────────────────────────
function Banner { param([string]$msg)
    Write-Host ""
    Write-Host "  $msg" -ForegroundColor Cyan
}
function OK   { param([string]$msg) { Write-Host "  [OK]    $msg" -ForegroundColor Green  } }
function WARN { param([string]$msg) { Write-Host "  [WARN]  $msg" -ForegroundColor Yellow } }
function ERR  { param([string]$msg) { Write-Host "  [ERR]   $msg" -ForegroundColor Red    } }
function Step { param([string]$n, [string]$msg)
    Write-Host ""
    Write-Host "  [$n]  $msg" -ForegroundColor Magenta
}

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
Clear-Host
Write-Host ""
Write-Host "  =============================================================" -ForegroundColor Cyan
Write-Host "   GhostGrid  --  Demo Day Master Launcher  v2" -ForegroundColor White
Write-Host "   Supply-Chain Crisis Detection  |  Live Pipeline Edition" -ForegroundColor DarkGray
Write-Host "  =============================================================" -ForegroundColor Cyan
Write-Host ""

# ─────────────────────────────────────────────────────────────────────────────
# PRE-FLIGHT CHECKS
# ─────────────────────────────────────────────────────────────────────────────
Banner "Running pre-flight checks ..."

# 1. Virtual environment
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Host "  [ERR]  Root .venv not found at: $VENV_PYTHON" -ForegroundColor Red
    Write-Host "  [ERR]  Create it: python -m venv .venv" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK]   Root .venv found" -ForegroundColor Green

# 2. Ngrok -- resolve FULL path so child windows can always find it
$ngrokCmd = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrokCmd) {
    Write-Host "  [WARN] ngrok not found on PATH. Window 2 will be skipped." -ForegroundColor Yellow
    $NGROK_EXE   = $null
    $SKIP_NGROK  = $true
} else {
    $NGROK_EXE  = $ngrokCmd.Source   # e.g. C:\Users\...\ngrok.exe
    Write-Host "  [OK]   ngrok found: $NGROK_EXE" -ForegroundColor Green
    $SKIP_NGROK = $false
}

# 3. npm for frontend
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "  [WARN] npm not found. Window 4 (frontend) will be skipped." -ForegroundColor Yellow
    $SKIP_FRONTEND = $true
} else {
    Write-Host "  [OK]   npm found" -ForegroundColor Green
    $SKIP_FRONTEND = $false
}

# 4. Backend .env
if (-not (Test-Path $BACKEND_ENV)) {
    Write-Host "  [ERR]  backend\.env not found: $BACKEND_ENV" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK]   backend\.env found" -ForegroundColor Green

# 5. Live pipeline script
if (Test-Path $PIPELINE_PS1) {
    Write-Host "  [OK]   live_pipeline.ps1 found" -ForegroundColor Green
} else {
    Write-Host "  [WARN] live_pipeline.ps1 not found at $PIPELINE_PS1 -- Window 5 will be skipped." -ForegroundColor Yellow
}

Start-Sleep -Milliseconds 400

# ─────────────────────────────────────────────────────────────────────────────
# WINDOW 1 -- NLP INFERENCE SERVER (port 8001)
# ─────────────────────────────────────────────────────────────────────────────
Step "1" "Launching NLP Inference Server (port $NLP_PORT) ..."

$nlpDir   = Join-Path $ROOT "nlp_model"
$nlpTitle = "GhostGrid -- Window 1  NLP Server :$NLP_PORT"
$nlpArgs  = "-NoExit -Command `"" +
            "Set-Location '$nlpDir'; " +
            "Write-Host '[WINDOW 1] NLP Inference Server' -ForegroundColor Cyan; " +
            "& '$VENV_PYTHON' -m uvicorn src.api_server:app --host 0.0.0.0 --port $NLP_PORT" +
            "`""

$nlpProc = Start-Process powershell.exe `
    -ArgumentList $nlpArgs `
    -PassThru -WindowStyle Normal
Write-Host "  [OK]   NLP server window opened  (PID $($nlpProc.Id))" -ForegroundColor Green

Write-Host "  Waiting 5s for the NLP server to begin loading ..." -ForegroundColor DarkGray
Start-Sleep -Seconds 5

# ─────────────────────────────────────────────────────────────────────────────
# WINDOW 2 -- NGROK TUNNEL
# ─────────────────────────────────────────────────────────────────────────────
if (-not $SKIP_NGROK) {
    Step "2" "Launching Ngrok tunnel for port $NLP_PORT ..."

    # Use the FULL resolved path so the child window always finds ngrok
    $ngrokArgs = "-NoExit -Command `"" +
                 "Write-Host '[WINDOW 2] Ngrok Tunnel' -ForegroundColor Cyan; " +
                 "& '$NGROK_EXE' http $NLP_PORT" +
                 "`""

    $ngrokProc = Start-Process powershell.exe `
        -ArgumentList $ngrokArgs `
        -PassThru -WindowStyle Normal
    Write-Host "  [OK]   Ngrok window opened  (PID $($ngrokProc.Id))" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Skipping Ngrok window. Run manually: ngrok http $NLP_PORT" -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────────────────────────────────
# WINDOW 3 -- FASTAPI BACKEND (port 8000)
# ─────────────────────────────────────────────────────────────────────────────
Step "3" "Launching FastAPI Backend (port $BACKEND_PORT) ..."

$backendDir  = Join-Path $ROOT "backend"
$backendArgs = "-NoExit -Command `"" +
               "Set-Location '$backendDir'; " +
               "Write-Host '[WINDOW 3] FastAPI Backend :$BACKEND_PORT' -ForegroundColor Cyan; " +
               "& '$VENV_PYTHON' -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload" +
               "`""

$backendProc = Start-Process powershell.exe `
    -ArgumentList $backendArgs `
    -PassThru -WindowStyle Normal
Write-Host "  [OK]   Backend window opened  (PID $($backendProc.Id))" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────────────
# WINDOW 4 -- VITE FRONTEND (port 5173)
# ─────────────────────────────────────────────────────────────────────────────
if (-not $SKIP_FRONTEND) {
    Step "4" "Launching Vite / React Frontend (port $FRONTEND_PORT) ..."

    $frontendDir  = Join-Path $ROOT "frontend"
    $frontendArgs = "-NoExit -Command `"" +
                    "Set-Location '$frontendDir'; " +
                    "Write-Host '[WINDOW 4] Vite Frontend :$FRONTEND_PORT' -ForegroundColor Cyan; " +
                    "npm run dev -- --port $FRONTEND_PORT" +
                    "`""

    $frontendProc = Start-Process powershell.exe `
        -ArgumentList $frontendArgs `
        -PassThru -WindowStyle Normal
    Write-Host "  [OK]   Frontend window opened  (PID $($frontendProc.Id))" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Skipping frontend window (npm not found)." -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────────────────────────────────
# INTERACTIVE NGROK URL CAPTURE
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  =============================================================" -ForegroundColor Yellow
Write-Host "   ACTION REQUIRED  --  Paste your Ngrok URL below" -ForegroundColor Yellow
Write-Host "  =============================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Look at Window 2 (Ngrok). Find the line that says:" -ForegroundColor White
Write-Host "    Forwarding   https://xxxx-xx-xxx.ngrok-free.app -> http://localhost:8001" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Copy the https://xxxx-xx-xxx.ngrok-free.app part." -ForegroundColor White
Write-Host ""

if ($SKIP_NGROK) {
    Write-Host "  [WARN] Ngrok was not launched automatically." -ForegroundColor Yellow
    Write-Host "         Run 'ngrok http $NLP_PORT' manually, then paste the URL below." -ForegroundColor Yellow
    Write-Host "         Press Enter to keep the existing NLP_API_URL." -ForegroundColor Yellow
}

# Use -Prompt to avoid any string-interpolation edge cases with parentheses
$ngrokUrl = (Read-Host -Prompt "  Paste Ngrok URL here (or press Enter to skip)").Trim().TrimEnd("/")

# ─────────────────────────────────────────────────────────────────────────────
# PATCH backend/.env WITH NEW NLP_API_URL
# ─────────────────────────────────────────────────────────────────────────────
if ($ngrokUrl -match "^https?://") {
    Write-Host ""
    Banner "Patching backend\.env ..."

    $envContent = Get-Content $BACKEND_ENV -Raw -Encoding UTF8

    if ($envContent -match "NLP_API_URL=") {
        $envContent = [regex]::Replace($envContent, "NLP_API_URL=[^\r\n]*", "NLP_API_URL=$ngrokUrl")
    } else {
        $envContent = $envContent.TrimEnd("`r`n") + "`r`nNLP_API_URL=$ngrokUrl`r`n"
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($BACKEND_ENV, $envContent, $utf8NoBom)

    Write-Host "  [OK]   backend\.env updated:" -ForegroundColor Green
    Write-Host "         NLP_API_URL=$ngrokUrl" -ForegroundColor Green

    Write-Host ""
    Write-Host "  [NOTE] Backend reads .env at startup." -ForegroundColor Yellow
    Write-Host "         If Window 3 was already running, restart it to pick up the new URL." -ForegroundColor Yellow

} elseif ($ngrokUrl -eq "") {
    Write-Host "  [WARN] No URL entered -- backend\.env left unchanged." -ForegroundColor Yellow
    $existing = (Get-Content $BACKEND_ENV | Where-Object { $_ -match "^NLP_API_URL=" }) -replace "NLP_API_URL=", ""
    Write-Host "         Current NLP_API_URL = $existing" -ForegroundColor DarkGray
} else {
    Write-Host "  [WARN] '$ngrokUrl' does not look like a valid URL." -ForegroundColor Yellow
    Write-Host "         backend\.env left unchanged. Edit it manually if needed." -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────────────────────────────────
# WINDOW 5 -- LIVE DATA PIPELINE (continuous scrape loop)
# ─────────────────────────────────────────────────────────────────────────────
Step "5" "Launching Live Data Pipeline (60-second scrape loop) ..."

if (Test-Path $PIPELINE_PS1) {

    $pipelineArgs = "-NoExit -ExecutionPolicy Bypass -Command `"" +
                    "Set-Location '$SCRAPPER_DIR'; " +
                    "Write-Host '[WINDOW 5] Live Data Pipeline' -ForegroundColor Cyan; " +
                    "& '$PIPELINE_PS1'" +
                    "`""

    $pipelineProc = Start-Process powershell.exe `
        -ArgumentList $pipelineArgs `
        -PassThru -WindowStyle Normal
    Write-Host "  [OK]   Live pipeline window opened  (PID $($pipelineProc.Id))" -ForegroundColor Green
    $pipelineLaunched = $true

} else {
    Write-Host "  [WARN] live_pipeline.ps1 not found -- skipping Window 5." -ForegroundColor Yellow
    Write-Host "         Run manually: python data_scrapper\utils\feed_to_backend.py" -ForegroundColor DarkGray
    $pipelineLaunched = $false
}

# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  =============================================================" -ForegroundColor Green
Write-Host "   ALL SYSTEMS GO!  GhostGrid is live." -ForegroundColor Green

if ($pipelineLaunched) {
    Write-Host "   The Live Data Pipeline has been launched in Window 5." -ForegroundColor Green
    Write-Host "   Live data will flow into the UI every 60 seconds." -ForegroundColor Green
}

Write-Host "  =============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Service layout:" -ForegroundColor White
Write-Host "  ---------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Window 1  NLP Server     http://localhost:$NLP_PORT/health" -ForegroundColor Green
Write-Host "  Window 2  Ngrok Tunnel   $ngrokUrl" -ForegroundColor Green
Write-Host "  Window 3  Backend API    http://localhost:$BACKEND_PORT/docs" -ForegroundColor Green

if (-not $SKIP_FRONTEND) {
    Write-Host "  Window 4  Frontend       http://localhost:$FRONTEND_PORT" -ForegroundColor Green
}

if ($pipelineLaunched) {
    Write-Host "  Window 5  Live Pipeline  scraping every 60s" -ForegroundColor Green
}

Write-Host "  ---------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  *** Wait ~30s for the NLP model to finish loading ***" -ForegroundColor Yellow
Write-Host "  (Watch Window 1 for: 'Ready to serve requests on POST /v1/predict')" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  To stop everything: close Windows 1-5 (or Ctrl-C in each)." -ForegroundColor White
Write-Host ""
Write-Host "  =============================================================" -ForegroundColor Green
Write-Host ""

Read-Host -Prompt "  Press Enter to close this launcher (all windows keep running)"
