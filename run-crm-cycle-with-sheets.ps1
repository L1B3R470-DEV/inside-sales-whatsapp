$ErrorActionPreference = 'Stop'

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = 'C:\AUTOMACAO\dados'

powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectDir 'run-crm-cycle.ps1')

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
$spreadsheetId = Get-EnvValue -Path $envFile -Key 'GOOGLE_SHEETS_SPREADSHEET_ID' -Default ''
$authMode = (Get-EnvValue -Path $envFile -Key 'GOOGLE_AUTH_MODE' -Default 'service_account').ToLower()

$ready = $false
if ($spreadsheetId) {
  if ($authMode -eq 'oauth_user') {
    $tokenPath = To-HostPath (Get-EnvValue -Path $envFile -Key 'GOOGLE_OAUTH_TOKEN_JSON_PATH' -Default '/work/google-oauth-token.json')
    $ready = Test-Path -LiteralPath $tokenPath
  } else {
    $saPath = To-HostPath (Get-EnvValue -Path $envFile -Key 'GOOGLE_SERVICE_ACCOUNT_JSON_PATH' -Default '/work/google-service-account.json')
    $ready = Test-Path -LiteralPath $saPath
  }
}

if ($ready) {
  powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectDir 'run-crm-sheet-sync.ps1')
  Write-Host "[crm-cycle-with-sheets] ciclo CRM + sync Google Sheets concluido (auth_mode=$authMode)."
} else {
  Write-Host "[crm-cycle-with-sheets] Google Sheets nao configurado para auth_mode=$authMode. Executado somente ciclo CRM."
}
