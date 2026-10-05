@echo off
REM =============================================================================
REM NL2SQL Pipeline — Foundation Model Downloader (Windows CMD)
REM =============================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0download_model.ps1" %*
