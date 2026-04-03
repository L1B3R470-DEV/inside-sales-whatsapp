$ProjectDir = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"
$InboxDir   = "C:\AUTOMACAO\cowork\claude_bridge\inbox_for_claude"
$OutboxDir  = "C:\AUTOMACAO\cowork\claude_bridge\outbox_from_claude"
$AcksDir    = "C:\AUTOMACAO\cowork\claude_bridge\ack_from_codex"

$host.UI.RawUI.WindowTitle = "Bridge Poll"
Clear-Host

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "  BRIDGE POLL - CICLO AUTONOMO OPENLAW" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. GIT PULL
Write-Host "[1/4] git pull..." -ForegroundColor Yellow
Set-Location $ProjectDir
$pull = git pull origin main 2>&1
Write-Host "  $pull" -ForegroundColor Gray
Write-Host ""

# 2. DOCKER
Write-Host "[2/4] Containers Docker..." -ForegroundColor Yellow
$containers = docker ps --format "{{.Names}}|{{.Status}}|{{.Ports}}" 2>$null
if ($containers) {
    foreach ($line in $containers) {
        $parts = $line -split "\|"
        $name   = $parts[0].PadRight(22)
        $status = $parts[1].PadRight(20)
        $ports  = $parts[2]
        $color  = if ($status -match "Up") { "Green" } else { "Red" }
        Write-Host "  $name $status $ports" -ForegroundColor $color
    }
} else {
    Write-Host "  (docker nao acessivel)" -ForegroundColor Red
}
Write-Host ""

# 3. ROUTER HEALTH
Write-Host "[3/4] Router health..." -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod "http://localhost:8091/health" -TimeoutSec 3
    Write-Host "  ok=$($r.ok)  docs=$($r.activeDocuments)  chunks=$($r.activeChunks)  cache=$($r.cacheItems)" -ForegroundColor Green
} catch {
    Write-Host "  ROUTER OFFLINE" -ForegroundColor Red
}
try {
    $n8n = Invoke-WebRequest "http://localhost:5678/healthz" -TimeoutSec 3 -UseBasicParsing
    Write-Host "  n8n: $($n8n.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  n8n: OFFLINE" -ForegroundColor Red
}
Write-Host ""

# 4. BRIDGE INBOX
Write-Host "[4/4] Bridge inbox..." -ForegroundColor Yellow
$inbox  = (Get-ChildItem $InboxDir  -Filter *.json -EA SilentlyContinue).Count
$outbox = (Get-ChildItem $OutboxDir -Filter *.json -EA SilentlyContinue).Count
$acks   = (Get-ChildItem $AcksDir   -Filter *.json -EA SilentlyContinue).Count
Write-Host "  inbox=$inbox  outbox(replies)=$outbox  acks=$acks" -ForegroundColor White
Write-Host ""

$tasks = Get-ChildItem $InboxDir -Filter *.json -EA SilentlyContinue |
         Sort-Object LastWriteTime -Descending |
         Select-Object -First 10

foreach ($f in $tasks) {
    try {
        $j = Get-Content $f.FullName -Raw | ConvertFrom-Json
        # Checa se existe reply correspondente pelo task_id
        $replyFile = Get-ChildItem $OutboxDir -Filter "*.json" -EA SilentlyContinue |
                     Where-Object {
                         try { (Get-Content $_.FullName -Raw | ConvertFrom-Json).task_id -eq $j.task_id } catch { $false }
                     } | Select-Object -First 1
        if ($replyFile) {
            Write-Host "  [REPLY OK] $($j.task_id)" -ForegroundColor Green
            Write-Host "             $($j.title)" -ForegroundColor DarkGray
        } else {
            Write-Host "  [PENDENTE] $($j.task_id)" -ForegroundColor Red
            Write-Host "             $($j.title)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [?] $($f.Name)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "--------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  ACKs recentes:" -ForegroundColor Yellow
$recentAcks = Get-ChildItem $AcksDir -Filter *.json -EA SilentlyContinue |
              Sort-Object LastWriteTime -Descending |
              Select-Object -First 5
foreach ($f in $recentAcks) {
    try {
        $j = Get-Content $f.FullName -Raw | ConvertFrom-Json
        Write-Host "  $($j.reply_id)  $($j.status)  $($j.acked_at)" -ForegroundColor DarkGray
    } catch {
        Write-Host "  $($f.Name)" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "  Pressione qualquer tecla para fechar..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
