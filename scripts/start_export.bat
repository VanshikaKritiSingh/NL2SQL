@echo off
REM =============================================================================
REM NL2SQL Pipeline — LoRA Merge & GGUF Exporter Launcher (Windows CMD)
REM =============================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_export.ps1" %*
