$ErrorActionPreference = 'Stop'
$env:Path += ';C:\Program Files\Docker\Docker\resources\bin'

Set-Location "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"
if (-not (Test-Path '.env')) {
  Copy-Item '.env.example' '.env'
  Write-Host 'Arquivo .env criado a partir do .env.example. Atualize OPENAI_API_KEY antes de usar.'
}

docker compose pull
docker compose up -d
docker compose ps


