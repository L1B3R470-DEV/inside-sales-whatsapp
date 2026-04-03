$RepoDir    = "C:\Users\murdo\inside-sales-whatsapp"
$CoordDir   = "$RepoDir\coordination"
$InboxCl    = "$CoordDir\inbox_claude"
$InboxCo    = "$CoordDir\inbox_codex_local"
$OutboxCl   = "$CoordDir\outbox_claude"
$OutboxCo   = "$CoordDir\outbox_codex_local"
$PollerLog  = "$RepoDir\poller-remoto.log"
$ProcessedF = "$RepoDir\processed_replies.txt"

$host.UI.RawUI.WindowTitle = "Monitor Remoto OPENLAW (murdo)"
$lastBeepState = $false

function Write-Log($line) {
    if     ($line -match "complete|sucesso|RELAY|aceito")       { Write-Host "  $line" -ForegroundColor Green }
    elseif ($line -match "ERRO|erro|fail|FAIL|BLOCKED")         { Write-Host "  $line" -ForegroundColor Red }
    elseif ($line -match "detectado|iniciado|pull|push|commit") { Write-Host "  $line" -ForegroundColor Yellow }
    else                                                         { Write-Host "  $line" -ForegroundColor Gray }
}

try {
    while ($true) {
        Clear-Host

        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host "  MONITOR REMOTO (murdo) - OPENLAW AUTONOMOUS MODE" -ForegroundColor Cyan
        Write-Host ("  " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "   [Ctrl+C para sair]") -ForegroundColor Gray
        Write-Host "============================================================" -ForegroundColor Cyan

        # STATUS COORDINATION
        Write-Host ""
        Write-Host "  [COORDINATION workspace-integration]" -ForegroundColor White
        $inCl  = (Get-ChildItem $InboxCl  -Filter *.json -EA SilentlyContinue).Count
        $inCo  = (Get-ChildItem $InboxCo  -Filter *.json -EA SilentlyContinue).Count
        $outCl = (Get-ChildItem $OutboxCl -Filter *.json -EA SilentlyContinue).Count
        $outCo = (Get-ChildItem $OutboxCo -Filter *.json -EA SilentlyContinue).Count
        $proc  = if (Test-Path $ProcessedF) {
            (Get-Content $ProcessedF -EA SilentlyContinue | Where-Object { $_.Trim() -ne "" }).Count
        } else { 0 }
        Write-Host ("  inbox_claude={0}  inbox_codex={1}  outbox_claude={2}  outbox_codex={3}  processados={4}" -f $inCl, $inCo, $outCl, $outCo, $proc) -ForegroundColor Cyan

        # TASKS PENDENTES
        Write-Host ""
        Write-Host "  [TASKS AGUARDANDO CLAUDE LOCAL]" -ForegroundColor White
        $pendentes = Get-ChildItem $InboxCl -Filter *.json -EA SilentlyContinue | Where-Object {
            try {
                $j = Get-Content $_.FullName -Raw | ConvertFrom-Json
                ($j.status -eq "pending") -or ($j.status -eq "accepted")
            } catch { $false }
        }
        if ($pendentes) {
            foreach ($f in $pendentes) {
                try {
                    $j = Get-Content $f.FullName -Raw | ConvertFrom-Json
                    Write-Host ("  >> {0} | ciclo={1} | {2}" -f $j.task_id, $j.cycle, $j.status) -ForegroundColor Yellow
                } catch {}
            }
        } else {
            Write-Host "  (nenhuma pendente)" -ForegroundColor DarkGray
        }

        # REPLIES RECENTES
        Write-Host ""
        Write-Host "  [REPLIES RECENTES DE CLAUDE LOCAL]" -ForegroundColor White
        $replies = Get-ChildItem $OutboxCl -Filter *.json -EA SilentlyContinue |
                   Sort-Object LastWriteTime -Descending |
                   Select-Object -First 5
        if ($replies) {
            foreach ($f in $replies) {
                try {
                    $j = Get-Content $f.FullName -Raw | ConvertFrom-Json
                    $st = $j.status
                    if     ($st -eq "complete")        { $color = "Green" }
                    elseif ($st -eq "processed")       { $color = "DarkGray" }
                    elseif ($st -eq "processed_error") { $color = "Red" }
                    else                               { $color = "Gray" }
                    Write-Host ("  {0} | ciclo={1} | {2}" -f $j.reply_id, $j.cycle, $st) -ForegroundColor $color
                } catch {
                    Write-Host ("  " + $f.Name) -ForegroundColor DarkGray
                }
            }
        } else {
            Write-Host "  (nenhum reply ainda)" -ForegroundColor DarkGray
        }

        # LOG POLLER
        Write-Host ""
        Write-Host "  [poller-remoto.log]" -ForegroundColor DarkGray
        if (Test-Path $PollerLog) {
            Get-Content $PollerLog -Tail 10 -EA SilentlyContinue | ForEach-Object { Write-Log $_ }
        } else {
            Write-Host "  (poller nao iniciado)" -ForegroundColor DarkGray
        }

        # BEEP ao receber reply completo novo
        $hasComplete = $false
        if ($replies) {
            foreach ($f in $replies) {
                try {
                    $j = Get-Content $f.FullName -Raw | ConvertFrom-Json
                    if ($j.status -eq "complete") { $hasComplete = $true }
                } catch {}
            }
        }
        if ($hasComplete -and -not $lastBeepState) {
            [Console]::Beep(1000, 300)
            Start-Sleep -Milliseconds 150
            [Console]::Beep(1200, 300)
        }
        $lastBeepState = $hasComplete

        Write-Host ""
        Write-Host "============================================================" -ForegroundColor DarkGray

        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host ""
    Write-Host "ERRO FATAL: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
}
