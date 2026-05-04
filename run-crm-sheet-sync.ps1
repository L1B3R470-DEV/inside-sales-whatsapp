$ErrorActionPreference = 'Stop'

$dockerBin = 'C:\Program Files\Docker\Docker\resources\bin'
if (($env:Path -split ';') -notcontains $dockerBin) {
  $env:Path += ";$dockerBin"
}

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = 'C:\AUTOMACAO\dados'

Set-Location $ProjectDir

function Get-EnvValue([string]$Path, [string]$Key, [string]$Default = '') {
  if (-not (Test-Path -LiteralPath $Path)) { return $Default }
  $line = Get-Content -LiteralPath $Path | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
  if (-not $line) { return $Default }
  return ($line -split '=', 2)[1].Trim()
}

function To-HostPath([string]$ContainerPath) {
  $p = $ContainerPath
  if ($null -eq $p) { $p = '' }
  $p = $p.Trim()
  if (-not $p) { return '' }
  if ($p.StartsWith('/work/')) {
    return (Join-Path $ProjectDir $p.Substring(6)).Replace('/', '\')
  }
  if ($p.StartsWith('/runtime/')) {
    return (Join-Path $RuntimeDir $p.Substring(9)).Replace('/', '\')
  }
  return $p
}

$envFile = Join-Path $ProjectDir '.env'
$authMode = (Get-EnvValue -Path $envFile -Key 'GOOGLE_AUTH_MODE' -Default 'service_account').ToLower()
$spreadsheetId = Get-EnvValue -Path $envFile -Key 'GOOGLE_SHEETS_SPREADSHEET_ID' -Default ''

if (-not $spreadsheetId) {
  throw 'GOOGLE_SHEETS_SPREADSHEET_ID vazio no .env.'
}

if ($authMode -eq 'oauth_user') {
  $tokenContainerPath = Get-EnvValue -Path $envFile -Key 'GOOGLE_OAUTH_TOKEN_JSON_PATH' -Default '/work/google-oauth-token.json'
  $tokenHostPath = To-HostPath $tokenContainerPath
  if (-not (Test-Path -LiteralPath $tokenHostPath)) {
    throw "OAuth token nao encontrado: $tokenHostPath. Rode bootstrap-google-oauth-user.ps1 no projeto vigente."
  }
} else {
  $saContainerPath = Get-EnvValue -Path $envFile -Key 'GOOGLE_SERVICE_ACCOUNT_JSON_PATH' -Default '/work/google-service-account.json'
  $saHostPath = To-HostPath $saContainerPath
  if (-not (Test-Path -LiteralPath $saHostPath)) {
    throw "Credencial service account nao encontrada: $saHostPath"
  }
}

$image = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String -Pattern "^crm-sync-runner:latest$"
if (-not $image) {
  Write-Host '[crm-sheet-sync] imagem nao encontrada, buildando...'
  powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectDir 'build-crm-sync-image.ps1')
}

Write-Host "[crm-sheet-sync] iniciando sync bidirecional com Google Sheets (auth_mode=$authMode)..."
$output = docker run --rm `
  -v ai_n8n_data:/data `
  -v "${ProjectDir}:/work" `
  -v "${RuntimeDir}:/runtime" `
  -e N8N_DB=/data/database.sqlite `
  -e CRM_DB=/runtime/crm_operacional.sqlite `
  -e ENV_FILE=/work/.env `
  crm-sync-runner:latest `
  /work/crm_sheet_sync.py

if ($LASTEXITCODE -ne 0) {
  throw "[crm-sheet-sync] falhou com exit code $LASTEXITCODE"
}

Write-Host '[crm-sheet-sync] concluido:'
$output | ForEach-Object { Write-Host $_ }
\n
