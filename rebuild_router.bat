@echo off
echo [1/3] Compilando imagem Docker...
cd /d "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"
docker build -t attendant-router:latest -f docker/router/Dockerfile .
if errorlevel 1 (echo ERRO no build! & pause & exit /b 1)
echo [2/3] Reiniciando container router...
docker compose up -d --no-deps router
if errorlevel 1 (echo ERRO ao subir container! & pause & exit /b 1)
echo [3/3] Aguardando 8 segundos...
timeout /t 8 /nobreak >nul
docker inspect --format="Health: {{.State.Health.Status}}" router
echo.
echo REBUILD CONCLUIDO. Pressione qualquer tecla para fechar.
pause
\n
