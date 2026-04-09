param(
  [Parameter(Mandatory = $true)]
  [string]$Number,
  [string]$ProjectDir = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES",
  [string]$RuntimeRoot = "C:\AUTOMACAO",
  [string]$WorkflowId = "zN3heKJVLO8w4dG6",
  [switch]$DryRun,
  [switch]$SkipBackup,
  [switch]$SkipRestart,
  [switch]$ExclusiveAllowlist
)

$venvPython = Join-Path $ProjectDir ".venv-router\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }
$scriptPath = Join-Path $ProjectDir "reset-lead-state.py"

$argsList = @(
  $scriptPath,
  "--number", $Number,
  "--project-dir", $ProjectDir,
  "--runtime-root", $RuntimeRoot,
  "--workflow-id", $WorkflowId
)

if ($DryRun) { $argsList += "--dry-run" }
if ($SkipBackup) { $argsList += "--skip-backup" }
if ($SkipRestart) { $argsList += "--skip-restart" }
if ($ExclusiveAllowlist) { $argsList += "--exclusive-allowlist" }

& $pythonExe @argsList
