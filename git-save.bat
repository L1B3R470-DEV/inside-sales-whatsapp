@echo off
cd /d "%~dp0"
echo [GIT] Verificando alteracoes...
git status
echo.

for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set DATA=%%c-%%b-%%a
for /f "tokens=1-2 delims=: " %%a in ("%time%") do set HORA=%%a%%b
set MSG=checkpoint %DATA% %HORA%

git add -A
git commit -m "%MSG%"
git push origin main
echo.
echo [GIT] Salvo com sucesso!
git log --oneline -3
pause
