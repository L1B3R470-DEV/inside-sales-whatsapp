@echo off
echo === CONFIGURANDO ACESSO TOTAL AO CHATGPT CODEX ===
echo.

:: Verificar se está executando como administrador
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Executando como Administrador
) else (
    echo [ERRO] Execute este script como Administrador!
    pause
    exit /b 1
)

:: Executar script PowerShell
powershell -ExecutionPolicy Bypass -File "%~dp0setup_codex_full_access.ps1"

if %errorLevel% == 0 (
    echo.
    echo [SUCESSO] Configuracao concluida!
    echo Reinicie o sistema para aplicar todas as alteracoes.
) else (
    echo.
    echo [ERRO] Ocorreu um erro durante a configuracao.
)

pause
