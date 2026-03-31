param(
  [Parameter(Mandatory = $true)]
  [string]$InstanceName,

  [string]$InstanceToken = "",

  [string]$PhoneNumber = "5575983211367",

  [string]$GlobalApiKey = "123456",
  [string]$BaseUrl = "http://localhost:8080",
  [switch]$LogoutFirst = $false
)

$PhoneNumber = ($PhoneNumber -replace "\D", "")
if (-not $PhoneNumber) {
  Write-Host "PhoneNumber invalido. Informe apenas digitos (DDD + numero)." -ForegroundColor Red
  exit 1
}

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

$encodedName = [uri]::EscapeDataString($InstanceName)
$encodedPhone = [uri]::EscapeDataString($PhoneNumber)
$logoutUri = ("{0}/instance/logout/{1}" -f $BaseUrl, $encodedName)
$connectUri = ("{0}/instance/connect/{1}?number={2}" -f $BaseUrl, $encodedName, $encodedPhone)

if ($LogoutFirst) {
  try {
    Invoke-RestMethod -Method Delete -Uri $logoutUri -Headers @{ apikey = $GlobalApiKey } | Out-Null
    Start-Sleep -Seconds 2
  } catch {
    $msg = $_.Exception.Message
    if ($msg -notmatch "\(400\)") {
      Write-Host "Aviso: nao foi possivel logout antes do pairing. Seguindo..." -ForegroundColor Yellow
    }
  }
}

$res = $null
$lastError = $null
for ($i = 1; $i -le 6; $i++) {
  try {
    $res = Invoke-RestMethod -Method Get -Uri $connectUri -Headers @{ apikey = $InstanceToken }
    break
  } catch {
    $lastError = $_.Exception.Message
    Start-Sleep -Seconds 2
  }
}

if (-not $res) {
  Write-Host "Erro ao solicitar pairing code: $lastError" -ForegroundColor Red
  exit 1
}

if (-not $res.pairingCode) {
  Write-Host "Pairing code nao retornado. Retorno atual:" -ForegroundColor Yellow
  Write-Host ($res | ConvertTo-Json -Depth 8)
  exit 1
}

$code = $res.pairingCode
Write-Host "Pairing code: $($code.Substring(0,4))-$($code.Substring(4,4))" -ForegroundColor Green
Write-Host "Pairing code (sem hifen): $code" -ForegroundColor Green
Set-Clipboard -Value $code
Write-Host "Codigo copiado para a area de transferencia." -ForegroundColor Green
