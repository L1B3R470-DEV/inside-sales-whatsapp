$LogFile    = "C:\AUTOMACAO\cowork\claude_bridge\autopilot.log"
$WorkerFile = "C:\AUTOMACAO\cowork\claude_bridge\worker_state.json"
$InboxDir   = "C:\AUTOMACAO\cowork\claude_bridge\inbox_for_claude"
$OutboxDir  = "C:\AUTOMACAO\cowork\claude_bridge\outbox_from_claude"
$AcksDir    = "C:\AUTOMACAO\cowork\claude_bridge\ack_from_codex"

$host.UI.RawUI.WindowTitle = "Monitor de Ciclos — OPENLAW"
Clear-Host

function Show-Status {
    $inbox  = (Get-ChildItem $InboxDir  -Filter *.json -EA SilentlyContinue).Count
    $outbox = (Get-ChildItem $OutboxDir -Filter *.json -EA SilentlyContinue).Count
    $acks   = (Get-ChildItem $AcksDir   -Filter *.json -EA SilentlyContinue).Count

    $worker = Get-Content $WorkerFile -Raw -EA SilentlyContinue | ConvertFrom-Json
    $done   = if ($worker.processed_tasks) { $worker.processed_tasks.Count } else { 0 }
    $pct    = if ($inbox -gt 0) { [int](($done / ($done + $inbox - $acks)) * 100) } else { 100 }

    Write-Host "`r[$(Get-Date -f 'HH:mm:ss')]  inbox=$inbox  replies=$outbox  acks=$acks  processadas=$done  " -NoNewline -ForegroundColor Cyan
    if ($inbox -eq $acks) {
        Write-Host "[FASE CONCLUIDA]" -ForegroundColor Green
    } else {
        Write-Host "[em andamento]  " -ForegroundColor Yellow
    }
}

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "  MONITOR DE CICLOS — OPENLAW AUTONOMOUS MODE" -ForegroundColor Cyan
Write-Host "  Ctrl+C para sair" -ForegroundColor Gray
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""

# Mostra ultimas 15 linhas do log existente
Write-Host "-- LOG RECENTE --" -ForegroundColor DarkGray
Get-Content $LogFile -Tail 15 -EA SilentlyContinue | ForEach-Object {
    if ($_ -match "FASE|concluida|completed")  { Write-Host "  $_" -ForegroundColor Green }
    elseif ($_ -match "erro|ERRO|fail|FAIL")   { Write-Host "  $_" -ForegroundColor Red }
    elseif ($_ -match "ACK|Subtarefa|iniciado"){ Write-Host "  $_" -ForegroundColor Yellow }
    else                                        { Write-Host "  $_" -ForegroundColor Gray }
}
Write-Host ""
Write-Host "-- AO VIVO (novas entradas) --" -ForegroundColor DarkGray

# Tail ao vivo do log
$lastSize = (Get-Item $LogFile -EA SilentlyContinue).Length
Show-Status

while ($true) {
    Start-Sleep -Seconds 2

    $current = Get-Item $LogFile -EA SilentlyContinue
    if ($current -and $current.Length -ne $lastSize) {
        $newLines = Get-Content $LogFile -Tail 20 -EA SilentlyContinue
        $linhas = $newLines | Select-Object -Last ([int](($current.Length - $lastSize) / 50 + 1))
        foreach ($linha in $linhas) {
            Write-Host ""
            if ($linha -match "FASE|concluida|completed")  { Write-Host "  $linha" -ForegroundColor Green }
            elseif ($linha -match "erro|ERRO|fail|FAIL")   { Write-Host "  $linha" -ForegroundColor Red }
            elseif ($linha -match "ACK|Subtarefa|iniciado"){ Write-Host "  $linha" -ForegroundColor Yellow }
            else                                            { Write-Host "  $linha" -ForegroundColor Gray }
        }
        $lastSize = $current.Length

        # Alerta sonoro quando fase conclui
        $acks  = (Get-ChildItem $AcksDir  -Filter *.json -EA SilentlyContinue).Count
        $inbox = (Get-ChildItem $InboxDir -Filter *.json -EA SilentlyContinue).Count
        if ($inbox -eq $acks) {
            [Console]::Beep(1000, 400)
            Write-Host ""
            Write-Host "  *** FASE CONCLUIDA — todas as tarefas respondidas e ACKadas ***" -ForegroundColor Green
        }
    }

    Show-Status
}
