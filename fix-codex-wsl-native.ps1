# fix-codex-wsl-native.ps1
# Repara configuracao do Codex Windows App para modo WSL-nativo
# Uso: powershell -ExecutionPolicy Bypass -File fix-codex-wsl-native.ps1

$ErrorActionPreference = 'Continue'
$codexDir = "$env:USERPROFILE\.codex"
$configToml = "$codexDir\config.toml"
$globalState = "$codexDir\.codex-global-state.json"

Write-Host "=== FIX CODEX WSL NATIVE ===" -ForegroundColor Cyan
Write-Host ""

# ── 1. Verifica WSL ───────────────────────────────────────────────────────────
Write-Host "[1/4] Verificando WSL..." -ForegroundColor Yellow
try {
    $wslList = wsl.exe -l -v 2>&1
    if ($wslList -match "Ubuntu") {
        Write-Host "  OK  Ubuntu WSL encontrado" -ForegroundColor Green
        $wslOk = $true
    } else {
        Write-Host "  AVISO  Ubuntu nao encontrado. Distribuicoes disponiveis:" -ForegroundColor Yellow
        Write-Host $wslList
        $wslOk = $false
    }
} catch {
    Write-Host "  ERRO  WSL nao acessivel: $_" -ForegroundColor Red
    $wslOk = $false
}

if (-not $wslOk) {
    Write-Host ""
    Write-Host "  WSL nao esta funcional. Tente:" -ForegroundColor Red
    Write-Host "    wsl --install" -ForegroundColor Gray
    Write-Host "    ou reiniciar o servico LxssManager:" -ForegroundColor Gray
    Write-Host "    net stop LxssManager && net start LxssManager" -ForegroundColor Gray
    Write-Host ""
}

# ── 2. Verifica binario Linux do Codex ───────────────────────────────────────
Write-Host "[2/4] Verificando binario Linux do Codex..." -ForegroundColor Yellow
$wslBin = "$codexDir\bin\wsl\codex"
if (Test-Path $wslBin) {
    $sz = [math]::Round((Get-Item $wslBin).Length / 1MB, 0)
    Write-Host "  OK  $wslBin ($sz MB)" -ForegroundColor Green
} else {
    Write-Host "  AVISO  Binario WSL nao encontrado em: $wslBin" -ForegroundColor Yellow
    Write-Host "  O Codex vai baixar automaticamente ao iniciar no modo WSL" -ForegroundColor Gray
}

# ── 3. Corrige config.toml ────────────────────────────────────────────────────
Write-Host "[3/4] Corrigindo config.toml..." -ForegroundColor Yellow
if (-not (Test-Path $configToml)) {
    Write-Host "  Criando config.toml do zero" -ForegroundColor Gray
    $tomlContent = @'
#:schema https://developers.openai.com/codex/config-schema.json

model = "gpt-5.4"
model_reasoning_effort = "high"

approval_policy = "never"
sandbox_mode = "danger-full-access"
web_search = "cached"
windows_wsl_setup_acknowledged = true
personality = "pragmatic"
[windows]
sandbox = "unelevated"
sandbox_private_desktop = false
'@
    $tomlContent | Out-File -FilePath $configToml -Encoding utf8
    Write-Host "  OK  config.toml criado" -ForegroundColor Green
} else {
    # Backup
    $bak = "$configToml.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $configToml $bak
    Write-Host "  Backup: $bak" -ForegroundColor Gray

    $toml = Get-Content $configToml -Raw

    # Garante windows_wsl_setup_acknowledged = true
    if ($toml -match 'windows_wsl_setup_acknowledged\s*=\s*false') {
        $toml = $toml -replace 'windows_wsl_setup_acknowledged\s*=\s*false', 'windows_wsl_setup_acknowledged = true'
        Write-Host "  CORRIGIDO  windows_wsl_setup_acknowledged: false -> true" -ForegroundColor Green
    } elseif ($toml -notmatch 'windows_wsl_setup_acknowledged') {
        $toml += "`nwindows_wsl_setup_acknowledged = true`n"
        Write-Host "  ADICIONADO  windows_wsl_setup_acknowledged = true" -ForegroundColor Green
    } else {
        Write-Host "  OK  windows_wsl_setup_acknowledged ja esta correto" -ForegroundColor Green
    }

    $toml | Out-File -FilePath $configToml -Encoding utf8 -NoNewline
}

