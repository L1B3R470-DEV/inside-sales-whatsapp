param(
  [string]$Number = "5575988340000",
  [switch]$DryRun = $false,
  [switch]$SkipRestart = $false,
  [switch]$SkipBackup = $true
)

$ErrorActionPreference = "Stop"
$projectDir = $PSScriptRoot
$argsList = @(
  "--number", ($Number -replace "\D", ""),
  "--project-dir", $projectDir
)

if ($DryRun) { $argsList += "--dry-run" }
if ($SkipRestart) { $argsList += "--skip-restart" }
if ($SkipBackup) { $argsList += "--skip-backup" }

& python (Join-Path $projectDir "reset-lead-state.py") @argsList
\n
