<#
=============================================================================
NL2SQL Pipeline — AST & Execution Accuracy Benchmark Evaluator (Windows PowerShell)

Usage:
  .\scripts\start_eval.ps1                       # Evaluates offline\datasets\eval.json
  .\scripts\start_eval.ps1 -EvalFile "custom.json"
=============================================================================
#>

[CmdletBinding()]
param(
    [string]$EvalFile = "offline\datasets\eval.json",
    [string]$DbPath = ":memory:"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonCmd = $VenvPython
} else {
    $PythonCmd = "python"
}

if (-not (Test-Path "offline\datasets\eval.json")) {
    Write-Host "[Notice] Eval dataset not found. Generating now..." -ForegroundColor Yellow
    & $PythonCmd scripts\generate_dataset.py --output-dir offline\datasets --sample-count 250
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "     NL2SQL Benchmark Evaluator (AST EM & SQLite EX)  " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "Eval Dataset : $EvalFile" -ForegroundColor Green
Write-Host "Database     : $DbPath`n" -ForegroundColor Green

$env:PYTHONPATH = "$RepoRoot;" + $env:PYTHONPATH
& $PythonCmd offline\training\evaluate.py --eval-file $EvalFile --db $DbPath
