<#
=============================================================================
NL2SQL Pipeline — QLoRA Fine-Tuning Launcher (Windows PowerShell)

Usage:
  .\scripts\start_train.ps1                       # Fine-tunes default model
  .\scripts\start_train.ps1 -Model "Qwen/Qwen2.5-Coder-7B-Instruct"
  .\scripts\start_train.ps1 -Epochs 5
=============================================================================
#>

[CmdletBinding()]
param(
    [string]$Model = "",
    [string]$Dataset = "offline\datasets\train.json",
    [string]$Output = "offline\checkpoints\qwen2.5-coder-qlora",
    [int]$Epochs = 3
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

# Ensure dataset exists
if (-not (Test-Path "offline\datasets\train.json")) {
    Write-Host "[Notice] Synthetic dataset not found. Generating now..." -ForegroundColor Yellow
    & $PythonCmd scripts\generate_dataset.py --output-dir offline\datasets --sample-count 250
}

# Determine default model
if (-not $Model) {
    if (Test-Path "offline\models\qwen2.5-coder-0.5b-instruct") {
        $Model = "offline\models\qwen2.5-coder-0.5b-instruct"
    } else {
        $Model = "Qwen/Qwen2.5-Coder-7B-Instruct"
    }
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "     NL2SQL Offline Fine-Tuning Suite (QLoRA)        " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "Base Model : $Model" -ForegroundColor Green
Write-Host "Dataset    : $Dataset" -ForegroundColor Green
Write-Host "Output Dir : $Output" -ForegroundColor Green
Write-Host "Epochs     : $Epochs`n" -ForegroundColor Green

& $PythonCmd offline\training\train_qlora.py --model $Model --dataset $Dataset --output $Output --epochs $Epochs
