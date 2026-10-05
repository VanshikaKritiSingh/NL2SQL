<#
=============================================================================
NL2SQL Pipeline — Windows PowerShell Setup & Environment Bootstrap Script

Usage:
  .\scripts\setup_windows.ps1                  # Core runtime + GUI + local dataset
  .\scripts\setup_windows.ps1 -InstallML       # Core + Heavy AI/ML training suite
  .\scripts\setup_windows.ps1 -SkipGUI         # Skip Node/NPM GUI setup
  .\scripts\setup_windows.ps1 -SkipData        # Skip dataset generation
=============================================================================
#>

[CmdletBinding()]
param(
    [switch]$InstallML = $false,
    [switch]$SkipGUI = $false,
    [switch]$SkipData = $false
)

$ErrorActionPreference = "Stop"

# Determine repository root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "     NL2SQL Production Pipeline — Environment Setup   " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "Repository Root: $RepoRoot`n"

# -----------------------------------------------------------------------------
# 1. Directory Structure Setup (Volume-Safe)
# -----------------------------------------------------------------------------
Write-Host "[1/5] Initializing local volume-safe directories..." -ForegroundColor Yellow
$Directories = @("offline\datasets", "offline\checkpoints", "offline\models")
foreach ($dir in $Directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Host "[OK] Local directories initialized." -ForegroundColor Green

# -----------------------------------------------------------------------------
# 2. Python Virtual Environment Setup
# -----------------------------------------------------------------------------
Write-Host "[2/5] Setting up Python virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        python -m venv .venv
        Write-Host "[OK] Created virtual environment in .venv" -ForegroundColor Green
    } else {
        Write-Error "[Error] Python not found in PATH. Please install Python 3.10+ from python.org."
        exit 1
    }
} else {
    Write-Host "[OK] Existing .venv detected." -ForegroundColor Green
}

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$VenvPip = Join-Path $RepoRoot ".venv\Scripts\pip.exe"

# -----------------------------------------------------------------------------
# 3. Install Core Python Dependencies (Zero Heavy GPU Overhead)
# -----------------------------------------------------------------------------
Write-Host "[3/5] Installing core lightweight dependencies (requirements.txt)..." -ForegroundColor Yellow
& $VenvPip install --upgrade pip setuptools wheel | Out-Null
& $VenvPip install -r requirements.txt

if ($InstallML) {
    Write-Host "[Notice] Installing isolated AI/ML fine-tuning dependencies (PyTorch, Transformers, PEFT)..." -ForegroundColor Magenta
    & $VenvPip install -r offline\training\requirements-train.txt
    Write-Host "[OK] ML training stack installed." -ForegroundColor Green
} else {
    Write-Host "[OK] Core runtime installed (Heavy ML/GPU packages skipped to save disk space)." -ForegroundColor Green
}

# -----------------------------------------------------------------------------
# 4. Generate Local Fine-Tuning Dataset (Git-Ignored)
# -----------------------------------------------------------------------------
if (-not $SkipData) {
    Write-Host "[4/5] Generating local fine-tuning dataset (offline/datasets/)..." -ForegroundColor Yellow
    & $VenvPython scripts\generate_dataset.py --output-dir offline\datasets --sample-count 250
    Write-Host "[OK] Synthetic fine-tuning datasets prepared (0 bytes committed to git)." -ForegroundColor Green
} else {
    Write-Host "[Skip] Dataset generation skipped." -ForegroundColor Gray
}

# -----------------------------------------------------------------------------
# 5. Frontend & Desktop GUI Setup
# -----------------------------------------------------------------------------
if (-not $SkipGUI) {
    Write-Host "[5/5] Setting up Desktop & Web Studio GUI (GUI\)..." -ForegroundColor Yellow
    $NpmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($NpmCmd) {
        Set-Location "$RepoRoot\GUI"
        npm install --silent
        Set-Location $RepoRoot
        Write-Host "[OK] GUI npm dependencies installed." -ForegroundColor Green
    } else {
        Write-Host "[Warning] npm not found in PATH. Skipping GUI npm install." -ForegroundColor Magenta
        Write-Host "Install Node.js 18+ to launch the Desktop & Web Studio UI." -ForegroundColor Gray
    }
} else {
    Write-Host "[Skip] GUI installation skipped." -ForegroundColor Gray
}

# -----------------------------------------------------------------------------
# Run Verification Tests
# -----------------------------------------------------------------------------
Write-Host "`nRunning core verification test suite..." -ForegroundColor Yellow
$env:PYTHONPATH = $RepoRoot
& $VenvPython -m pytest tests/ -v

Write-Host "`n======================================================" -ForegroundColor Green
Write-Host "   NL2SQL Environment Setup Completed Successfully!  " -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host "`nQuick Start Commands:"
Write-Host "  - Run Tests     : .\.venv\Scripts\pytest tests/ -v"
Write-Host "  - Launch Desktop: cd GUI; npm run desktop:dev"
Write-Host "  - Launch Web App: cd GUI; npm run dev"
Write-Host "  - Fine-Tune ML  : .\.venv\Scripts\python offline\training\train_qlora.py"
Write-Host "  - Generate Data : .\.venv\Scripts\python scripts\generate_dataset.py`n"
