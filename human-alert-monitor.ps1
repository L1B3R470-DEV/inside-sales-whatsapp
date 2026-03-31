param(
  [string]$ProjectDir = 'C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES',
  [string]$WorkflowId = 'zN3heKJVLO8w4dG6',
  [string]$InsideSalesNumber = '557583211367'
)

$ErrorActionPreference = 'Stop'
$envFile = Join-Path $ProjectDir '.env'
if (-not (Test-Path $envFile)) { throw ".env nao encontrado em $ProjectDir" }

$envMap = @{}
Get-Content $envFile | ForEach-Object {
  if ($_ -match '^\s*#') { return }
  if ($_ -match '^\s*([^=]+)=(.*)$') {
    $envMap[$matches[1].Trim()] = $matches[2].Trim()
  }
}

$evolutionBaseUrl = ($envMap['EVOLUTION_BASE_URL'] | ForEach-Object { if ($_){$_} else {'http://localhost:8080'} })
$evolutionApiKey = $envMap['EVOLUTION_API_KEY']
$evolutionInstance = $envMap['EVOLUTION_INSTANCE']
if ($envMap.ContainsKey('INSIDE_SALES_ALERT_NUMBER') -and $envMap['INSIDE_SALES_ALERT_NUMBER']) {
  $InsideSalesNumber = ($envMap['INSIDE_SALES_ALERT_NUMBER'] -replace '\D','')
}

$pendingJson = docker run --rm -v ai_n8n_data:/data python:3.11-alpine python -c @"
import json, sqlite3
workflow_id = '$WorkflowId'
conn = sqlite3.connect('/data/database.sqlite')
cur = conn.cursor()
row = cur.execute('SELECT staticData FROM workflow_entity WHERE id = ?', (workflow_id,)).fetchone()
obj = json.loads(row[0] or '{}') if row else {}
global_data = obj.get('global') or {}
queue = global_data.get('humanQueue') or []
pending = [q for q in queue if q.get('status') != 'closed' and not q.get('alertedAt')]
pending.sort(key=lambda q: q.get('priorityScore', 0), reverse=True)
print(json.dumps(pending, ensure_ascii=False))
conn.close()
"@

$pending = @()
if ($pendingJson) {
  $pending = $pendingJson | ConvertFrom-Json
}
if (-not $pending) {
  Write-Output 'human_alert_monitor: no_pending_tickets'
  exit 0
}

foreach ($ticket in $pending) {
  $number = (($ticket.number | Out-String).Trim()) -replace '\D',''
  $pushName = (($ticket.pushName | Out-String).Trim())
  $reason = (($ticket.reason | Out-String).Trim())
  $intent = (($ticket.intent | Out-String).Trim())
  $priority = (($ticket.priority | Out-String).Trim())
  $priorityScore = if ($ticket.priorityScore) { $ticket.priorityScore } else { 0 }
  $snippet = (($ticket.inboundText | Out-String).Trim())
  if ($snippet.Length -gt 200) { $snippet = $snippet.Substring(0,200) }

  $priorityLabel = switch ($priority) {
    'critical' { 'CRITICO' }
    'high'     { 'ALTA' }
    'medium'   { 'MEDIA' }
    default    { 'NORMAL' }
  }

  $alertText = "[$priorityLabel] ATENCAO HUMANA: cliente aguardando. Numero: $number. Nome: $pushName. Prioridade: $priorityLabel ($priorityScore pts). Motivo: $reason. Intencao: $intent. Mensagem: $snippet"

  $body = @{
    number = $InsideSalesNumber
    text = $alertText
    delay = 0
  } | ConvertTo-Json -Depth 5

  $alertSent = $false
  try {
    Invoke-RestMethod -Method Post -Uri "$evolutionBaseUrl/message/sendText/$evolutionInstance" -Headers @{ apikey = $evolutionApiKey } -ContentType 'application/json; charset=utf-8' -Body $body | Out-Null
    $alertSent = $true
  } catch {
    $alertSent = $false
  }

  try {
    powershell -NoLogo -ExecutionPolicy Bypass -File (Join-Path $ProjectDir 'flash-whatsapp-window.ps1') | Out-Null
  } catch {}

  $ticketCreatedAt = (($ticket.createdAt | Out-String).Trim())
  $alertedAt = (Get-Date).ToUniversalTime().ToString('o')
  $alertSentText = if ($alertSent) { 'true' } else { 'false' }

  docker run --rm -v ai_n8n_data:/data python:3.11-alpine python -c @"
import json, sqlite3
workflow_id = '$WorkflowId'
ticket_number = '$number'
ticket_created_at = '$ticketCreatedAt'
alerted_at = '$alertedAt'
alert_sent = '$alertSentText' == 'true'
conn = sqlite3.connect('/data/database.sqlite')
cur = conn.cursor()
row = cur.execute('SELECT staticData FROM workflow_entity WHERE id = ?', (workflow_id,)).fetchone()
obj = json.loads(row[0] or '{}') if row else {}
global_data = obj.get('global') or {}
queue = global_data.get('humanQueue') or []
for item in queue:
    if str(item.get('number') or '') == ticket_number and str(item.get('createdAt') or '') == ticket_created_at and item.get('status') != 'closed':
        item['alertedAt'] = alerted_at
        item['alertSent'] = alert_sent
        item['alertChannel'] = 'evolution_text'
obj['global'] = global_data
cur.execute('UPDATE workflow_entity SET staticData = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE id = ?', (json.dumps(obj, ensure_ascii=False, separators=(",", ":")), workflow_id))
conn.commit()
conn.close()
"@ | Out-Null

  Write-Output "human_alert_monitor: alerted $number sent=$alertSent"
}
