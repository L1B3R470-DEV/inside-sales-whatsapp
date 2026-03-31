$ErrorActionPreference = 'Stop'

powershell -ExecutionPolicy Bypass -File "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\run-crm-cycle.ps1"

function Get-EnvValue([string]$Path, [string]$Key, [string]$Default = '') {
  if (-not (Test-Path $Path)) { return $Default }
  $line = Get-Content $Path | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
  if (-not $line) { return $Default }
  return ($line -split '=', 2)[1].Trim()
}

function To-HostPath([string]$ContainerPath) {
  $p = $ContainerPath
  if ($null -eq $p) { $p = '' }
  $p = $p.Trim()
  if (-not $p) { return '' }
  if ($p.StartsWith('/work/')) {
    return ('C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\' + $p.Substring(6)).Replace('/', '\\')
  }
  return $p
}

$envFile = 'C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\.env'
$spreadsheetId = Get-EnvValue -Path $envFile -Key 'GOOGLE_SHEETS_SPREADSHEET_ID' -Default ''
$authMode = (Get-EnvValue -Path $envFile -Key 'GOOGLE_AUTH_MODE' -Default 'service_account').ToLower()

$ready = $false
if ($spreadsheetId) {
  if ($authMode -eq 'oauth_user') {
    $tokenPath = To-HostPath (Get-EnvValue -Path $envFile -Key 'GOOGLE_OAUTH_TOKEN_JSON_PATH' -Default '/work/google-oauth-token.json')
    $ready = Test-Path $tokenPath
  } else {
    $saPath = To-HostPath (Get-EnvValue -Path $envFile -Key 'GOOGLE_SERVICE_ACCOUNT_JSON_PATH' -Default '/work/google-service-account.json')
    $ready = Test-Path $saPath
  }
}

if ($ready) {
  powershell -ExecutionPolicy Bypass -File "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\run-crm-sheet-sync.ps1"
  Write-Host "[crm-cycle-with-sheets] ciclo CRM + sync Google Sheets concluido (auth_mode=$authMode)."
} else {
  Write-Host "[crm-cycle-with-sheets] Google Sheets nao configurado para auth_mode=$authMode. Executado somente ciclo CRM."
}

