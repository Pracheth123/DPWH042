<#
.SYNOPSIS
    GhostGrid -- Live Data Pipeline (Continuous Loop)
    ==================================================
    Runs every scraper, cleans, validates, and feeds data
    to the backend in an infinite 60-second cycle.

.USAGE
    Launched automatically by start_ghostgrid.ps1.
    Or manually:
        cd "c:\PRACHETH FILES\DP WORLD HACKATHON\data_scrapper"
        .\live_pipeline.ps1

.NOTES
    - Each scraper is wrapped in try/catch so one failure
      does not abort the rest of the cycle.
    - Set $CYCLE_DELAY_SECONDS to change the wait between cycles.
#>

$ErrorActionPreference = "Continue"   # do NOT stop on scraper errors
$SCRAPER_DIR = $PSScriptRoot           # data_scrapper/ root
$UTILS_DIR   = Join-Path $SCRAPER_DIR "utils"
$PYTHON      = Join-Path $SCRAPER_DIR "..\\.venv\Scripts\python.exe"

# If no venv python found at root, fall back to system python
if (-not (Test-Path $PYTHON)) {
    $PYTHON = "python"
}

$CYCLE_DELAY_SECONDS = 60

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR HELPERS
# ─────────────────────────────────────────────────────────────────────────────
function Write-Cycle($msg)  { Write-Host "`n$msg" -ForegroundColor Cyan   }
function Write-Step($msg)   { Write-Host "  >> $msg" -ForegroundColor White  }
function Write-Pass($msg)   { Write-Host "  [OK]  $msg" -ForegroundColor Green  }
function Write-Skip($msg)   { Write-Host "  [SKIP] $msg" -ForegroundColor Yellow }
function Write-Fail($msg)   { Write-Host "  [ERR] $msg" -ForegroundColor Red    }

