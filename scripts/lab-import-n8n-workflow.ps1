param(
  [string]$WorkflowBackupDir,
  [string]$WorkflowId = "zN3heKJVLO8w4dG6"
)

$ErrorActionPreference = "Stop"

if (-not $WorkflowBackupDir) {
  $latest = Get-ChildItem -LiteralPath "C:\AUTOMACAO\backups" -Directory |
    Where-Object { $_.Name -like "lab_upgrade_n8n_evolution_rag_*" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if (-not $latest) { throw "Nenhum backup lab_upgrade_n8n_evolution_rag_* encontrado." }
  $WorkflowBackupDir = Join-Path $latest.FullName "n8n\workflows"
}

$workflowFile = Get-ChildItem -LiteralPath $WorkflowBackupDir -Filter "$WorkflowId*.json" -File -ErrorAction SilentlyContinue |
  Select-Object -First 1

if (-not $workflowFile) {
  $workflowFile = Get-ChildItem -LiteralPath $WorkflowBackupDir -Filter "*.json" -File |
    Where-Object { Select-String -LiteralPath $_.FullName -Pattern $WorkflowId -Quiet } |
    Select-Object -First 1
}

if (-not $workflowFile) { throw "Workflow $WorkflowId nao encontrado em $WorkflowBackupDir." }

docker cp $workflowFile.FullName "n8n-lab:/tmp/$($workflowFile.Name)" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Falha ao copiar workflow para n8n-lab." }

docker exec n8n-lab n8n import:workflow --input="/tmp/$($workflowFile.Name)" | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Falha ao importar workflow no n8n-lab." }

docker exec n8n-lab n8n update:workflow --id="$WorkflowId" --active=true | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Falha ao ativar workflow no n8n-lab." }

docker exec n8n-lab n8n list:workflow --active=true --onlyId
if ($LASTEXITCODE -ne 0) { throw "Falha ao listar workflows ativos no n8n-lab." }
