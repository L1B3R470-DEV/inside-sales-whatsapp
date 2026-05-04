# migrate_crm_and_rebuild.ps1
# Migra crm_operacional.sqlite para volume persistente e reconstroi + reinicia o container router.
# Execute no diretorio do projeto (pode precisar de permissao de administrador).

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SrcCrm = Join-Path $ProjectDir "crm_operacional.sqlite"
$DestDir = "C:\AUTOMACAO\dados"
$DestCrm = Join-Path $DestDir "crm_operacional.sqlite"

Write-Host "=== Migracao CRM + Rebuild Router ===" -ForegroundColor Cyan

# 1. Garantir que C:\AUTOMACAO\dados existe
if (-not (Test-Path $DestDir)) {
    Write-Host "[1/4] Criando diretorio $DestDir ..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
} else {
    Write-Host "[1/4] Diretorio $DestDir ja existe." -ForegroundColor Green
}

# 2. Copiar crm_operacional.sqlite
if (Test-Path $SrcCrm) {
    if (-not (Test-Path $DestCrm)) {
        Write-Host "[2/4] Copiando CRM para $DestCrm ..." -ForegroundColor Yellow
        Copy-Item -Path $SrcCrm -Destination $DestCrm -Force
        Write-Host "      Copia concluida." -ForegroundColor Green
    } else {
        $srcDate = (Get-Item $SrcCrm).LastWriteTime
        $destDate = (Get-Item $DestCrm).LastWriteTime
        if ($srcDate -gt $destDate) {
            Write-Host "[2/4] CRM destino mais antigo. Atualizando..." -ForegroundColor Yellow
            Copy-Item -Path $SrcCrm -Destination $DestCrm -Force
            Write-Host "      Copia concluida." -ForegroundColor Green
        } else {
            Write-Host "[2/4] CRM destino ja e o mais recente. Nada a copiar." -ForegroundColor Green
        }
    }
} else {
    Write-Host "[2/4] AVISO: $SrcCrm nao encontrado. CRM novo sera criado em /runtime." -ForegroundColor Yellow
}

# 3. Rebuild da imagem Docker
Write-Host "[3/4] Rebuilding imagem attendant-router:latest ..." -ForegroundColor Yellow
Set-Location $ProjectDir
docker build -t attendant-router:latest -f docker/router/Dockerfile .
Write-Host "      Build concluido." -ForegroundColor Green

# 4. Restart do container router
Write-Host "[4/4] Reiniciando container router ..." -ForegroundColor Yellow
docker compose up -d --no-deps router
Write-Host "      Container reiniciado." -ForegroundColor Green

Write-Host ""
Write-Host "=== Concluido! ===" -ForegroundColor Cyan
Write-Host "Acesse http://localhost:8091/sdr-dashboard para verificar." -ForegroundColor White
Write-Host "LEADS e MSGS HOJE devem aparecer corretamente agora." -ForegroundColor White
\n
