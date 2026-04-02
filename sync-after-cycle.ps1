# sync-after-cycle.ps1
# Executa após cada ciclo:
#   1. Commita e faz push dos artefatos no branch master
#   2. Regenera STATE.md e faz push no branch context
#
# Uso: .\sync-after-cycle.ps1 -CycleId "18B" -Message "revisão 18B homologada"

param(
    [Parameter(Mandatory=$true)]
    [string]$CycleId,

    [string]$Message = "ciclo concluído"
)

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

# ─── 1. PUSH MASTER (artefatos completos) ─────────────────────────────────────
Write-Host "[sync] Branch master — commit dos artefatos do ciclo $CycleId..." -ForegroundColor Cyan
git checkout master 2>$null
git add -A
$status = git status --short
if ($status) {
    $fullMessage = "checkpoint: ciclo $CycleId — $Message`n`nCo-Authored-By: Inside Sales Dev <dev@insidesales.local>"
    git commit -m $fullMessage
    git push origin master
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[sync] master: push OK" -ForegroundColor Green
    } else {
        Write-Host "[sync] master: push FALHOU" -ForegroundColor Red
    }
} else {
    Write-Host "[sync] master: nenhuma alteração." -ForegroundColor Yellow
}

# ─── 2. REGENERAR STATE.md ────────────────────────────────────────────────────
$lastOutput  = (Get-ChildItem "$RepoRoot\output" -Filter "*.json" -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1).Name
$lastInputDir = (Get-ChildItem "$RepoRoot" -Filter "cycle*-input" -Directory -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1).Name
$lastPayload = if ($lastInputDir) {
    (Get-ChildItem "$RepoRoot\$lastInputDir" -Filter "*.json" -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1).Name
} else { "N/A" }
$now = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

$stateContent = @"
# STATE — OpenClaw Workspace
<!-- Atualizado automaticamente por sync-after-cycle.ps1 em $now -->

## Ciclo Atual

| Campo | Valor |
|-------|-------|
| Último ciclo concluído | $CycleId |
| Último payload produzido | $lastInputDir\$lastPayload |
| Última revisão homologada | output\$lastOutput |
| Atualizado em | $now |
| Mensagem | $Message |

## Restrições Vinculantes

- session_write_policy = RESSALVA_OPERACIONAL (binding_from: 14A)
- crm_scope = snapshot-bound
- live_crm_authorized = false
- sandbox_authorized = false
- write_authorized = false
- r6_inheritance_prohibited = true
- OQ1-OQ4 = abertas, nao autorizadas, fronteiras registradas

## Cadeia Homologada

12A-S/12B → 13A/B → 14A/B → 15A/B → 16A/B → 17A/B → 18A → $CycleId ($Message)

## Proibições Absolutas

- Não tocar em produção, .mcp.json, bridge local, projeto real
- Não usar runner stateful
- Não reabrir R2 ou R6
- Não tratar OQ1-OQ4 como agenda

## Repositório

- Branch artefatos: master
- Branch contexto: context
- Remote: https://github.com/L1B3R470-DEV/inside-sales-whatsapp
"@

# ─── 3. PUSH CONTEXT (estado leve) ───────────────────────────────────────────
Write-Host "[sync] Branch context — atualizando STATE.md..." -ForegroundColor Cyan
git checkout context 2>$null
$stateContent | Out-File -FilePath "$RepoRoot\STATE.md" -Encoding UTF8
git add STATE.md
$contextStatus = git status --short
if ($contextStatus) {
    git commit -m "state: ciclo $CycleId — $Message"
    git push origin context
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[sync] context: push OK" -ForegroundColor Green
    } else {
        Write-Host "[sync] context: push FALHOU" -ForegroundColor Red
    }
} else {
    Write-Host "[sync] context: nenhuma alteração." -ForegroundColor Yellow
}

# ─── 4. VOLTAR PARA MASTER ────────────────────────────────────────────────────
git checkout master 2>$null
Write-Host ""
Write-Host "[sync] Concluido. Ciclo $CycleId registrado." -ForegroundColor Green
Write-Host "  master  -> artefatos completos"
Write-Host "  context -> STATE.md atualizado"
Write-Host ""
Write-Host "CODEX REMOTO atualiza com:"
Write-Host "  git pull origin context && cat STATE.md"
