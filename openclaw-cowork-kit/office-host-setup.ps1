[CmdletBinding()]
param(
    [string]$WorkspaceDir = "C:\PROJETOS\ATENDENTE",
    [string]$GatewayToken = "",
    [int]$GatewayPort = 18789,
    [string[]]$AgentNames = @("claude-office", "architect", "qa", "integration"),
    [switch]$SkipAgentCreation,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function New-HexToken {
    param([int]$Bytes = 32)
    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
    return ([System.BitConverter]::ToString($buffer)).Replace("-", "").ToLowerInvariant()
}

function Invoke-Cmd {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $rendered = $Arguments | ForEach-Object {
        if ($_ -match '\s') { '"' + $_ + '"' } else { $_ }
    }
    Write-Host "$FilePath $($rendered -join ' ')" -ForegroundColor DarkGray

    if ($DryRun) {
        return
    }

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar: $FilePath $($Arguments -join ' ')"
    }
}

function Ensure-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Comando obrigatorio nao encontrado: $Name"
    }
}

function Get-AgentNames {
    $json = & openclaw agents list --json
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($json)) {
        return @()
    }

    try {
        $parsed = $json | ConvertFrom-Json
        if ($parsed -is [System.Array]) {
            return @($parsed | ForEach-Object { $_.name } | Where-Object { $_ })
        }
        if ($parsed.items) {
            return @($parsed.items | ForEach-Object { $_.name } | Where-Object { $_ })
        }
    } catch {
        return @()
    }

    return @()
}

Ensure-Command -Name "openclaw"

if ([string]::IsNullOrWhiteSpace($GatewayToken)) {
    $GatewayToken = New-HexToken
}

Write-Step "Preparando workspace"
if (-not (Test-Path -LiteralPath $WorkspaceDir)) {
    Write-Host "Criando: $WorkspaceDir" -ForegroundColor DarkGray
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $WorkspaceDir | Out-Null
    }
}

Write-Step "Configurando gateway local do escritorio"
Invoke-Cmd -FilePath "openclaw" -Arguments @("config", "set", "gateway.mode", "local")
Invoke-Cmd -FilePath "openclaw" -Arguments @("config", "set", "gateway.bind", "loopback")
Invoke-Cmd -FilePath "openclaw" -Arguments @("config", "set", "gateway.auth.mode", "token")
Invoke-Cmd -FilePath "openclaw" -Arguments @("config", "set", "gateway.auth.token", $GatewayToken)
Invoke-Cmd -FilePath "openclaw" -Arguments @("config", "set", "gateway.port", $GatewayPort.ToString(), "--strict-json")

Write-Step "Instalando e reiniciando o servico do gateway"
Invoke-Cmd -FilePath "openclaw" -Arguments @("gateway", "install")
Invoke-Cmd -FilePath "openclaw" -Arguments @("gateway", "restart")

if (-not $SkipAgentCreation) {
    Write-Step "Criando agents isolados"
    $existingAgents = if ($DryRun) { @() } else { Get-AgentNames }
    foreach ($agentName in $AgentNames) {
        if ($existingAgents -contains $agentName) {
            Write-Host "Agent ja existe: $agentName" -ForegroundColor Yellow
            continue
        }

        Invoke-Cmd -FilePath "openclaw" -Arguments @(
            "agents", "add", $agentName,
            "--non-interactive",
            "--workspace", $WorkspaceDir
        )
    }
}

Write-Step "Salvando token localmente no host"
$tokenDir = Join-Path $HOME ".openclaw"
$tokenFile = Join-Path $tokenDir "gateway-office-token.txt"
Write-Host "Token file: $tokenFile" -ForegroundColor DarkGray
if (-not $DryRun) {
    New-Item -ItemType Directory -Force -Path $tokenDir | Out-Null
    Set-Content -LiteralPath $tokenFile -Value $GatewayToken -NoNewline
}

Write-Step "Validando status"
Invoke-Cmd -FilePath "openclaw" -Arguments @("gateway", "status")
Invoke-Cmd -FilePath "openclaw" -Arguments @("agents", "list", "--bindings")

Write-Host ""
Write-Host "HOST PRONTO" -ForegroundColor Green
Write-Host "Workspace : $WorkspaceDir"
Write-Host "Gateway   : ws://127.0.0.1:$GatewayPort"
Write-Host "Token     : $GatewayToken"
Write-Host "Agents    : $($AgentNames -join ', ')"
Write-Host ""
Write-Host "Exemplo de tunel no outro PC:" -ForegroundColor Cyan
Write-Host "ssh -N -L $GatewayPort`:127.0.0.1:$GatewayPort usuario@host-escritorio"