# ─────────────────────────────────────────────────────────────────────────────
# HELPER: run a python script with error isolation
# ─────────────────────────────────────────────────────────────────────────────
function Invoke-Scraper {
    param(
        [string]$Label,
        [string]$ScriptPath,
        [string]$WorkDir
    )
    Write-Step "$Label ..."
    if (-not (Test-Path $ScriptPath)) {
        Write-Skip "$Label script not found: $ScriptPath"
        return
    }
    try {
        $proc = Start-Process -FilePath $PYTHON `
                              -ArgumentList "`"$ScriptPath`"" `
                              -WorkingDirectory $WorkDir `
                              -Wait -NoNewWindow -PassThru
        if ($proc.ExitCode -eq 0) {
            Write-Pass "$Label completed (exit 0)"
        } else {
            Write-Fail "$Label exited with code $($proc.ExitCode) -- continuing"
        }
    } catch {
        Write-Fail "$Label threw exception: $($_.Exception.Message) -- continuing"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# STARTUP BANNER
# ─────────────────────────────────────────────────────────────────────────────
Clear-Host
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Cyan
Write-Host "   GhostGrid -- Live Data Pipeline" -ForegroundColor White
Write-Host "   Cycle interval: $CYCLE_DELAY_SECONDS seconds" -ForegroundColor DarkGray
Write-Host "   Python: $PYTHON" -ForegroundColor DarkGray
Write-Host "   Scraper root: $SCRAPER_DIR" -ForegroundColor DarkGray
Write-Host "  ============================================================" -ForegroundColor Cyan
Write-Host "  Press Ctrl-C at any time to stop." -ForegroundColor Yellow
Write-Host ""

$cycleCount = 0

# ─────────────────────────────────────────────────────────────────────────────
# INFINITE PIPELINE LOOP
# ─────────────────────────────────────────────────────────────────────────────
while ($true) {
    $cycleCount++
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    Write-Cycle "=== STARTING SCRAPE CYCLE #$cycleCount  [$timestamp] ==="

    # ------------------------------------------------------------------
    # PHASE 1: RUN SCRAPERS (each isolated -- one failure = skip, not crash)
    # ------------------------------------------------------------------
    Write-Host "`n  [PHASE 1]  Scrapers" -ForegroundColor Magenta

    Invoke-Scraper -Label "Telegram Scraper"        `
                   -ScriptPath (Join-Path $SCRAPER_DIR "telegram_scraper.py") `
                   -WorkDir $SCRAPER_DIR

    Invoke-Scraper -Label "News Scraper"            `
                   -ScriptPath (Join-Path $SCRAPER_DIR "news_scraper.py") `
                   -WorkDir $SCRAPER_DIR

    Invoke-Scraper -Label "RSS Scraper"             `
                   -ScriptPath (Join-Path $SCRAPER_DIR "rss_scraper.py") `
                   -WorkDir $SCRAPER_DIR

    Invoke-Scraper -Label "OLX Scraper"             `
                   -ScriptPath (Join-Path $SCRAPER_DIR "olx_scraper.py") `
                   -WorkDir $SCRAPER_DIR

    Invoke-Scraper -Label "Shipping Scraper"        `
                   -ScriptPath (Join-Path $SCRAPER_DIR "shipping_scraper.py") `
                   -WorkDir $SCRAPER_DIR

    Invoke-Scraper -Label "Commodity Scraper"       `
                   -ScriptPath (Join-Path $SCRAPER_DIR "commodity_scraper.py") `
                   -WorkDir $SCRAPER_DIR

    Invoke-Scraper -Label "Customs Scraper"         `
                   -ScriptPath (Join-Path $SCRAPER_DIR "customs_scraper.py") `
                   -WorkDir $SCRAPER_DIR

    Invoke-Scraper -Label "Trends Scraper"          `
                   -ScriptPath (Join-Path $SCRAPER_DIR "trends_scraper.py") `
                   -WorkDir $SCRAPER_DIR

    Invoke-Scraper -Label "Trends Realtime Scraper" `
                   -ScriptPath (Join-Path $SCRAPER_DIR "trends_realtime_scraper.py") `
                   -WorkDir $SCRAPER_DIR

    Invoke-Scraper -Label "Trends RSS Scraper"      `
                   -ScriptPath (Join-Path $SCRAPER_DIR "trends_rss_scraper.py") `
                   -WorkDir $SCRAPER_DIR

    # ------------------------------------------------------------------
    # PHASE 2: MERGE — combine all scraper outputs into combined_data.json
    # ------------------------------------------------------------------
    Write-Host "`n  [PHASE 2]  Data Merge" -ForegroundColor Magenta

    Invoke-Scraper -Label "merge_data.py"           `
                   -ScriptPath (Join-Path $SCRAPER_DIR "merge_data.py") `
                   -WorkDir $SCRAPER_DIR

    # ------------------------------------------------------------------
    # PHASE 3: VALIDATE — schema check on combined_data.json
    # ------------------------------------------------------------------
    Write-Host "`n  [PHASE 3]  Data Validation" -ForegroundColor Magenta

    Invoke-Scraper -Label "data_validator.py"       `
                   -ScriptPath (Join-Path $SCRAPER_DIR "data_validator.py") `
                   -WorkDir $SCRAPER_DIR

    # ------------------------------------------------------------------
    # PHASE 4: FEED — POST records to the FastAPI backend
    # ------------------------------------------------------------------
    Write-Host "`n  [PHASE 4]  Feed to Backend" -ForegroundColor Magenta

    Invoke-Scraper -Label "feed_to_backend.py"      `
                   -ScriptPath (Join-Path $UTILS_DIR "feed_to_backend.py") `
                   -WorkDir $UTILS_DIR

    # ------------------------------------------------------------------
    # CYCLE COMPLETE
    # ------------------------------------------------------------------
    $doneAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Cycle "=== CYCLE #$cycleCount COMPLETE [$doneAt]. WAITING $CYCLE_DELAY_SECONDS SECONDS ==="
    Write-Host "  (Next cycle starts at $($(Get-Date).AddSeconds($CYCLE_DELAY_SECONDS).ToString('HH:mm:ss')))" `
               -ForegroundColor DarkGray

    Start-Sleep -Seconds $CYCLE_DELAY_SECONDS
}
