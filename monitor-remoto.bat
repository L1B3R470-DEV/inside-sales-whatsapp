@echo off
powershell -NoLogo -ExecutionPolicy Bypass -File "%~dp0monitor-remoto.ps1"
echo.
echo Script encerrado com codigo: %ERRORLEVEL%
pause
