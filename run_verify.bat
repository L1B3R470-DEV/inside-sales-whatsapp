@echo off
echo === VERIFICAÇÃO COMPLETA DE ACESSO TOTAL ===
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0verify_total_access.ps1"

pause
