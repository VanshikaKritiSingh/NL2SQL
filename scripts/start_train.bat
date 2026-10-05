@echo off
REM =============================================================================
REM NL2SQL Pipeline — QLoRA Fine-Tuning Launcher (Windows CMD)
REM =============================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_train.ps1" %*
