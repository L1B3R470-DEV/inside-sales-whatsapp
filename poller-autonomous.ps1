# poller-autonomous.ps1
# Monitora o branch master por novos task files na coordination/.
# Aciona Claude Code (via CLI) e notifica CODEX LOCAL quando tasks chegam.
# Fazer push dos outputs de volta ao repositório automaticamente.
#
# Iniciar:  .\poller-autonomous.ps1
# Parar:    Ctrl+C ou fechar a janela
# Instalar como tarefa agendada: .\install-autonomous-task.ps1

param(
    [int]$PollIntervalSeconds = 60
)

$WorkDir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$CoordDir     = Join-Path $WorkDir "coordination"
$InboxClaude  = Join-Path $CoordDir "inbox_claude"
$InboxCodex   = Join-Path $CoordDir "inbox_codex_local"
$OutboxClaude = Join-Path $CoordDir "outbox_claude"
$LogFile      = Join-Path $WorkDir "poller-autonomous.log"
$ProcessedFile= Join-Path $WorkDir "processed_tasks.txt"

# Diretório do projeto real — onde claude CLI carrega CLAUDE.md
$ProjectDir   = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"

function Write-Log {
    param([string]$Msg, [string]$Level = "INFO")
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [$Level] $Msg"
    Write-Host $line -ForegroundColor $(if ($Level -eq "ERROR") { "Red" } elseif ($Level -eq "WARN") { "Yellow" } else { "Cyan" })
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
}

function Is-Processed {
    param([string]$TaskId)
    if (Test-Path $ProcessedFile) {
        return ((Get-Content $ProcessedFile -ErrorAction SilentlyContinue) -contains $TaskId)
    }
    return $false
}

function Mark-Processed {
    param([string]$TaskId)
    Add-Content -Path $ProcessedFile -Value $TaskId
}

function Git-Pull {
    $result = git -C $WorkDir pull origin master 2>&1
    return $LASTEXITCODE -eq 0
}

function Git-CommitPush {
    param([string]$Message, [string[]]$Files)
    foreach ($f in $Files) {
        git -C $WorkDir add $f 2>&1 | Out-Null
    }
    $staged = git -C $WorkDir diff --cached --name-only
    if ($staged) {
        git -C $WorkDir commit -m $Message 2>&1 | Out-Null
        git -C $WorkDir push origin master 2>&1 | Out-Null
        return $true
    }
    return $false
}

function Update-TaskStatus {
    param([string]$FilePath, [string]$NewStatus)
    $data = Get-Content $FilePath -Raw | ConvertFrom-Json
    $data.status = $NewStatus
    $data | ConvertTo-Json -Depth 20 | Set-Content $FilePath -Encoding UTF8
    return $data
}

function Process-ClaudeTask {
    param([string]$TaskFilePath)

    $data = Get-Content $TaskFilePath -Raw | ConvertFrom-Json
    $taskId = $data.task_id
    $cycle  = $data.cycle

    if (Is-Processed $taskId) { return }
    if ($data.status -ne "pending") { return }

    Write-Log "Claude task detectada: $taskId (ciclo $cycle)"

    # Marcar como accepted antes de processar
    $data = Update-TaskStatus $TaskFilePath "accepted"
    Git-CommitPush "accepted: $taskId" @($TaskFilePath)

    # Montar instrução — instrução já vem completa no campo instruction
    $instruction = $data.instruction

    # Adicionar contexto obrigatório de red_lines ao prompt
    $fullPrompt = @"
[OPENLAW AUTONOMOUS MODE — CICLO $cycle]

RED LINES (invioláveis):
- Não escrever fora de C:\Users\User\.openclaw\workspace-integration\
- Não tocar em produção (Evolution API, n8n, bridge local)
- Não tocar em .mcp.json do projeto real
- Não reabrir R2 nem R6

INSTRUÇÃO:
$instruction

OUTPUT: Escreva seu relatório como texto estruturado. O poller capturará o stdout.
"@

    Write-Log "Invocando claude CLI para $taskId..."

    # Invocar Claude Code em modo não-interativo a partir do diretório do projeto
    $outputRaw = ""
    try {
        Push-Location $ProjectDir
        $outputRaw = & claude -p $fullPrompt 2>&1 | Out-String
        Pop-Location
    } catch {
        Pop-Location
        Write-Log "Erro ao invocar claude CLI: $_" "ERROR"
        $outputRaw = "ERRO: $_"
    }

    # Determinar status do output
    $outputStatus = "complete"
    if ($outputRaw -match "BLOCKED|ERRO|ERROR") {
        $outputStatus = "BLOCKED"
        Write-Log "Output retornou BLOCKED para $taskId" "WARN"
    }

    # Escrever reply file
    $replyId   = "reply-$cycle-$(Get-Date -Format 'yyyyMMddTHHmmssZ')"
    $replyPath = Join-Path $OutboxClaude "$replyId.json"

    $reply = [ordered]@{
        reply_id       = $replyId
        source_task_id = $taskId
        actor          = "claude_local"
        cycle          = $cycle
        output         = $outputRaw.Trim()
        status         = $outputStatus
        produced_at    = (Get-Date -Format 'o')
    }
    $reply | ConvertTo-Json -Depth 20 | Set-Content $replyPath -Encoding UTF8

    # Push reply
    Git-CommitPush "claude-local: output $cycle" @($replyPath)

    Mark-Processed $taskId
    Write-Log "Claude output commitado: $replyId (status: $outputStatus)"
}

