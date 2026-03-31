param(
  [string]$ProjectDir = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES",
  [string]$RuntimeRoot = "C:\AUTOMACAO",
  [switch]$ForceInstallDeps
)

$healthUrl = "http://localhost:8091/health"
$envFile = Join-Path $ProjectDir ".env"
$venvPath = Join-Path $ProjectDir ".venv-router"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$requirements = Join-Path $ProjectDir "requirements-router.txt"
$serviceScript = Join-Path $ProjectDir "router_service.py"
$ragDir = Join-Path $RuntimeRoot "rag"
$cacheDir = Join-Path $RuntimeRoot "cache"
$logsDir = Join-Path $RuntimeRoot "logs"
$dadosDir = Join-Path $RuntimeRoot "dados"
$scriptsDir = Join-Path $RuntimeRoot "scripts"
$knowledgeDir = Join-Path $ragDir "knowledge"
$vectorDir = Join-Path $ragDir "vector_store"
$dbPath = Join-Path $dadosDir "router_runtime.sqlite"
$projectKnowledgeDir = Join-Path $ProjectDir "CHATGPT_MACHINE_LEARNING"
$projectVectorDir = Join-Path $ProjectDir "rag_vector_store"
$projectDbPath = Join-Path $ProjectDir "router_runtime.sqlite"

function Test-Health {
  try {
    $resp = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3
    return ($resp.ok -eq $true)
  } catch {
    return $false
  }
}

if (Test-Health) {
  Write-Output "router_already_healthy=true"
  exit 0
}

if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if (-not $_ -or $_.Trim().StartsWith('#')) { return }
    $parts = $_ -split '=', 2
    if ($parts.Count -ne 2) { return }
    $name = $parts[0].Trim()
    $value = $parts[1].Trim()
    if ($name) {
      Set-Item -Path ("Env:{0}" -f $name) -Value $value
    }
  }
}

foreach ($dir in @($RuntimeRoot, $ragDir, $cacheDir, $logsDir, $dadosDir, $scriptsDir)) {
  if (-not (Test-Path $dir)) {
    New-Item -ItemType Directory -Path $dir | Out-Null
  }
}

if (-not (Test-Path $knowledgeDir) -and (Test-Path $projectKnowledgeDir)) {
  cmd /c "mklink /J `"$knowledgeDir`" `"$projectKnowledgeDir`"" | Out-Null
}

if (-not (Test-Path $dbPath) -and (Test-Path $projectDbPath)) {
  Copy-Item $projectDbPath $dbPath -Force
}

if (-not (Test-Path $vectorDir) -and (Test-Path $projectVectorDir)) {
  Copy-Item $projectVectorDir $vectorDir -Recurse -Force
}

if (-not (Test-Path $venvPath)) {
  python -m venv $venvPath
  $ForceInstallDeps = $true
}

if ($ForceInstallDeps) {
  & $pythonExe -m pip install --upgrade pip
  & $pythonExe -m pip install -r $requirements
} else {
  Write-Output "deps_install_skipped=true (use -ForceInstallDeps to reinstall)"
}

$env:AUTOMACAO_ROOT = $RuntimeRoot
$env:ROUTER_ML_DIR = $knowledgeDir
$env:ROUTER_DB_PATH = $dbPath
$env:ROUTER_QDRANT_PATH = $vectorDir
$env:ROUTER_QDRANT_COLLECTION = "knowledge_chunks"
$env:ROUTER_OPENAI_EMBED_MODEL = "text-embedding-3-small"
$env:ROUTER_WATCH_INTERVAL_SECONDS = "900"

& $pythonExe $serviceScript
