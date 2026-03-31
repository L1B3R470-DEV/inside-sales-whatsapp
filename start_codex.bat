@echo off
title INICIALIZAR CODEX COM PERMISSOES
color 0E
echo.
echo === INICIALIZANDO CODEX COM ACESSO TOTAL ===
echo.

echo 1. Verificando executavel...
if not exist "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex.exe" (
    echo [ERRO] Executavel CODEX nao encontrado!
    pause
    exit /b 1
)

echo 2. Configurando permissoes...
icacls "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex.exe" /grant "LIBERNOTE\Liberato":(F) /F
icacls "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex.exe" /grant "LIBERNOTE\Luiza":(F) /F
icacls "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex.exe" /grant "Administradores":(F) /F

echo 3. Iniciando CODEX...
cd /d "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64"
start "" codex.exe app-server --analytics-default-enable

echo 4. Aguardando inicializacao...
timeout /t 10 /nobreak >nul

echo 5. Verificando se esta rodando...
tasklist | findstr "codex.exe" >nul
if %errorLevel% == 0 (
    echo [SUCESSO] CODEX esta rodando!
    echo Tente usar o comando: chatgpt.openSidebar
) else (
    echo [ERRO] CODEX nao iniciou!
    echo Verifique o log em: C:\Users\murdo\.codex\.sandbox\sandbox.log
)

echo.
pause
