$ErrorActionPreference = 'Stop'
$env:Path += ';C:\Program Files\Docker\Docker\resources\bin'

Set-Location "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"

$clientJson = 'C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\google-oauth-client.json'
if (-not (Test-Path $clientJson)) {
  throw 'Arquivo C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\google-oauth-client.json nao encontrado. Crie credencial OAuth Client ID (Desktop app) no Google Cloud e salve esse JSON.'
}

$image = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String -Pattern "^crm-sync-runner:latest$"
if (-not $image) {
  powershell -ExecutionPolicy Bypass -File "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\build-crm-sync-image.ps1"
}

Write-Host '[oauth-bootstrap] iniciando autorizacao OAuth de usuario (URL + codigo no terminal)...'
docker run --rm -it `
  -p 8765:8765 `
  -v "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES:/work" `
  crm-sync-runner:latest `
  /work/bootstrap_google_oauth_user.py

if ($LASTEXITCODE -ne 0) {
  throw "Falha no bootstrap OAuth. Exit code: $LASTEXITCODE"
}

Write-Host '[oauth-bootstrap] concluido.'


