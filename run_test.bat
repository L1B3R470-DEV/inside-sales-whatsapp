@echo off
echo === TESTANDO ACESSO AUTONOMO DO CHATGPT CODEX ===
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0test_codex_access.ps1"

pause
