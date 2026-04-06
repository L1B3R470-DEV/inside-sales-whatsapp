param(
  [string]$ProjectDir = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES",
  [string]$RuntimeRoot = "C:\AUTOMACAO",
  [string]$AuthorizedNumber = "557588340000",
  [string]$RouterDbPath = "C:\AUTOMACAO\dados\router_runtime.sqlite",
  [string]$RouterBaseUrl = "http://localhost:8091",
  [string]$EvolutionBaseUrl = "http://localhost:8080",
  [string]$EvolutionInstance = "ATENDIMENTO_VENDAS_CLEAN",
  [string]$WorkflowId = "zN3heKJVLO8w4dG6",
  [int]$ResponseTimeoutSeconds = 75,
  [int]$RecoveryGraceSeconds = 35,
  [int]$PollIntervalSeconds = 8,
  [switch]$Once,
  [switch]$DrySend
)

$ErrorActionPreference = "Stop"

$logDir = Join-Path $RuntimeRoot "logs"
if (-not (Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

$stdout = Join-Path $logDir "test-conversation-watchdog.out.log"
$stderr = Join-Path $logDir "test-conversation-watchdog.err.log"
$scriptPath = Join-Path $ProjectDir "test_conversation_watchdog.py"
$venvPython = Join-Path $ProjectDir ".venv-router\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }

$args = @(
  "`"$scriptPath`"",
  "--authorized-number", $AuthorizedNumber,
  "--project-dir", "`"$ProjectDir`"",
  "--runtime-root", "`"$RuntimeRoot`"",
  "--router-db-path", "`"$RouterDbPath`"",
  "--router-base-url", $RouterBaseUrl,
  "--evolution-base-url", $EvolutionBaseUrl,
  "--evolution-instance", $EvolutionInstance,
  "--workflow-id", $WorkflowId,
  "--response-timeout-seconds", "$ResponseTimeoutSeconds",
  "--recovery-grace-seconds", "$RecoveryGraceSeconds",
  "--poll-interval-seconds", "$PollIntervalSeconds"
)

if ($Once) { $args += "--once" }
if ($DrySend) { $args += "--dry-send" }

if ($Once) {
  & $pythonExe @args
  exit $LASTEXITCODE
}

if (Test-Path $stdout) { Remove-Item $stdout -Force -ErrorAction SilentlyContinue }
if (Test-Path $stderr) { Remove-Item $stderr -Force -ErrorAction SilentlyContinue }

Start-Process `
  -FilePath $pythonExe `
  -ArgumentList $args `
  -WorkingDirectory $ProjectDir `
  -RedirectStandardOutput $stdout `
  -RedirectStandardError $stderr `
  -WindowStyle Hidden

Write-Output "started=true"
Write-Output "stdout=$stdout"
Write-Output "stderr=$stderr"
