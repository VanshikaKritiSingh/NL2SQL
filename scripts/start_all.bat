@echo off
REM =============================================================================
REM NL2SQL Pipeline — Full-Stack Launcher (Windows CMD)
REM =============================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_all.ps1" %*
