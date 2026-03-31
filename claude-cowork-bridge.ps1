param(
  [string]$BridgeRoot = "C:\AUTOMACAO\cowork\claude_bridge"
)

$ErrorActionPreference = "Stop"

$InboxDir = Join-Path $BridgeRoot "inbox_for_claude"
$OutboxDir = Join-Path $BridgeRoot "outbox_from_claude"
$AckDir = Join-Path $BridgeRoot "ack_from_codex"
$StateFile = Join-Path $BridgeRoot "bridge_state.json"

function Ensure-Bridge {
  foreach ($d in @($BridgeRoot, $InboxDir, $OutboxDir, $AckDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
  }
  if (-not (Test-Path $StateFile)) {
    $state = @{
      created_at = (Get-Date).ToString("o")
      last_sent_task_id = ""
      last_seen_reply_id = ""
    } | ConvertTo-Json -Depth 5
    Set-Content -Path $StateFile -Value $state -Encoding UTF8
  }
}

function Read-State {
  if (-not (Test-Path $StateFile)) { Ensure-Bridge }
  return (Get-Content $StateFile -Raw | ConvertFrom-Json)
}

function Save-State($obj) {
  ($obj | ConvertTo-Json -Depth 6) | Set-Content -Path $StateFile -Encoding UTF8
}

function New-TaskId {
  return "TASK-" + (Get-Date -Format "yyyyMMdd-HHmmss")
}

function Send-TaskToClaude {
  $taskId = New-TaskId
  $title = Read-Host "Titulo curto da tarefa"
  if (-not $title) { Write-Host "Titulo obrigatorio."; return }

  Write-Host "Descreva a tarefa. Finalize com uma linha contendo apenas: FIM"
  $lines = @()
  while ($true) {
    $line = Read-Host
    if ($line -eq "FIM") { break }
    $lines += $line
  }
  $body = ($lines -join "`n").Trim()
  if (-not $body) { Write-Host "Descricao obrigatoria."; return }

  $refs = Read-Host "Arquivos de referencia (opcional, separados por ; )"
  $refList = @()
  if ($refs) {
    $refList = $refs.Split(";") | ForEach-Object { $_.Trim() } | Where-Object { $_ }
  }

  $payload = @{
    task_id = $taskId
    created_at = (Get-Date).ToString("o")
    from = "codex"
    to = "claude"
    title = $title
    body = $body
    references = $refList
    required_output = "Resposta em JSON com: status, resumo, mudancas, riscos, proximos_passos."
  }

  $target = Join-Path $InboxDir ("{0}.json" -f $taskId)
  ($payload | ConvertTo-Json -Depth 8) | Set-Content -Path $target -Encoding UTF8

  $state = Read-State
  $state.last_sent_task_id = $taskId
  Save-State $state

  Write-Host ""
  Write-Host "Tarefa enviada ao Claude:"
  Write-Host "  $target"
}

function List-ClaudeReplies {
  $files = Get-ChildItem -Path $OutboxDir -Filter *.json -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
  if (-not $files) {
    Write-Host "Sem respostas do Claude no momento."
    return
  }

  Write-Host "Ultimas respostas do Claude:"
  $i = 1
  foreach ($f in $files | Select-Object -First 10) {
    Write-Host ("[{0}] {1}  ({2})" -f $i, $f.Name, $f.LastWriteTime)
    $i++
  }

  $pick = Read-Host "Digite o numero para abrir (Enter para voltar)"
  if (-not $pick) { return }
  if (-not ($pick -as [int])) { Write-Host "Opcao invalida."; return }
  $idx = [int]$pick
  if ($idx -lt 1 -or $idx -gt [Math]::Min(10, $files.Count)) { Write-Host "Opcao invalida."; return }
  $file = ($files | Select-Object -First 10)[$idx - 1]
  Write-Host ""
  Get-Content $file.FullName -Raw
  Write-Host ""
}

function Ack-ClaudeReply {
  $replyId = Read-Host "Informe o reply_id (sem .json)"
  if (-not $replyId) { Write-Host "reply_id obrigatorio."; return }
  $source = Join-Path $OutboxDir ("{0}.json" -f $replyId)
  if (-not (Test-Path $source)) { Write-Host "Resposta nao encontrada: $source"; return }

  $ack = @{
    reply_id = $replyId
    acked_at = (Get-Date).ToString("o")
    from = "codex"
    to = "claude"
    status = "received"
  }
  $target = Join-Path $AckDir ("ACK-{0}.json" -f $replyId)
  ($ack | ConvertTo-Json -Depth 6) | Set-Content -Path $target -Encoding UTF8

  $state = Read-State
  $state.last_seen_reply_id = $replyId
  Save-State $state
  Write-Host "ACK registrado em: $target"
}

function Show-Menu {
  Write-Host ""
  Write-Host "======================================"
  Write-Host " CLAUDE <-> CODEX COWORK BRIDGE"
  Write-Host "======================================"
  Write-Host "[1] Enviar tarefa para Claude"
  Write-Host "[2] Ver respostas do Claude"
  Write-Host "[3] Confirmar recebimento (ACK)"
  Write-Host "[4] Mostrar caminhos da ponte"
  Write-Host "[0] Sair"
}

Ensure-Bridge

while ($true) {
  Show-Menu
  $opt = Read-Host "Escolha"
  switch ($opt) {
    "1" { Send-TaskToClaude }
    "2" { List-ClaudeReplies }
    "3" { Ack-ClaudeReply }
    "4" {
      Write-Host "BridgeRoot: $BridgeRoot"
      Write-Host "Inbox:      $InboxDir"
      Write-Host "Outbox:     $OutboxDir"
      Write-Host "Ack:        $AckDir"
      Write-Host "State:      $StateFile"
    }
    "0" { break }
    default { Write-Host "Opcao invalida." }
  }
}

