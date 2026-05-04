param(
  [Parameter(Mandatory = $true)]
  [string]$Text,

  [string]$ClientInstance = "STRESS_CLIENT_SETOR",
  [string]$AttendantNumber = "557583211367"
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

$body = @{
  number = ($AttendantNumber -replace "\D", "")
  text = $Text
} | ConvertTo-Json -Depth 6

$uri = "{0}/message/sendText/{1}" -f $baseUrl.TrimEnd("/"), [uri]::EscapeDataString($ClientInstance)
$response = Invoke-RestMethod -Method Post -Uri $uri -Headers @{ apikey = $apiKey } -ContentType "application/json; charset=utf-8" -Body $body -TimeoutSec 30
$response | ConvertTo-Json -Depth 8
\n
