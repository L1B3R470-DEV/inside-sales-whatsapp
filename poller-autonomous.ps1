# poller-autonomous.ps1
# Monitora o branch master por novos task files na coordination/.
# Aciona Claude Code (via CLI) para inbox_claude E inbox_codex_local.
# Push dos outputs de volta ao repositorio automaticamente.
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
$OutboxCodex  = Join-Path $CoordDir "outbox_codex_local"
$LogFile      = Join-Path $WorkDir "poller-autonomous.log"
$ProcessedFile= Join-Path $WorkDir "processed_tasks.txt"
$PromptFile   = Join-Path $WorkDir "temp_prompt.txt"
$CurrentTaskClaudeTxt = Join-Path $WorkDir "current_task_claude_local.txt"
$CurrentTaskClaudeJson = Join-Path $WorkDir "current_task_claude_local.json"
$CurrentTaskCodexTxt = Join-Path $WorkDir "current_task_codex_local.txt"
$CurrentTaskCodexJson = Join-Path $WorkDir "current_task_codex_local.json"

# Diretorio do projeto real onde claude CLI carrega CLAUDE.md
$ProjectDir = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"
$WorkspaceDir = $WorkDir

$BootstrapClaude = Join-Path $WorkDir "BOOTSTRAP_CLAUDE_v2.md"
$BootstrapCodex  = Join-Path $WorkDir "BOOTSTRAP_LOCAL_v2.md"

# Caminho completo do claude CLI (necessario para tarefa agendada sem PATH do usuario)
$ClaudeCLI = "C:\Users\User\AppData\Roaming\npm\claude.cmd"

function Write-Log {
    param([string]$Msg, [string]$Level = "INFO")
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [$Level] $Msg"
    $color = switch ($Level) { "ERROR" { "Red" } "WARN" { "Yellow" } default { "Cyan" } }
    Write-Host $line -ForegroundColor $color
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
    git -C $WorkDir pull origin master 2>&1 | Out-Null
    return $LASTEXITCODE -eq 0
}

