<#
=============================================================================
NL2SQL Pipeline — Foundation Model Downloader (Windows PowerShell)

Usage:
  .\scripts\download_model.ps1                     # Downloads default 0.5B model
  .\scripts\download_model.ps1 -Preset 7b          # Downloads flagship Qwen2.5-Coder-7B
  .\scripts\download_model.ps1 -Preset 1.5b        # Downloads balanced Qwen2.5-Coder-1.5B
  .\scripts\download_model.ps1 -Preset 7b-gguf     # Downloads GGUF Q4_K_M for CPU
  .\scripts\download_model.ps1 -ListPresets        # Lists all available presets
=============================================================================
#>

[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [string]$Preset = "",
    [string]$RepoId = "",
    [string]$OutputDir = "",
    [switch]$ListPresets = $false
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "     NL2SQL Foundation Base Model Downloader          " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonCmd = $VenvPython
} else {
    $PythonCmd = "python"
}

$Arguments = @("scripts\download_model.py")
if ($ListPresets) {
    $Arguments += "--list-presets"
} else {
    if ($Preset) { $Arguments += @("--preset", $Preset) }
    if ($RepoId) { $Arguments += @("--repo-id", $RepoId) }
    if ($OutputDir) { $Arguments += @("--output-dir", $OutputDir) }
}

& $PythonCmd $Arguments
