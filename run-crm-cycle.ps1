$ErrorActionPreference = 'Stop'

$dockerBin = 'C:\Program Files\Docker\Docker\resources\bin'
if (($env:Path -split ';') -notcontains $dockerBin) {
  $env:Path += ";$dockerBin"
}

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = 'C:\AUTOMACAO\dados'
$RuntimeCrm = Join-Path $RuntimeDir 'crm_operacional.sqlite'
$RuntimeRouter = Join-Path $RuntimeDir 'router_runtime.sqlite'

if (-not (Test-Path -LiteralPath $ProjectDir)) {
  throw "Projeto nao encontrado: $ProjectDir"
}
if (-not (Test-Path -LiteralPath $RuntimeCrm)) {
  throw "CRM runtime nao encontrado: $RuntimeCrm"
}
if (-not (Test-Path -LiteralPath $RuntimeRouter)) {
  throw "Router runtime nao encontrado: $RuntimeRouter"
}

Set-Location $ProjectDir

Write-Host "[crm-cycle] projeto: $ProjectDir"
Write-Host "[crm-cycle] CRM runtime: $RuntimeCrm"
Write-Host '[crm-cycle] iniciando ciclo...'

$output = docker run --rm `
  -v ai_n8n_data:/data `
  -v "${ProjectDir}:/work" `
  -v "${RuntimeDir}:/runtime" `
  -e N8N_DB=/data/database.sqlite `
  -e CRM_DB=/runtime/crm_operacional.sqlite `
  -e CRM_EXPORT_DIR=/runtime/crm_exports `
  -e LEADS_WORKBOOK_PATH=/runtime/LEADS_INSIDE_SALES_AUTO.xlsx `
  -e LEADS_WORKBOOK_EXPORT_PATH=/runtime/crm_exports/LEADS_INSIDE_SALES_AUTO.xlsx `
  python:3.11-slim `
  sh -lc "python /work/crm_cycle_engine.py"

if ($LASTEXITCODE -ne 0) {
  throw "[crm-cycle] falhou com exit code $LASTEXITCODE"
}

Write-Host '[crm-cycle] concluido:'
$output | ForEach-Object { Write-Host $_ }
\n