function Process-CodexLocalTask {
    param([string]$TaskFilePath)

    $data = Get-Content $TaskFilePath -Raw | ConvertFrom-Json
    $taskId = $data.task_id
    $cycle  = $data.cycle

    if (Is-Processed $taskId) { return }
    if ($data.status -ne "pending") { return }

    Write-Log "CODEX LOCAL task detectada: $taskId (ciclo $cycle)"

    # Marcar como accepted
    $data = Update-TaskStatus $TaskFilePath "accepted"
    Git-CommitPush "accepted: $taskId" @($TaskFilePath)

    # Invocar Claude Code em modo não-interativo (mesmo mecanismo do inbox_claude)
    $outboxCodex = Join-Path $CoordDir "outbox_codex_local"
    $fullPrompt = @"
[OPENLAW AUTONOMOUS MODE — CODEX LOCAL — CICLO $cycle]

RED LINES (invioláveis):
- Não escrever fora de C:\Users\User\.openclaw\workspace-integration\
- Não tocar em produção (Evolution API, n8n, bridge local)
- Não tocar em .mcp.json do projeto real
- Não reabrir R2 nem R6

INSTRUÇÃO:
$($data.instruction)

OUTPUT: Escreva seu relatório como texto estruturado. O poller capturará o stdout.
"@

    Write-Log "Invocando claude CLI para CODEX LOCAL $taskId..."

    $outputRaw = ""
    try {
        Push-Location $ProjectDir
        $outputRaw = & claude -p $fullPrompt 2>&1 | Out-String
        Pop-Location
    } catch {
        Pop-Location
        Write-Log "Erro ao invocar claude CLI (codex-local): $_" "ERROR"
        $outputRaw = "ERRO: $_"
    }

    $outputStatus = "complete"
    if ($outputRaw -match "BLOCKED|ERRO|ERROR") {
        $outputStatus = "BLOCKED"
        Write-Log "Output retornou BLOCKED para $taskId" "WARN"
    }

    $replyId   = "reply-$cycle-$(Get-Date -Format 'yyyyMMddTHHmmssZ')"
    $replyPath = Join-Path $outboxCodex "$replyId.json"

    $reply = [ordered]@{
        reply_id       = $replyId
        source_task_id = $taskId
        actor          = "codex_local"
        cycle          = $cycle
        output         = $outputRaw.Trim()
        status         = $outputStatus
        produced_at    = (Get-Date -Format 'o')
    }
    $reply | ConvertTo-Json -Depth 20 | Set-Content $replyPath -Encoding UTF8

    Git-CommitPush "codex-local: output $cycle" @($replyPath)

    Mark-Processed $taskId
    Write-Log "Codex-local output commitado: $replyId (status: $outputStatus)"
}

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────

Write-Log "=== poller-autonomous iniciado (intervalo: ${PollIntervalSeconds}s) ==="
Write-Log "WorkDir:     $WorkDir"
Write-Log "Inbox Claude:      $InboxClaude"
Write-Log "Inbox Codex Local: $InboxCodex"

try {
    while ($true) {
        # Pull do repositório remoto
        $pulled = Git-Pull
        if (-not $pulled) {
            Write-Log "git pull falhou — tentando novamente no proximo ciclo" "WARN"
        }

        # Processar tasks do Claude
        $claudeTasks = Get-ChildItem "$InboxClaude\*.json" -ErrorAction SilentlyContinue
        foreach ($taskFile in $claudeTasks) {
            try {
                Process-ClaudeTask $taskFile.FullName
            } catch {
                Write-Log "Erro ao processar Claude task $($taskFile.Name): $_" "ERROR"
            }
        }

        # Processar tasks do CODEX LOCAL
        $codexTasks = Get-ChildItem "$InboxCodex\*.json" -ErrorAction SilentlyContinue
        foreach ($taskFile in $codexTasks) {
            try {
                Process-CodexLocalTask $taskFile.FullName
            } catch {
                Write-Log "Erro ao processar Codex task $($taskFile.Name): $_" "ERROR"
            }
        }

        Start-Sleep -Seconds $PollIntervalSeconds
    }
} finally {
    Write-Log "=== poller-autonomous encerrado ==="
}
