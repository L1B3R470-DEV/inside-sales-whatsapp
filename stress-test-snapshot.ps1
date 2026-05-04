param(
  [string]$Number = "5575988340000",
  [string]$RunId = "STRESSREAL-2026-04-28-5575988340000"
)

$ErrorActionPreference = "Stop"
$projectDir = $PSScriptRoot
$outDir = Join-Path $projectDir ("stress-test-runs\" + $RunId)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$snapshotFile = Join-Path $outDir "pre-snapshot-reset-dry-run.json"
$healthFile = Join-Path $outDir "runtime-health.json"

$dryRun = & python (Join-Path $projectDir "reset-lead-state.py") --number $Number --project-dir $projectDir --dry-run --skip-backup --skip-restart
$dryRun | Set-Content -Encoding UTF8 $snapshotFile

$health = [ordered]@{
  runId = $RunId
  number = ($Number -replace "\D", "")
  createdAt = (Get-Date).ToString("o")
  routerHealth = $null
  n8nHealth = $null
  dockerPs = @()
}

try { $health.routerHealth = Invoke-RestMethod -Uri "http://localhost:8091/health" -TimeoutSec 10 } catch { $health.routerHealth = @{ error = $_.Exception.Message } }
try { $health.n8nHealth = Invoke-RestMethod -Uri "http://localhost:5678/healthz" -TimeoutSec 10 } catch { $health.n8nHealth = @{ error = $_.Exception.Message } }
$health.dockerPs = docker ps --format "{{.Names}}|{{.Status}}|{{.Ports}}"

$health | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $healthFile

Write-Host "Snapshot salvo em: $outDir" -ForegroundColor Green
Write-Host "Dry-run reset: $snapshotFile" -ForegroundColor Green
\n
