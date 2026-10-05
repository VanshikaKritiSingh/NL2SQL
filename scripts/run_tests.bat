@echo off
REM =============================================================================
REM NL2SQL Pipeline — Test Suite Launcher (Windows CMD)
REM =============================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_tests.ps1" %*
