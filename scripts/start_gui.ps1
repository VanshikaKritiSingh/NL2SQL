<#
=============================================================================
NL2SQL Pipeline — Desktop & Web Studio GUI Launcher (Windows PowerShell)

Usage:
  .\scripts\start_gui.ps1                         # Starts Web Studio (Vite dev server)
  .\scripts\start_gui.ps1 -Desktop                # Starts Electron Desktop App
=============================================================================
#>

[CmdletBinding()]
param(
    [switch]$Desktop = $false,
    [switch]$HostNetwork = $false
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$GuiDir = Join-Path $RepoRoot "GUI"

$NpmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $NpmCmd) {
    Write-Error "[Error] Node.js and npm are required to launch the GUI. Please install Node.js 18+ from https://nodejs.org/"
    exit 1
}

Set-Location $GuiDir

if (-not (Test-Path "node_modules")) {
    Write-Host "[Notice] Installing GUI dependencies first..." -ForegroundColor Yellow
    npm install
}

Write-Host "======================================================" -ForegroundColor Cyan
if ($Desktop) {
    Write-Host "     NL2SQL Pipeline — Launching Electron Desktop GUI " -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan
    npm run desktop:dev
} else {
    Write-Host "     NL2SQL Pipeline — Launching Web Studio UI        " -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host "UI Web URL  : http://localhost:5173" -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop the frontend server.`n" -ForegroundColor Yellow
    if ($HostNetwork) {
        npm run dev -- --host
    } else {
        npm run dev
    }
}
