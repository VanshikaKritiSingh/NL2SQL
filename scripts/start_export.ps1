<#
=============================================================================
NL2SQL Pipeline — LoRA Merge & GGUF / Ollama Exporter (Windows PowerShell)

Usage:
  .\scripts\start_export.ps1                      # Merges default LoRA checkpoint
  .\scripts\start_export.ps1 -Base "Qwen/Qwen2.5-Coder-7B-Instruct" -Lora "offline\checkpoints\my_lora"
=============================================================================
#>

[CmdletBinding()]
param(
    [string]$Base = "Qwen/Qwen2.5-Coder-7B-Instruct",
    [string]$Lora = "offline\checkpoints\qwen2.5-coder-7b-qlora",
    [string]$MergedOut = "offline\checkpoints\qwen2.5-coder-7b-merged",
    [string]$GgufOut = "offline\checkpoints\gguf"
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

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "     NL2SQL Model Exporter: LoRA Merge & GGUF Modelfile" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

& $PythonCmd offline\training\export_gguf.py --base $Base --lora $Lora --merged-out $MergedOut --gguf-out $GgufOut
