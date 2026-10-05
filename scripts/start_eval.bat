@echo off
REM =============================================================================
REM NL2SQL Pipeline — Benchmark Evaluator Launcher (Windows CMD)
REM =============================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_eval.ps1" %*
