@echo off
title INICIALIZAR CODEX COMO ADMIN
color 0C
echo.
echo === INICIALIZANDO CODEX COMO ADMINISTRADOR ===
echo.

echo 1. Verificando se esta como Administrador...
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERRO] Execute este script como Administrador!
    pause
    exit /b 1
)

echo 2. Parando processos CODEX existentes...
taskkill /f /im codex.exe 2>nul
timeout /t 2 /nobreak >nul

echo 3. Configurando permissões completas...
takeown /f "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex.exe"
icacls "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex.exe" /grant "Todos":(F) /T

echo 4. Configurando variáveis de ambiente...
set CODEX_FULL_ACCESS=1
set CODEX_AUTONOMOUS=1
set CODEX_BYPASS_SECURITY=1

echo 5. Iniciando CODEX com privilégios máximos...
cd /d "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64"
runas /user:Administradores /savecred "codex.exe app-server --analytics-default-enable"

echo 6. Aguardando inicializacao...
timeout /t 15 /nobreak >nul

echo 7. Verificando se esta rodando...
tasklist | findstr "codex.exe" >nul
if %errorLevel% == 0 (
    echo [SUCESSO] CODEX esta rodando como Administrador!
    echo 
    echo === COMANDOS DISPONIVEIS ===
    echo chatgpt.openSidebar
    echo chatgpt.newChat
    echo chatgpt.newCodexPanel
    echo 
    echo Tente usar Ctrl+Shift+P e digite "Codex"
) else (
    echo [ERRO] CODEX nao iniciou!
    echo Verificando logs...
    type "C:\Users\murdo\.codex\.sandbox\sandbox.log" | more
)

echo.
pause
