param(
  [string]$ProjectDir = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES",
  [string]$RuntimeRoot = "C:\AUTOMACAO",
  [switch]$ForceInstallDeps,
  [switch]$Once
)

$ErrorActionPreference = "Stop"

$venvPath = Join-Path $ProjectDir ".venv-router"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$scriptPath = Join-Path $ProjectDir "ai_capacity_monitor.py"
$logDir = Join-Path $RuntimeRoot "logs"

if (-not (Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

if (-not (Test-Path $venvPath)) {
  python -m venv $venvPath
  $ForceInstallDeps = $true
}

if ($ForceInstallDeps) {
  & $pythonExe -m pip install --upgrade pip | Out-Null
  & $pythonExe -m pip install python-dotenv | Out-Null
}

$stdout = Join-Path $logDir "ai-capacity-monitor.out.log"
$stderr = Join-Path $logDir "ai-capacity-monitor.err.log"

if ($Once) {
  & $pythonExe -c "import json; import ai_capacity_monitor; print(json.dumps(ai_capacity_monitor.monitor_once(), ensure_ascii=False, indent=2))"
  exit $LASTEXITCODE
}

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match '^python(w)?(\.exe)?$' -and $_.CommandLine -like '*ai_capacity_monitor.py*'
}
if ($existing) {
  $pids = ($existing | Select-Object -ExpandProperty ProcessId) -join ","
  Write-Output "already_running=true"
  Write-Output "pids=$pids"
  Write-Output "stdout=$stdout"
  Write-Output "stderr=$stderr"
  exit 0
}

Start-Process `
  -FilePath "powershell.exe" `
  -ArgumentList "-NoLogo -ExecutionPolicy Bypass -Command `"& '$pythonExe' '$scriptPath'`"" `
  -WorkingDirectory $ProjectDir `
  -RedirectStandardOutput $stdout `
  -RedirectStandardError $stderr `
  -WindowStyle Hidden

Write-Output "started=true"
Write-Output "stdout=$stdout"
Write-Output "stderr=$stderr"
