$ErrorActionPreference = "SilentlyContinue"

$RepoDir    = $PSScriptRoot
$CoordDir   = Join-Path $RepoDir "coordination"
$InboxCl    = Join-Path $CoordDir "inbox_claude"
$InboxCo    = Join-Path $CoordDir "inbox_codex_local"
$OutboxCl   = Join-Path $CoordDir "outbox_claude"
$OutboxCo   = Join-Path $CoordDir "outbox_codex_local"
$StateFile  = Join-Path $RepoDir "STATE.md"
$RemoteLog  = Join-Path $RepoDir "poller-remoto.log"
$LocalLog   = Join-Path $RepoDir "poller-autonomous.log"
$RelayLog   = Join-Path $RepoDir "relay-local.log"
$BridgeDir  = "C:\AUTOMACAO\cowork\claude_bridge"
$BridgeInbox = Join-Path $BridgeDir "inbox_for_claude"
$BridgeReplies = Join-Path $BridgeDir "replies_for_openlaw"
$BridgeAck = Join-Path $BridgeDir "ack"
$BridgeProcessed = Join-Path $BridgeDir "processadas"

$host.UI.RawUI.WindowTitle = "Monitor OpenClaw"

function Count-JsonFiles($Path) {
    if (Test-Path $Path) {
        return (Get-ChildItem $Path -Filter *.json -File).Count
    }
    return 0
}

function Get-JsonObjects($Path) {
    if (-not (Test-Path $Path)) { return @() }
    $items = @()
    foreach ($f in (Get-ChildItem $Path -Filter *.json -File | Sort-Object LastWriteTime -Descending)) {
        try {
            $j = Get-Content $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
            $j | Add-Member -NotePropertyName "__file" -NotePropertyValue $f.Name -Force
            $j | Add-Member -NotePropertyName "__time" -NotePropertyValue $f.LastWriteTime -Force
            $items += $j
        } catch {}
    }
    return $items
}

function Get-TaskSummary($Items) {
    $pending = @($Items | Where-Object { $_.status -eq "pending" }).Count
    $accepted = @($Items | Where-Object { $_.status -eq "accepted" }).Count
    return @{ pending = $pending; accepted = $accepted; total = @($Items).Count }
}

function Get-ReplySummary($Items) {
    $complete = @($Items | Where-Object { $_.status -eq "complete" }).Count
    $processed = @($Items | Where-Object { $_.status -eq "processed" }).Count
    $blocked = @($Items | Where-Object { $_.status -eq "BLOCKED" -or $_.status -eq "processed_error" -or $_.status -eq "processed_blocked" }).Count
    return @{ complete = $complete; processed = $processed; blocked = $blocked; total = @($Items).Count }
}

function Write-Section($Title) {
    Write-Host ""
    Write-Host ("  [{0}]" -f $Title) -ForegroundColor White
}

function Write-KeyValue($Label, $Value, $Color = "Cyan") {
    Write-Host ("  {0}: {1}" -f $Label, $Value) -ForegroundColor $Color
}

function Get-RecentEvents($Collections) {
    $events = @()
    foreach ($c in $Collections) {
        $events += $c
    }
    return $events | Sort-Object __time -Descending | Select-Object -First 10
}

