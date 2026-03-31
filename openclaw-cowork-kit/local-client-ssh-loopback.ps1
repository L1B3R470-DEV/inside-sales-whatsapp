[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SshTarget,
    [Parameter(Mandatory = $true)][string]$GatewayToken,
    [string]$IdentityFile = "",
    [int]$LocalTunnelPort = 18789,
    [int]$RemoteGatewayPort = 18789,
    [switch]$SetupOnly,
    [switch]$StopTunnel,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Ensure-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Comando obrigatorio nao encontrado: $Name"
    }
}

function Resolve-SshExecutable {
    $cmd = Get-Command ssh -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        return $cmd.Source
    }

    $fallback = "C:\Windows\System32\OpenSSH\ssh.exe"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }

    return $null
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

function Get-TunnelProcesses {
    $needle = "-L $LocalTunnelPort`:127.0.0.1:$RemoteGatewayPort"
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -ieq "ssh.exe" -and
            $_.CommandLine -like "*$needle*" -and
            $_.CommandLine -like "*$SshTarget*"
        }
}

Ensure-Command -Name "openclaw"
$sshExe = Resolve-SshExecutable
if (-not $sshExe -and -not $DryRun) {
    throw "Comando obrigatorio nao encontrado: ssh"
}

if ($StopTunnel) {
    Write-Step "Encerrando tunnel SSH"
    $procs = if ($DryRun) { @() } else { Get-TunnelProcesses }
    foreach ($proc in $procs) {
        Write-Host "Parando PID $($proc.ProcessId)" -ForegroundColor DarkGray
        if (-not $DryRun) {
            Stop-Process -Id $proc.ProcessId -Force
        }
    }
    Write-Host "Tunnel encerrado." -ForegroundColor Green
    return
}

Write-Step "Configurando OpenClaw local para gateway remoto via loopback"
Invoke-Cmd -FilePath "openclaw" -Arguments @("config", "set", "gateway.mode", "remote")
Invoke-Cmd -FilePath "openclaw" -Arguments @("config", "set", "gateway.remote.url", "ws://127.0.0.1:$LocalTunnelPort")
Invoke-Cmd -FilePath "openclaw" -Arguments @("config", "set", "gateway.remote.token", $GatewayToken)

if (-not $SetupOnly) {
    Write-Step "Subindo tunnel SSH"
    $existing = if ($DryRun) { @() } else { Get-TunnelProcesses }
    if ($existing.Count -gt 0) {
        Write-Host "Tunnel ja existe para esse alvo." -ForegroundColor Yellow
    } else {
        $sshArgs = @(
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3"
        )

        if (-not [string]::IsNullOrWhiteSpace($IdentityFile)) {
            $sshArgs += @("-i", $IdentityFile)
        }

        $sshArgs += @(
            "-N",
            "-L", "$LocalTunnelPort`:127.0.0.1:$RemoteGatewayPort",
            $SshTarget
        )

        Write-Host "ssh $($sshArgs -join ' ')" -ForegroundColor DarkGray
        if (-not $DryRun) {
            Start-Process -FilePath $sshExe -ArgumentList $sshArgs -WindowStyle Hidden | Out-Null
            Start-Sleep -Seconds 3
        }
    }
}

Write-Step "Testando o gateway remoto tunneled"
Invoke-Cmd -FilePath "openclaw" -Arguments @(
    "gateway", "probe",
    "--url", "ws://127.0.0.1:$LocalTunnelPort",
    "--token", $GatewayToken
)
Invoke-Cmd -FilePath "openclaw" -Arguments @("status")

Write-Host ""
Write-Host "CLIENTE PRONTO" -ForegroundColor Green
Write-Host "Gateway remoto via tunnel : ws://127.0.0.1:$LocalTunnelPort"
Write-Host "Sessao ACP recomendada    : openclaw acp --session agent:claude-office:main"
Write-Host "Parar tunnel              : powershell -ExecutionPolicy Bypass -File .\local-client-ssh-loopback.ps1 -SshTarget $SshTarget -GatewayToken $GatewayToken -StopTunnel"
