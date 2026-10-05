@echo off
REM =============================================================================
REM NL2SQL Pipeline — Desktop & Web Studio GUI Launcher (Windows CMD)
REM =============================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_gui.ps1" %*
