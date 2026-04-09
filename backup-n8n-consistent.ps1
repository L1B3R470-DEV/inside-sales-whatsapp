$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backupDir = Join-Path $projectRoot 'backups\n8n_consistent'
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$wasRunning = $false
$wasAutohealRunning = $false
try {
  $state = docker inspect -f "{{.State.Running}}" n8n 2>$null
  $wasRunning = ($LASTEXITCODE -eq 0 -and "$state".Trim().ToLower() -eq 'true')
  $autohealState = docker inspect -f "{{.State.Running}}" n8n-autoheal 2>$null
  $wasAutohealRunning = ($LASTEXITCODE -eq 0 -and "$autohealState".Trim().ToLower() -eq 'true')
  if ($wasAutohealRunning) {
    docker stop n8n-autoheal | Out-Null
  }
  if ($wasRunning) {
    docker stop n8n | Out-Null
  }

  docker run --rm `
    -v ai_n8n_data:/data `
    -v "${projectRoot}:/work" `
    -v "${backupDir}:/backup" `
    python:3.11-slim `
    python /work/backup_n8n_sqlite_consistent.py
}
finally {
  if ($wasRunning) {
    docker start n8n | Out-Null
  }
  if ($wasAutohealRunning) {
    docker start n8n-autoheal | Out-Null
  }
}
