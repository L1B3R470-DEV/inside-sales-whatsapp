$ErrorActionPreference = 'Stop'
$env:Path += ';C:\Program Files\Docker\Docker\resources\bin'

Set-Location "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"

Write-Host '[crm-cycle] iniciando ciclo...'

$output = docker run --rm `
  -v ai_n8n_data:/data `
  -v "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES:/work" `
  python:3.11-slim `
  sh -lc "python /work/crm_cycle_engine.py"

if ($LASTEXITCODE -ne 0) {
  throw "[crm-cycle] falhou com exit code $LASTEXITCODE"
}

Write-Host '[crm-cycle] concluido:'
$output | ForEach-Object { Write-Host $_ }


