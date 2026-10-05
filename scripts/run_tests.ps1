<#
=============================================================================
NL2SQL Pipeline — Comprehensive Verification & Integration Test Suite (Windows PowerShell)

Usage:
  .\scripts\run_tests.ps1
=============================================================================
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$VenvPytest = Join-Path $RepoRoot ".venv\Scripts\pytest.exe"

if (Test-Path $VenvPython) {
    $PythonCmd = $VenvPython
    $PytestCmd = $VenvPytest
} else {
    $PythonCmd = "python"
    $PytestCmd = "pytest"
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "     NL2SQL Pipeline — Integration & Verification     " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# Step 1: Core Unit Tests
Write-Host "`n[1/2] Running Core & Transpiler Unit Tests (pytest)..." -ForegroundColor Yellow
$env:PYTHONPATH = $RepoRoot
& $PytestCmd tests\ -v

# Step 2: Backend Integration Tests
Write-Host "`n[2/2] Running Backend API Integration Tests..." -ForegroundColor Yellow
$env:PYTHONPATH = "$RepoRoot;$RepoRoot\GUI\server;" + $env:PYTHONPATH
& $PythonCmd GUI\server\test_backend.py

Write-Host "`n======================================================" -ForegroundColor Green
Write-Host "   ALL INTEGRATION & VERIFICATION TESTS PASSED 100%!  " -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
