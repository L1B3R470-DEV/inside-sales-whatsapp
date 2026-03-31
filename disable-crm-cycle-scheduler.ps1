$ErrorActionPreference = 'Stop'

$taskName = 'CRM_CYCLE_N8N'
schtasks /Delete /TN $taskName /F | Out-Null

if ($LASTEXITCODE -ne 0) {
  throw "Falha ao remover tarefa agendada $taskName"
}

Write-Host "Tarefa $taskName removida."
