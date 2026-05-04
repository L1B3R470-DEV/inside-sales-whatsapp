param(
  [Parameter(Mandatory = $true)]
  [string]$InstanceName,

  [string]$InstanceToken = "",

  [string]$GlobalApiKey = "123456",
  [string]$BaseUrl = "http://localhost:8080",
  [string]$Number = "5575983211367"
)

if ($InstanceToken -match "^<.*>$") {
  $InstanceToken = ""
}

if (-not $InstanceToken) {
  try {
    $instances = Invoke-RestMethod -Method Get -Uri ("{0}/instance/fetchInstances" -f $BaseUrl) -Headers @{ apikey = $GlobalApiKey }
    if (-not ($instances -is [System.Array])) {
      $instances = @($instances)
    }
    $instance = $instances | Where-Object { $_.name -eq $InstanceName } | Select-Object -First 1
    if (-not $instance) {
      Write-Host "Instancia '$InstanceName' nao encontrada. Informe -InstanceToken manualmente." -ForegroundColor Red
      exit 1
    }
    if (-not $instance.token) {
      Write-Host "Token da instancia '$InstanceName' nao retornado pela API. Informe -InstanceToken manualmente." -ForegroundColor Red
      exit 1
    }
    $InstanceToken = [string]$instance.token
    Write-Host "InstanceToken carregado automaticamente para '$InstanceName'." -ForegroundColor Cyan
  } catch {
    Write-Host "Falha ao carregar token automaticamente: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Informe -InstanceToken manualmente ou valide EVOLUTION_API_KEY." -ForegroundColor Yellow
    exit 1
  }
}

$uri = "$BaseUrl/instance/connect/$([uri]::EscapeDataString($InstanceName))"
if ($Number) {
  $Number = ($Number -replace "\D", "")
  $uri = ("{0}?number={1}" -f $uri, $Number)
}

try {
  $response = Invoke-RestMethod -Method Get -Uri $uri -Headers @{ apikey = $InstanceToken }
} catch {
  Write-Host "Falha ao buscar QR: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}

if ($response.pairingCode) {
  Write-Host "Pairing code: $($response.pairingCode)" -ForegroundColor Yellow
}

if (-not $response.base64) {
  Write-Host "Sem base64 de QR no retorno. Tente novamente em 2-5 segundos." -ForegroundColor Yellow
  Write-Host ("Retorno: " + ($response | ConvertTo-Json -Depth 6))
  exit 1
}

$parts = $response.base64 -split ",", 2
if ($parts.Count -ne 2) {
  Write-Host "Formato inesperado de base64." -ForegroundColor Red
  exit 1
}

$bytes = [Convert]::FromBase64String($parts[1])
$safeName = ($InstanceName -replace "[^a-zA-Z0-9_-]", "_")
$outFile = Join-Path $PSScriptRoot "qr-$safeName.png"
[IO.File]::WriteAllBytes($outFile, $bytes)

Write-Host "QR salvo em: $outFile" -ForegroundColor Green
Start-Process $outFile

