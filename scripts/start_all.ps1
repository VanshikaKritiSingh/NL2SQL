<#
=============================================================================
NL2SQL Pipeline — Unified Full-Stack Launcher (Windows PowerShell)

Starts both the FastAPI Backend Server and Desktop / Web GUI concurrently.
Automatically manages processes and cleans up on exit.

Usage:
  .\scripts\start_all.ps1                         # Starts Backend + Web UI
  .\scripts\start_all.ps1 -Desktop                # Starts Backend + Electron Desktop
=============================================================================
#>

[CmdletBinding()]
param(
    [switch]$Desktop = $false
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "       NL2SQL Full-Stack Pipeline — Starting Services " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonCmd = $VenvPython
} else {
    $PythonCmd = "python"
}

# 1. Start FastAPI Backend in background
Write-Host "[1/2] Launching FastAPI Backend Server on http://127.0.0.1:8000..." -ForegroundColor Yellow
$env:PYTHONPATH = "$RepoRoot;$RepoRoot\GUI\server;" + $env:PYTHONPATH

$BackendProcess = Start-Process -FilePath $PythonCmd -ArgumentList "-m", "uvicorn", "GUI.server.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload" -PassThru

Start-Sleep -Seconds 2

# 2. Start Frontend
Write-Host "[2/2] Launching Studio GUI..." -ForegroundColor Yellow
$GuiDir = Join-Path $RepoRoot "GUI"
Set-Location $GuiDir

if (-not (Test-Path "node_modules")) {
    npm install
}

Write-Host "`n======================================================" -ForegroundColor Green
Write-Host "  NL2SQL Full-Stack Environment is Active & Ready!    " -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host "  - Backend API : http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  - API Swagger : http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "  - Web Studio  : http://localhost:5173" -ForegroundColor Cyan
Write-Host "  - Close this window or press Ctrl+C to stop services.`n" -ForegroundColor Yellow

try {
    if ($Desktop) {
        npm run desktop:dev
    } else {
        npm run dev
    }
} finally {
    Write-Host "`nStopping backend process..." -ForegroundColor Yellow
    if ($BackendProcess -and -not $BackendProcess.HasExited) {
        Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[OK] All NL2SQL services stopped." -ForegroundColor Green
}
