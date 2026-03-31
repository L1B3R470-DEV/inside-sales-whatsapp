@echo off
cd /d "%~dp0"
echo [GIT] Sincronizando com repositorio remoto...
git pull origin main
echo.
echo [GIT] Estado atual:
git log --oneline -3
git status
pause
