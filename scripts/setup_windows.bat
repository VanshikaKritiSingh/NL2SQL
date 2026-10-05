@echo off
REM =============================================================================
REM NL2SQL Pipeline — Windows Command Prompt Setup Launcher
REM =============================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1" %*
pause
