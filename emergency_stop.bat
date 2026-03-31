@echo off
title EMERGENCIA - PARAR SCRIPT
color 4F
echo.
echo [91m[1m!!! EMERGENCIA - RISCO CRITICO DETECTADO !!![0m
echo.
echo O script pode estar corrompendo seu sistema AGORA!
echo.
echo [91mOPCOES DE EMERGENCIA:[0m
echo.
echo 1. Forcar desligamento IMEDIATO (RECOMENDADO)
echo 2. Tentar parar processo PowerShell
echo 3. Abrir Gerenciador de Tarefas
echo.
echo [91mAVISO: Desligar pode causar perda de dados,[0m
echo [91mmas continuar pode CORROMPER O SISTEMA COMPLETO![0m
echo.
set /p opcao="Escolha (1-3): "

if "%opcao%"=="1" (
    echo.
    echo [91mForcando desligamento em 3 segundos...[0m
    timeout /t 3 /nobreak >nul
    shutdown /s /f /t 0
)

if "%opcao%"=="2" (
    echo.
    echo Tentando parar PowerShell...
    taskkill /f /im powershell.exe
    taskkill /f /im pwsh.exe
    echo Verifique se o processo parou...
    pause
)

if "%opcao%"=="3" (
    echo.
    echo Abrindo Gerenciador de Tarefas...
    taskmgr.exe
    echo Procure por processos PowerShell e finalize todos.
    pause
)
