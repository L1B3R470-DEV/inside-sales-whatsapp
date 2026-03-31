@echo off
echo === CONFIGURAÇÃO ULTRA RÁPIDA DO CHATGPT CODEX ===
echo Tempo estimado: 30-60 segundos
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0setup_codex_fast.ps1"

if %errorLevel% == 0 (
    echo.
    echo [SUCESSO] Configuracao ultra-rapida concluida!
    echo Reinicie o sistema para aplicar as alteracoes.
) else (
    echo.
    echo [ERRO] Ocorreu um erro durante a configuracao.
)

pause