function Git-CommitPush {
    param([string]$Message, [string[]]$Files)
    foreach ($f in $Files) { git -C $WorkDir add $f 2>&1 | Out-Null }
    $staged = git -C $WorkDir diff --cached --name-only 2>&1
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

function Invoke-ClaudeCLI {
    param(
        [string]$Prompt,
        [string]$Label,
        [string]$WorkingDir
    )
    $Prompt | Set-Content $PromptFile -Encoding UTF8
    Write-Log "Invocando claude CLI para $Label..."
    $output = ""
    try {
        Push-Location $WorkingDir
        $output = & $ClaudeCLI -p (Get-Content $PromptFile -Raw) 2>&1 | Out-String
        Pop-Location
    } catch {
        Pop-Location
        Write-Log "Erro ao invocar claude CLI: $_" "ERROR"
        $output = "ERRO: $_"
    }
    return $output
}

function Build-Prompt {
    param(
        [string]$Actor,
        [string]$Cycle,
        [string]$Instruction,
        [string[]]$ContextFiles
    )

    $isCodex = $Actor -eq "CODEX_LOCAL"

    if ($isCodex) {
        # Prompt para CODEX_LOCAL: instrucao direta, sem preamble de automacao ou atribuicao de papel
        $contextBlock = if ($ContextFiles -and $ContextFiles.Count -gt 0) {
            "Arquivos de referencia disponiveis (leia os necessarios):`n- " + ($ContextFiles -join "`n- ")
        } else {
            ""
        }
        $lines = @(
            $contextBlock,
            "",
            $Instruction
        )
        return ($lines | Where-Object { $_ -ne "" -and $_ -ne $null }) -join "`n"
    } else {
        # Prompt para CLAUDE_LOCAL (roda no projeto real com CLAUDE.md completo)
        $contextBlock = if ($ContextFiles -and $ContextFiles.Count -gt 0) {
            "Arquivos de contexto da task:`n- " + ($ContextFiles -join "`n- ")
        } else {
            "Arquivos de contexto: nenhum"
        }
        $lines = @(
            "Tarefa OpenClaw — ciclo $Cycle",
            "Consulte BOOTSTRAP_CLAUDE_v2.md em: $BootstrapClaude",
            $contextBlock,
            "",
            $Instruction
        )
        return $lines -join "`n"
    }
}

function Persist-CurrentTask {
    param(
        [pscustomobject]$TaskData,
        [string]$Actor
    )

    if ($Actor -eq "CODEX_LOCAL") {
        $txtPath = $CurrentTaskCodexTxt
        $jsonPath = $CurrentTaskCodexJson
    } else {
        $txtPath = $CurrentTaskClaudeTxt
        $jsonPath = $CurrentTaskClaudeJson
    }

    $TaskData.instruction | Set-Content $txtPath -Encoding UTF8
    $TaskData | ConvertTo-Json -Depth 20 | Set-Content $jsonPath -Encoding UTF8
}

function Process-Task {
    param(
        [string]$TaskFilePath,
        [string]$Actor,
        [string]$OutboxDir
    )

    $data   = Get-Content $TaskFilePath -Raw | ConvertFrom-Json
    $taskId = $data.task_id
    $cycle  = $data.cycle

    if (Is-Processed $taskId) { return }
    if ($data.status -ne "pending") { return }

    Write-Log "$Actor task detectada: $taskId (ciclo $cycle)"

    $data = Update-TaskStatus $TaskFilePath "accepted"
    Git-CommitPush "accepted: $taskId" @($TaskFilePath)

    Persist-CurrentTask -TaskData $data -Actor $Actor

    $workingDir = if ($Actor -eq "CODEX_LOCAL") { $WorkspaceDir } else { $ProjectDir }
    $prompt    = Build-Prompt -Actor $Actor -Cycle $cycle -Instruction $data.instruction -ContextFiles $data.context_files
    $outputRaw = Invoke-ClaudeCLI -Prompt $prompt -Label $taskId -WorkingDir $workingDir

    $outputStatus = "complete"
    if ($outputRaw -match "BLOCKED") {
        $outputStatus = "BLOCKED"
        Write-Log "Output retornou BLOCKED para $taskId" "WARN"
    } elseif ($outputRaw -match "^ERRO") {
        $outputStatus = "BLOCKED"
        Write-Log "Erro CLI para $taskId" "ERROR"
    }

    $replyId   = "reply-$cycle-$(Get-Date -Format 'yyyyMMddTHHmmssZ')"
    $replyPath = Join-Path $OutboxDir "$replyId.json"

    $reply = [ordered]@{
        reply_id       = $replyId
        source_task_id = $taskId
        actor          = $Actor.ToLower() -replace " ", "_"
        cycle          = $cycle
        output         = $outputRaw.Trim()
        status         = $outputStatus
        produced_at    = (Get-Date -Format "o")
    }
    $reply | ConvertTo-Json -Depth 20 | Set-Content $replyPath -Encoding UTF8

    Git-CommitPush "$($Actor.ToLower()): output $cycle" @($replyPath)
    Mark-Processed $taskId
    Write-Log "Output commitado: $replyId (status: $outputStatus)"
}

# --- MAIN LOOP ---

Write-Log "=== poller-autonomous iniciado (intervalo: ${PollIntervalSeconds}s) ==="
Write-Log "WorkDir: $WorkDir"

try {
    while ($true) {
        $pulled = Git-Pull
        if (-not $pulled) {
            Write-Log "git pull falhou -- tentando novamente no proximo ciclo" "WARN"
        }

        $claudeTasks = Get-ChildItem "$InboxClaude\*.json" -ErrorAction SilentlyContinue
        foreach ($f in $claudeTasks) {
            try { Process-Task -TaskFilePath $f.FullName -Actor "CLAUDE_LOCAL" -OutboxDir $OutboxClaude }
            catch { Write-Log "Erro em $($f.Name): $_" "ERROR" }
        }

        $codexTasks = Get-ChildItem "$InboxCodex\*.json" -ErrorAction SilentlyContinue
        foreach ($f in $codexTasks) {
            try { Process-Task -TaskFilePath $f.FullName -Actor "CODEX_LOCAL" -OutboxDir $OutboxCodex }
            catch { Write-Log "Erro em $($f.Name): $_" "ERROR" }
        }

        Start-Sleep -Seconds $PollIntervalSeconds
    }
} finally {
    Write-Log "=== poller-autonomous encerrado ==="
}
