param(
  [string]$ProjectDir = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES",
  [string]$RuntimeRoot = "C:\AUTOMACAO"
)

$ragDir = Join-Path $RuntimeRoot "rag"
$cacheDir = Join-Path $RuntimeRoot "cache"
$logsDir = Join-Path $RuntimeRoot "logs"
$dadosDir = Join-Path $RuntimeRoot "dados"
$scriptsDir = Join-Path $RuntimeRoot "scripts"
$knowledgeDir = Join-Path $ragDir "knowledge"
$vectorDir = Join-Path $ragDir "vector_store"
$projectKnowledgeDir = Join-Path $ProjectDir "CHATGPT_MACHINE_LEARNING"
$projectVectorDir = Join-Path $ProjectDir "rag_vector_store"
$projectDbPath = Join-Path $ProjectDir "router_runtime.sqlite"
$dbPath = Join-Path $dadosDir "router_runtime.sqlite"
$resetPs1 = Join-Path $ProjectDir "reset-lead-state.ps1"
$resetMenuPs1 = Join-Path $ProjectDir "reset-lead-state-menu.ps1"
$resetPy = Join-Path $ProjectDir "reset-lead-state.py"

foreach ($dir in @($RuntimeRoot, $ragDir, $cacheDir, $logsDir, $dadosDir, $scriptsDir)) {
  if (-not (Test-Path $dir)) {
    New-Item -ItemType Directory -Path $dir | Out-Null
  }
}

if (-not (Test-Path $knowledgeDir) -and (Test-Path $projectKnowledgeDir)) {
  cmd /c "mklink /J `"$knowledgeDir`" `"$projectKnowledgeDir`"" | Out-Null
}

if (-not (Test-Path $vectorDir) -and (Test-Path $projectVectorDir)) {
  New-Item -ItemType Directory -Path $vectorDir | Out-Null
  Get-ChildItem $projectVectorDir -Force | Where-Object { $_.Name -ne ".lock" } | ForEach-Object {
    Copy-Item $_.FullName $vectorDir -Recurse -Force
  }
}

if (-not (Test-Path $dbPath) -and (Test-Path $projectDbPath)) {
  Copy-Item $projectDbPath $dbPath -Force
}

$runtimeReadme = @"
Runtime operacional do SDR IA B2B

Estrutura:
- rag\knowledge -> base documental
- rag\vector_store -> banco vetorial local
- cache -> artefatos de cache
- logs -> logs do roteador
- dados -> sqlite e estado local
- scripts -> atalhos/automação operacional
"@

$runtimeReadme | Set-Content -Path (Join-Path $RuntimeRoot "README.txt") -Encoding UTF8

if (Test-Path $resetPs1) {
  Copy-Item $resetPs1 (Join-Path $scriptsDir "reset-lead-state.ps1") -Force
}
if (Test-Path $resetMenuPs1) {
  Copy-Item $resetMenuPs1 (Join-Path $scriptsDir "reset-lead-state-menu.ps1") -Force
}
if (Test-Path $resetPy) {
  Copy-Item $resetPy (Join-Path $scriptsDir "reset-lead-state.py") -Force
}

Write-Output "runtime_root=$RuntimeRoot"
Write-Output "knowledge_dir=$knowledgeDir"
Write-Output "vector_dir=$vectorDir"
Write-Output "db_path=$dbPath"
