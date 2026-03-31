$ErrorActionPreference = 'Stop'
$env:Path += ';C:\Program Files\Docker\Docker\resources\bin'

Set-Location "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"
docker build -f Dockerfile.crm-sync -t crm-sync-runner:latest .

if ($LASTEXITCODE -ne 0) {
  throw 'Falha ao buildar imagem crm-sync-runner:latest'
}

Write-Host 'Imagem crm-sync-runner:latest pronta.'


