@echo off
title REINICIAR WINDSURF E CODEX
color 0A
echo.
echo === REINICIANDO WINDSURF PARA APLICAR CONFIG ===
echo.

echo 1. Fechando Windsurf...
taskkill /f /im "Windsurf.exe" 2>nul
timeout /t 2 /nobreak >nul

echo 2. Limpando processos CODEX...
taskkill /f /im "codex.exe" 2>nul
timeout /t 2 /nobreak >nul

echo 3. Aguardando 5 segundos...
timeout /t 5 /nobreak >nul

echo 4. Reiniciando Windsurf...
start "" "C:\Users\murdo\AppData\Local\Programs\Windsurf\Windsurf.exe"

echo.
echo [OK] Windsurf reiniciado com nova configuracao!
echo Aguarde 30 segundos para o CODEX carregar completamente...
timeout /t 30 /nobreak >nul

echo.
echo === TESTE DE ACESSO ===
echo Tente executar uma operacao antes bloqueada agora.
echo.
pause
