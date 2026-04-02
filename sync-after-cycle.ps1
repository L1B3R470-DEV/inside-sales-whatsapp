# sync-after-cycle.ps1
# Executa após cada ciclo para sincronizar o repo com o remoto.
# Uso: .\sync-after-cycle.ps1 -CycleId "18B" -Message "revisão 18B homologada"

param(
    [Parameter(Mandatory=$true)]
    [string]$CycleId,

    [string]$Message = "checkpoint: ciclo $CycleId concluído"
)

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "[sync] Adicionando arquivos do ciclo $CycleId..."
git add -A

$status = git status --short
if (-not $status) {
    Write-Host "[sync] Nenhuma alteração detectada. Nada a commitar."
    exit 0
}

$fullMessage = "checkpoint: ciclo $CycleId — $Message`n`nCo-Authored-By: Inside Sales Dev <dev@insidesales.local>"
git commit -m $fullMessage

if ($LASTEXITCODE -ne 0) {
    Write-Host "[sync] ERRO: commit falhou." -ForegroundColor Red
    exit 1
}

# Push se houver remote configurado
$remote = git remote 2>$null
if ($remote) {
    Write-Host "[sync] Fazendo push para $remote..."
    git push origin master
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[sync] AVISO: push falhou. Estado local commitado." -ForegroundColor Yellow
    } else {
        Write-Host "[sync] Push concluído." -ForegroundColor Green
    }
} else {
    Write-Host "[sync] Nenhum remote configurado. Commit local apenas." -ForegroundColor Yellow
    Write-Host "[sync] Para adicionar remote: git remote add origin <URL_DO_REPO>"
}

Write-Host "[sync] Concluído. Ciclo $CycleId registrado no git."
