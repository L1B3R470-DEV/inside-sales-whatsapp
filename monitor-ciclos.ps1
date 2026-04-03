$BridgeLog  = "C:\AUTOMACAO\cowork\claude_bridge\autopilot.log"
$RelayLog   = "C:\Users\User\.openclaw\workspace-integration\relay-local.log"
$WorkerFile = "C:\AUTOMACAO\cowork\claude_bridge\worker_state.json"
$InboxDir   = "C:\AUTOMACAO\cowork\claude_bridge\inbox_for_claude"
$OutboxDir  = "C:\AUTOMACAO\cowork\claude_bridge\outbox_from_claude"
$AcksDir    = "C:\AUTOMACAO\cowork\claude_bridge\ack_from_codex"
$WsInbox    = "C:\Users\User\.openclaw\workspace-integration\coordination\inbox_claude"
$WsOutbox   = "C:\Users\User\.openclaw\workspace-integration\coordination\outbox_claude"

$host.UI.RawUI.WindowTitle = "Monitor de Ciclos — OPENLAW"
$lastBeepState = $false

function Write-Log($line) {
    if     ($line -match "CONCLUIDA|CONFIRMADO|complete|sucesso") { Write-Host "  $line" -ForegroundColor Green }
    elseif ($line -match "ERRO|erro|fail|FAIL|BLOCKED|offline")  { Write-Host "  $line" -ForegroundColor Red }
    elseif ($line -match "ACK|Subtarefa|iniciado|detectado|aceito|Processando") { Write-Host "  $line" -ForegroundColor Yellow }
    elseif ($line -match "RELAY|relay|push|pull|commit")         { Write-Host "  $line" -ForegroundColor Cyan }
    else                                                          { Write-Host "  $line" -ForegroundColor Gray }
}

while ($true) {
    Clear-Host

    # ── CABEÇALHO ──────────────────────────────────────────────────
    Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  MONITOR DE CICLOS — OPENLAW AUTONOMOUS MODE" -ForegroundColor Cyan
    Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')   [Ctrl+C para sair]" -ForegroundColor Gray
    Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Cyan

    # ── STATUS BRIDGE (OPENLAW) ─────────────────────────────────────
    Write-Host ""
    Write-Host "  [BRIDGE OPENLAW]" -ForegroundColor White
    $inbox  = (Get-ChildItem $InboxDir  -Filter *.json -EA SilentlyContinue).Count
    $outbox = (Get-ChildItem $OutboxDir -Filter *.json -EA SilentlyContinue).Count
    $acks   = (Get-ChildItem $AcksDir   -Filter *.json -EA SilentlyContinue).Count
    $worker = Get-Content $WorkerFile -Raw -EA SilentlyContinue | ConvertFrom-Json
    $done   = if ($worker.processed_tasks) { $worker.processed_tasks.Count } else { 0 }
    $faseColor = if ($inbox -eq $acks) { "Green" } else { "Yellow" }
    $faseLabel = if ($inbox -eq $acks) { "FASE CONCLUIDA" } else { "em andamento" }
    Write-Host ("  inbox={0}  replies={1}  acks={2}  processadas={3}  [{4}]" -f $inbox, $outbox, $acks, $done, $faseLabel) -ForegroundColor $faseColor

    # ── STATUS WORKSPACE-INTEGRATION ───────────────────────────────
    Write-Host ""
    Write-Host "  [WORKSPACE-INTEGRATION / OpenClaw]" -ForegroundColor White
    $wsIn  = (Get-ChildItem $WsInbox  -Filter *.json -EA SilentlyContinue).Count
    $wsOut = (Get-ChildItem $WsOutbox -Filter *.json -EA SilentlyContinue).Count
    $ptFile = "C:\Users\User\.openclaw\workspace-integration\processed_tasks_local.txt"
    $ptDone = if (Test-Path $ptFile) { (Get-Content $ptFile -EA SilentlyContinue | Where-Object { $_ -ne "" }).Count } else { 0 }
    Write-Host ("  inbox_claude={0}  outbox_claude={1}  processadas_local={2}" -f $wsIn, $wsOut, $ptDone) -ForegroundColor Cyan

    # ── LOG AUTOPILOT (BRIDGE) ──────────────────────────────────────
    Write-Host ""
    Write-Host "  [autopilot.log — últimas 8 linhas]" -ForegroundColor DarkGray
    if (Test-Path $BridgeLog) {
        Get-Content $BridgeLog -Tail 8 -EA SilentlyContinue | ForEach-Object { Write-Log $_ }
    } else {
        Write-Host "  (arquivo não encontrado)" -ForegroundColor DarkGray
    }

    # ── LOG RELAY-LOCAL ─────────────────────────────────────────────
    Write-Host ""
    Write-Host "  [relay-local.log — últimas 8 linhas]" -ForegroundColor DarkGray
    if (Test-Path $RelayLog) {
        Get-Content $RelayLog -Tail 8 -EA SilentlyContinue | ForEach-Object { Write-Log $_ }
    } else {
        Write-Host "  (relay-local não iniciado)" -ForegroundColor DarkGray
    }

    # ── TASKS PENDENTES WORKSPACE-INTEGRATION ───────────────────────
    $pendentes = Get-ChildItem $WsInbox -Filter *.json -EA SilentlyContinue |
                 Where-Object {
                     try {
                         $j = Get-Content $_.FullName -Raw | ConvertFrom-Json
                         $j.status -in @("pending","accepted") -and
                         (-not (Get-Content $ptFile -EA SilentlyContinue | Where-Object { $_ -eq $j.task_id }))
                     } catch { $false }
                 }
    if ($pendentes) {
        Write-Host ""
        Write-Host "  [TASKS PENDENTES PARA CLAUDE LOCAL]" -ForegroundColor Red
        foreach ($f in $pendentes) {
            try {
                $j = Get-Content $f.FullName -Raw | ConvertFrom-Json
                Write-Host ("  >> {0} | ciclo={1} | {2}" -f $j.task_id, $j.cycle, $j.status) -ForegroundColor Red
            } catch {}
        }
    }

    # ── BEEP quando nova fase conclui ───────────────────────────────
    $faseOK = ($inbox -eq $acks -and $inbox -gt 0)
    if ($faseOK -and -not $lastBeepState) {
        [Console]::Beep(1000, 300); Start-Sleep -Milliseconds 100; [Console]::Beep(1200, 300)
    }
    $lastBeepState = $faseOK

    Write-Host ""
    Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor DarkGray

    Start-Sleep -Seconds 2
}
