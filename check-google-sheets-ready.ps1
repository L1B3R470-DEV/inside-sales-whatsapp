$ErrorActionPreference = 'Stop'

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
if (-not (Test-Path $envFile)) {
  throw 'Arquivo .env nao encontrado em C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\.env'
}

$authMode = (Get-EnvValue -Path $envFile -Key 'GOOGLE_AUTH_MODE' -Default 'service_account').ToLower()
$spreadsheetId = Get-EnvValue -Path $envFile -Key 'GOOGLE_SHEETS_SPREADSHEET_ID' -Default ''

Write-Host "auth_mode=$authMode"
Write-Host "spreadsheet_id_set=$([bool]($spreadsheetId))"
if ($spreadsheetId) {
  Write-Host "spreadsheet_id=$spreadsheetId"
}

if ($authMode -eq 'oauth_user') {
  $clientPath = To-HostPath (Get-EnvValue -Path $envFile -Key 'GOOGLE_OAUTH_CLIENT_SECRET_JSON_PATH' -Default '/work/google-oauth-client.json')
  $tokenPath = To-HostPath (Get-EnvValue -Path $envFile -Key 'GOOGLE_OAUTH_TOKEN_JSON_PATH' -Default '/work/google-oauth-token.json')
  Write-Host "oauth_client_file_exists=$([bool](Test-Path $clientPath))"
  Write-Host "oauth_token_file_exists=$([bool](Test-Path $tokenPath))"
  Write-Host "oauth_client_path=$clientPath"
  Write-Host "oauth_token_path=$tokenPath"
} else {
  $credPath = To-HostPath (Get-EnvValue -Path $envFile -Key 'GOOGLE_SERVICE_ACCOUNT_JSON_PATH' -Default '/work/google-service-account.json')
  Write-Host "service_account_file_exists=$([bool](Test-Path $credPath))"
  Write-Host "service_account_path=$credPath"
}

