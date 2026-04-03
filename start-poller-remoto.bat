@echo off
title OpenClaw - Poller Codex Remoto (Orquestrador)
cd /d "%~dp0"

echo.
echo ============================================
echo  OpenClaw - Poller Codex Remoto
echo  Modo: AUTONOMO (relay=false)
echo  Repo: %~dp0
echo ============================================
echo.

echo [1/2] Atualizando repositorio...
git pull origin master
if %ERRORLEVEL% NEQ 0 (
    echo AVISO: git pull falhou. Continuando com versao local.
)

echo.
echo [2/2] Iniciando poller (Ctrl+C para parar)...
echo.

python "%~dp0poller-codex-remoto.py" --relay false --repo-dir "." --interval 60 --claude-path "C:\Users\murdo\AppData\Roaming\npm\claude.cmd"

echo.
echo Poller encerrado com codigo: %ERRORLEVEL%
pause
