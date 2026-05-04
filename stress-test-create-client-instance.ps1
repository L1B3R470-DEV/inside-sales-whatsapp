param(
  [string]$ClientInstance = "STRESS_CLIENT_SETOR",
  [string]$ClientNumber = "5575988340000"
)

$ErrorActionPreference = "Stop"
$envMap = @{}
Get-Content (Join-Path $PSScriptRoot ".env") | ForEach-Object {
  if ($_ -match '^([^#=]+)=(.*)$') { $envMap[$matches[1]] = $matches[2] }
}

$baseUrl = $envMap["EVOLUTION_BASE_URL"]
if (-not $baseUrl) { $baseUrl = "http://localhost:8080" }
$apiKey = $envMap["EVOLUTION_API_KEY"]
if (-not $apiKey) { throw "EVOLUTION_API_KEY ausente no .env" }

$headers = @{ apikey = $apiKey }
$instances = Invoke-RestMethod -Method Get -Uri ("{0}/instance/fetchInstances" -f $baseUrl.TrimEnd("/")) -Headers $headers -TimeoutSec 30
if (-not ($instances -is [System.Array])) { $instances = @($instances) }
$existing = $instances | Where-Object { $_.name -eq $ClientInstance } | Select-Object -First 1

if (-not $existing) {
  $body = @{
    instanceName = $ClientInstance
    token = [guid]::NewGuid().ToString().ToUpper()
    qrcode = $true
    number = ($ClientNumber -replace "\D", "")
    integration = "WHATSAPP-BAILEYS"
  } | ConvertTo-Json -Depth 8
  Invoke-RestMethod -Method Post -Uri ("{0}/instance/create" -f $baseUrl.TrimEnd("/")) -Headers $headers -ContentType "application/json; charset=utf-8" -Body $body -TimeoutSec 30 | Out-Null
  Start-Sleep -Seconds 2
}

try {
  $webhook = Invoke-RestMethod -Method Get -Uri ("{0}/webhook/find/{1}" -f $baseUrl.TrimEnd("/"), [uri]::EscapeDataString($ClientInstance)) -Headers $headers -TimeoutSec 15
  if ($webhook -and $webhook.enabled) {
    $disableBody = @{ enabled = $false; url = ""; webhookByEvents = $false; events = @() } | ConvertTo-Json -Depth 8
    Invoke-RestMethod -Method Post -Uri ("{0}/webhook/set/{1}" -f $baseUrl.TrimEnd("/"), [uri]::EscapeDataString($ClientInstance)) -Headers $headers -ContentType "application/json; charset=utf-8" -Body $disableBody -TimeoutSec 15 | Out-Null
  }
} catch {
  Write-Host "Webhook da instancia cliente nao encontrado ou ja desabilitado: $($_.Exception.Message)" -ForegroundColor Yellow
}

& (Join-Path $PSScriptRoot "show-evolution-qr.ps1") -InstanceName $ClientInstance -GlobalApiKey $apiKey -BaseUrl $baseUrl -Number $ClientNumber
\n
