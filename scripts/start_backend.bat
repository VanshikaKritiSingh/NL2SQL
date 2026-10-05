@echo off
REM =============================================================================
REM NL2SQL Pipeline — FastAPI Backend Server Launcher (Windows CMD)
REM =============================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_backend.ps1" %*
