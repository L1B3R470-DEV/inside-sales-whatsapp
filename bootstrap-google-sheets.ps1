$ErrorActionPreference = 'Stop'
$env:Path += ';C:\Program Files\Docker\Docker\resources\bin'

Set-Location "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"

if (-not (Test-Path 'google-service-account.json')) {
  throw 'Arquivo C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\google-service-account.json nao encontrado.'
}

$image = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String -Pattern "^crm-sync-runner:latest$"
if (-not $image) {
  powershell -ExecutionPolicy Bypass -File "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\build-crm-sync-image.ps1"
}

$output = docker run --rm `
  -v "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES:/work" `
  crm-sync-runner:latest `
  /work/bootstrap_google_sheet.py

if ($LASTEXITCODE -ne 0) {
  throw "Falha no bootstrap Google Sheets. exit code: $LASTEXITCODE"
}

$output | ForEach-Object { Write-Host $_ }


