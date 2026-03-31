param(
  [string]$ProjectDir = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES",
  [string]$RuntimeRoot = "C:\AUTOMACAO",
  [string]$HealthUrl = "http://localhost:8091/health",
  [int]$HealthTimeoutSeconds = 8,
  [int]$StartWaitSeconds = 15
)

$ErrorActionPreference = "Stop"

$logDir = Join-Path $RuntimeRoot "logs"
if (-not (Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

$logFile = Join-Path $logDir "router-watchdog.log"
$lockFile = Join-Path $logDir "router-watchdog.lock"
$detachedStarter = Join-Path $ProjectDir "start-router-service-detached.ps1"

function Write-Log {
  param(
    [string]$Level,
    [string]$Message
  )

  $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $logFile -Value "[$timestamp] [$Level] $Message"
}

function Test-Health {
  try {
    $resp = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec $HealthTimeoutSeconds
    return ($resp.ok -eq $true)
  } catch {
    return $false
  }
}

try {
  if (Test-Path $lockFile) {
    $ageSeconds = ((Get-Date) - (Get-Item $lockFile).LastWriteTime).TotalSeconds
    if ($ageSeconds -lt 120) {
      Write-Log -Level "INFO" -Message "Watchdog skipped: another run is active."
      exit 0
    }
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
  }

  Set-Content -Path $lockFile -Value (Get-Date -Format "o")

  if (Test-Health) {
    Write-Log -Level "INFO" -Message "Router healthcheck OK."
    exit 0
  }

  Write-Log -Level "WARN" -Message "Router healthcheck failed. Attempting restart."

  if (-not (Test-Path $detachedStarter)) {
    throw "Detached starter not found at $detachedStarter"
  }

  powershell.exe -NoLogo -ExecutionPolicy Bypass -File $detachedStarter -ProjectDir $ProjectDir -RuntimeRoot $RuntimeRoot | Out-Null
  Start-Sleep -Seconds $StartWaitSeconds

  if (Test-Health) {
    Write-Log -Level "INFO" -Message "Router restart successful."
    exit 0
  }

  Write-Log -Level "ERROR" -Message "Router restart attempted but healthcheck is still failing."
  exit 1
} catch {
  Write-Log -Level "ERROR" -Message $_.Exception.Message
  exit 1
} finally {
  if (Test-Path $lockFile) {
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
  }
}
