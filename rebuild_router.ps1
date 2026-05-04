Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$proj = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"
Set-Location $proj
Write-Host "[1/3] Compilando imagem Docker..." -ForegroundColor Cyan
docker build -t attendant-router:latest -f docker/router/Dockerfile .
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO no build!" -ForegroundColor Red; exit 1 }
Write-Host "[2/3] Reiniciando container router..." -ForegroundColor Cyan
docker compose up -d --no-deps router
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO ao subir container!" -ForegroundColor Red; exit 1 }
Write-Host "[3/3] Aguardando healthcheck..." -ForegroundColor Cyan
Start-Sleep -Seconds 8
$health = docker inspect --format="{{.State.Health.Status}}" router 2>&1
Write-Host "Health: $health" -ForegroundColor $(if ($health -eq "healthy") { "Green" } else { "Yellow" })
Write-Host "REBUILD CONCLUIDO. Teste o router em http://localhost:8091/health" -ForegroundColor Green
\n
