<#
=============================================================================
NL2SQL Pipeline — FastAPI Backend Server Launcher (Windows PowerShell)

Usage:
  .\scripts\start_backend.ps1                    # Runs backend on 127.0.0.1:8000
  .\scripts\start_backend.ps1 -Port 8080         # Custom port
  .\scripts\start_backend.ps1 -Host "0.0.0.0"    # Bind to all interfaces
=============================================================================
#>

[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoReload = $false
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "       NL2SQL Pipeline — Starting FastAPI Backend     " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "Server URL  : http://${HostAddress}:${Port}" -ForegroundColor Green
Write-Host "API Docs    : http://${HostAddress}:${Port}/docs" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server.`n" -ForegroundColor Yellow

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonCmd = $VenvPython
} else {
    $PythonCmd = "python"
}

$env:PYTHONPATH = "$RepoRoot;$RepoRoot\GUI\server;" + $env:PYTHONPATH

$ArgsList = @("-m", "uvicorn", "GUI.server.main:app", "--host", $HostAddress, "--port", "$Port")
if (-not $NoReload) {
    $ArgsList += "--reload"
}

& $PythonCmd $ArgsList
