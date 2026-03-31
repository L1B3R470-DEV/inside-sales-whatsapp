param(
  [string]$ProjectDir = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES",
  [string]$RuntimeRoot = "C:\AUTOMACAO"
)

$healthUrl = "http://localhost:8091/health"
$logDir = Join-Path $RuntimeRoot "logs"
if (-not (Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

$stdout = Join-Path $logDir "router-service.out.log"
$stderr = Join-Path $logDir "router-service.err.log"
$scriptPath = Join-Path $ProjectDir "start-router-service.ps1"

function Test-Health {
  try {
    $resp = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3
    return ($resp.ok -eq $true)
  } catch {
    return $false
  }
}

function Test-RouterProcess {
  $procs = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match 'python' -and $_.CommandLine -match 'router_service.py'
  }
  return ($procs.Count -gt 0)
}

if (Test-Health) {
  Write-Output "already_healthy=true"
  exit 0
}

if (Test-RouterProcess) {
  Write-Output "already_running=true"
  exit 0
}

if (Test-Path $stdout) { Remove-Item $stdout -Force }
if (Test-Path $stderr) { Remove-Item $stderr -Force }

Start-Process `
  -FilePath "powershell.exe" `
  -ArgumentList "-ExecutionPolicy Bypass -File `"$scriptPath`" -RuntimeRoot `"$RuntimeRoot`"" `
  -WorkingDirectory $ProjectDir `
  -RedirectStandardOutput $stdout `
  -RedirectStandardError $stderr `
  -WindowStyle Hidden

Write-Output "started=true"
Write-Output "stdout=$stdout"
Write-Output "stderr=$stderr"