function Show-LogStatus($Label, $Path) {
    if (Test-Path $Path) {
        $item = Get-Item $Path
        $ageMinutes = [math]::Round(((Get-Date) - $item.LastWriteTime).TotalMinutes, 1)
        $color = if ($ageMinutes -le 5) { "Green" } elseif ($ageMinutes -le 30) { "Yellow" } else { "DarkYellow" }
        Write-Host ("  {0}: atualizado ha {1} min ({2})" -f $Label, $ageMinutes, $item.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")) -ForegroundColor $color
    } else {
        Write-Host ("  {0}: ausente" -f $Label) -ForegroundColor DarkGray
    }
}

function Show-LegacyNote($Path) {
    if (Test-Path $Path) {
        $item = Get-Item $Path
        $ageHours = [math]::Round(((Get-Date) - $item.LastWriteTime).TotalHours, 1)
        if ($ageHours -gt 6) {
            Write-Host ("  observacao: {0} parece legado/parado ha {1}h; nao usar como sinal primario do fluxo atual." -f $item.Name, $ageHours) -ForegroundColor Yellow
        }
    }
}

try {
    while ($true) {
        Clear-Host

        $inboxClaudeItems = Get-JsonObjects $InboxCl
        $inboxCodexItems  = Get-JsonObjects $InboxCo
        $outboxClaudeItems = Get-JsonObjects $OutboxCl
        $outboxCodexItems  = Get-JsonObjects $OutboxCo

        $claudeTaskSummary = Get-TaskSummary $inboxClaudeItems
        $codexTaskSummary  = Get-TaskSummary $inboxCodexItems
        $claudeReplySummary = Get-ReplySummary $outboxClaudeItems
        $codexReplySummary  = Get-ReplySummary $outboxCodexItems

        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host "  MONITOR OPENCLAW FLOW" -ForegroundColor Cyan
        Write-Host ("  " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "   [Ctrl+C para sair]") -ForegroundColor Gray
        Write-Host "============================================================" -ForegroundColor Cyan

        Write-Section "ESTADO"
        if (Test-Path $StateFile) {
            $statePreview = Get-Content $StateFile -TotalCount 20
            $activeLine = ($statePreview | Where-Object { $_ -match "Ciclo ativo" } | Select-Object -First 1)
            $phaseLine = ($statePreview | Where-Object { $_ -match "Fase em andamento" } | Select-Object -First 1)
            $nextLine = ($statePreview | Where-Object { $_ -match "Próxima etapa|Proxima etapa" } | Select-Object -First 1)
            if ($activeLine) { Write-Host ("  " + $activeLine.Trim()) -ForegroundColor Cyan }
            if ($phaseLine) { Write-Host ("  " + $phaseLine.Trim()) -ForegroundColor Gray }
            if ($nextLine) { Write-Host ("  " + $nextLine.Trim()) -ForegroundColor Gray }
        } else {
            Write-Host "  STATE.md ausente" -ForegroundColor DarkGray
        }

        Write-Section "COORDINATION"
        Write-Host ("  CLAUDE  inbox total={0} pending={1} accepted={2} | outbox total={3} complete={4} processed={5} blocked/error={6}" -f `
            $claudeTaskSummary.total, $claudeTaskSummary.pending, $claudeTaskSummary.accepted, `
            $claudeReplySummary.total, $claudeReplySummary.complete, $claudeReplySummary.processed, $claudeReplySummary.blocked) -ForegroundColor Cyan
        Write-Host ("  CODEX   inbox total={0} pending={1} accepted={2} | outbox total={3} complete={4} processed={5} blocked/error={6}" -f `
            $codexTaskSummary.total, $codexTaskSummary.pending, $codexTaskSummary.accepted, `
            $codexReplySummary.total, $codexReplySummary.complete, $codexReplySummary.processed, $codexReplySummary.blocked) -ForegroundColor Cyan

        Write-Section "ULTIMOS EVENTOS"
        $recent = Get-RecentEvents @($inboxClaudeItems, $inboxCodexItems, $outboxClaudeItems, $outboxCodexItems)
        if ($recent) {
            foreach ($e in $recent) {
                $kind = if ($e.PSObject.Properties.Name -contains "source_task_id") { "reply" } else { "task" }
                $id = if ($kind -eq "reply") { $e.reply_id } else { $e.task_id }
                $actor = if ($e.actor) { $e.actor } else { $e.target_actor }
                $status = $e.status
                $color = switch ($status) {
                    "pending" { "Yellow" }
                    "accepted" { "DarkYellow" }
                    "complete" { "Green" }
                    "processed" { "DarkGray" }
                    "BLOCKED" { "Red" }
                    "processed_error" { "Red" }
                    default { "Gray" }
                }
                Write-Host ("  {0:HH:mm:ss} | {1} | {2} | ciclo={3} | actor={4} | {5}" -f $e.__time, $kind, $id, $e.cycle, $actor, $status) -ForegroundColor $color
            }
        } else {
            Write-Host "  (nenhum evento encontrado)" -ForegroundColor DarkGray
        }

        Write-Section "LOGS"
        Show-LogStatus "poller-remoto.log" $RemoteLog
        Show-LogStatus "poller-autonomous.log" $LocalLog
        Show-LogStatus "relay-local.log" $RelayLog
        if (Test-Path (Join-Path $BridgeDir "autopilot.log")) {
            Show-LogStatus "autopilot.log" (Join-Path $BridgeDir "autopilot.log")
            Show-LegacyNote (Join-Path $BridgeDir "autopilot.log")
        } else {
            Write-Host "  autopilot.log: ausente" -ForegroundColor DarkGray
        }

        Write-Section "BRIDGE"
        if (Test-Path $BridgeDir) {
            $bridgeInboxCount = Count-JsonFiles $BridgeInbox
            $bridgeRepliesCount = Count-JsonFiles $BridgeReplies
            $bridgeAckCount = Count-JsonFiles $BridgeAck
            $bridgeProcessedCount = Count-JsonFiles $BridgeProcessed
            Write-Host ("  inbox={0} replies={1} ack={2} processadas={3}" -f $bridgeInboxCount, $bridgeRepliesCount, $bridgeAckCount, $bridgeProcessedCount) -ForegroundColor Cyan
            if ($bridgeProcessedCount -ge $bridgeRepliesCount -and $bridgeRepliesCount -gt 0) {
                Write-Host "  status_bridge: estavel" -ForegroundColor Green
            }
        } else {
            Write-Host "  bridge indisponivel nesta maquina" -ForegroundColor DarkGray
        }

        Write-Section "ATENCAO"
        $latestCodexReply = $outboxCodexItems | Select-Object -First 1
        if ($latestCodexReply -and $latestCodexReply.cycle -eq "019SYNC" -and $latestCodexReply.output -match "inje|N.o reconhe") {
            Write-Host "  019SYNC ainda nao concluiu; o ultimo reply do CODEX LOCAL continua invalido para o fluxo." -ForegroundColor Yellow
        } else {
            Write-Host "  nenhuma anomalia nova detectada neste recorte." -ForegroundColor Green
        }

        Write-Host ""
        Write-Host "============================================================" -ForegroundColor DarkGray
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host ""
    Write-Host "ERRO FATAL: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
}