# ── 4. Corrige .codex-global-state.json ──────────────────────────────────────
Write-Host "[4/4] Corrigindo .codex-global-state.json..." -ForegroundColor Yellow
if (-not (Test-Path $globalState)) {
    Write-Host "  AVISO  Arquivo nao existe ainda — sera criado pelo app ao iniciar" -ForegroundColor Yellow
    Write-Host "  Abra o Codex, va em Settings > Environment e ative 'Run in WSL'" -ForegroundColor Gray
} else {
    # Backup
    $bak2 = "$globalState.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $globalState $bak2
    Write-Host "  Backup: $bak2" -ForegroundColor Gray

    try {
        $json = Get-Content $globalState -Raw | ConvertFrom-Json

        $atom = $json.'electron-persisted-atom-state'
        if ($null -eq $atom) {
            Write-Host "  ERRO  Estrutura inesperada no global-state.json" -ForegroundColor Red
        } else {
            $current = $atom.runCodexInWindowsSubsystemForLinux
            if ($current -eq $true) {
                Write-Host "  OK  runCodexInWindowsSubsystemForLinux ja esta true" -ForegroundColor Green
            } else {
                Write-Host "  CORRIGINDO  runCodexInWindowsSubsystemForLinux: $current -> true" -ForegroundColor Yellow
                # Modifica via string (preserva encoding e campos desconhecidos)
                $raw = Get-Content $globalState -Raw
                if ($raw -match '"runCodexInWindowsSubsystemForLinux"\s*:\s*false') {
                    $raw = $raw -replace '"runCodexInWindowsSubsystemForLinux"\s*:\s*false', '"runCodexInWindowsSubsystemForLinux":true'
                    $raw | Out-File -FilePath $globalState -Encoding utf8 -NoNewline
                    Write-Host "  OK  Corrigido com sucesso" -ForegroundColor Green
                } elseif ($raw -notmatch 'runCodexInWindowsSubsystemForLinux') {
                    # Injeta antes do ultimo }
                    $raw = $raw -replace '(\}\s*)$', ',"runCodexInWindowsSubsystemForLinux":true$1'
                    $raw | Out-File -FilePath $globalState -Encoding utf8 -NoNewline
                    Write-Host "  OK  Chave adicionada ao global-state.json" -ForegroundColor Green
                }
            }
        }
    } catch {
        Write-Host "  ERRO ao processar JSON: $_" -ForegroundColor Red
        Write-Host "  Restaurando backup..." -ForegroundColor Gray
        Copy-Item $bak2 $globalState -Force
    }
}

# ── Resumo ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== RESULTADO ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "config.toml:" -ForegroundColor White
Get-Content $configToml | Select-String 'wsl|sandbox|model|approval' | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

Write-Host ""
Write-Host "global-state (runCodexInWindowsSubsystemForLinux):" -ForegroundColor White
if (Test-Path $globalState) {
    $check = Get-Content $globalState -Raw | ConvertFrom-Json
    $val = $check.'electron-persisted-atom-state'.runCodexInWindowsSubsystemForLinux
    if ($val -eq $true) {
        Write-Host "  TRUE (WSL-nativo ativo)" -ForegroundColor Green
    } else {
        Write-Host "  $val (ATENCAO: deveria ser true)" -ForegroundColor Red
    }
}

Write-Host ""
if ($wslOk) {
    Write-Host "Pronto! Reinicie o Codex para aplicar." -ForegroundColor Green
} else {
    Write-Host "ATENCAO: WSL nao esta funcional. Corrija o WSL antes de reiniciar o Codex." -ForegroundColor Red
}
Write-Host ""
