[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('Auto', 'Host', 'Router', 'Relay', 'All')]
    [string]$Mode = 'Auto',

    [int]$HostPort,
    [int]$RouterPort = 8060,
    [int]$RelayPort = 8070,

    [switch]$SkipFirewall,
    [switch]$SkipServiceConfig,
    [switch]$SkipServiceStart,
    [switch]$SkipAccessTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-AspiaServices {
    Get-Service -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like '*aspia*' -or $_.DisplayName -like '*aspia*'
        } |
        Sort-Object Name -Unique
}

function Resolve-ExistingPaths {
    param([string[]]$Paths)

    foreach ($path in $Paths) {
        if ([string]::IsNullOrWhiteSpace($path)) {
            continue
        }

        if (Test-Path -LiteralPath $path) {
            (Resolve-Path -LiteralPath $path).Path
        }
    }
}

function Get-AspiaExecutables {
    $candidates = @(
        'C:\Program Files\Aspia\Host\aspia_host.exe'
        'C:\Program Files (x86)\Aspia\Host\aspia_host.exe'
        'C:\Program Files\Aspia\Router\aspia_router.exe'
        'C:\Program Files (x86)\Aspia\Router\aspia_router.exe'
        'C:\Program Files\Aspia\Relay\aspia_relay.exe'
        'C:\Program Files (x86)\Aspia\Relay\aspia_relay.exe'
    )

    Resolve-ExistingPaths -Paths $candidates | Sort-Object -Unique
}

function Test-ExecutableMatch {
    param(
        [string[]]$Paths,
        [string]$Pattern
    )

    return @($Paths | Where-Object { $_ -match $Pattern }).Count -gt 0
}

function Get-JsonPort {
    param(
        [string]$Path,
        [string[]]$Keys,
        [int]$DefaultValue
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $DefaultValue
    }

    try {
        $json = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    }
    catch {
        Write-Warning "Nao foi possivel ler $Path. Usando valor padrao $DefaultValue."
        return $DefaultValue
    }

    foreach ($key in $Keys) {
        if ($null -ne $json.PSObject.Properties[$key]) {
            $value = $json.$key
            if ($value -is [int] -and $value -gt 0) {
                return $value
            }

            if ($value -as [int]) {
                return [int]$value
            }
        }
    }

    return $DefaultValue
}

function Add-FirewallRuleIfMissing {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DisplayName,

        [string]$Program,
        [string]$Protocol = 'TCP',
        [int]$LocalPort,
        [ValidateSet('Inbound', 'Outbound')]
        [string]$Direction = 'Inbound'
    )

    $existing = Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Ja existe regra: $DisplayName" -ForegroundColor Yellow
        return
    }

    $params = @{
        DisplayName = $DisplayName
        Direction   = $Direction
        Action      = 'Allow'
        Enabled     = 'True'
        Profile     = 'Any'
    }

    if ($Program) {
        $params['Program'] = $Program
    }

    if ($LocalPort) {
        $params['Protocol'] = $Protocol
        $params['LocalPort'] = $LocalPort
    }

    if ($PSCmdlet.ShouldProcess($DisplayName, 'Criar regra de firewall')) {
        New-NetFirewallRule @params | Out-Null
        Write-Host "Regra criada: $DisplayName" -ForegroundColor Green
    }
}

function Start-AspiaServices {
    param([System.ServiceProcess.ServiceController[]]$Services)

    foreach ($service in $Services) {
        if ($service.Status -eq 'Running') {
            Write-Host "Servico ja em execucao: $($service.Name)" -ForegroundColor Yellow
            continue
        }

        if ($PSCmdlet.ShouldProcess($service.Name, 'Iniciar servico')) {
            Start-Service -Name $service.Name
            Write-Host "Servico iniciado: $($service.Name)" -ForegroundColor Green
        }
    }
}

function Set-AspiaServiceStartupType {
    param([System.ServiceProcess.ServiceController[]]$Services)

    foreach ($service in $Services) {
        if ($service.StartType -eq 'Automatic') {
            Write-Host "Inicializacao ja automatica: $($service.Name)" -ForegroundColor Yellow
            continue
        }

        if ($PSCmdlet.ShouldProcess($service.Name, 'Definir inicializacao automatica')) {
            Set-Service -Name $service.Name -StartupType Automatic
            Write-Host "Inicializacao automatica configurada: $($service.Name)" -ForegroundColor Green
        }
    }
}

function Test-PortOpen {
    param(
        [string]$ComputerName,
        [int]$Port
    )

    try {
        return Test-NetConnection -ComputerName $ComputerName -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
    }
    catch {
        return $false
    }
}

function Get-LanIPv4Addresses {
    Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike '127.*' -and
            $_.IPAddress -notlike '169.254*' -and
            $_.PrefixOrigin -ne 'WellKnown'
        } |
        Select-Object InterfaceAlias, IPAddress
}

function Get-PublicIPAddress {
    try {
        return (Invoke-RestMethod -Uri 'https://api.ipify.org?format=text' -TimeoutSec 10)
    }
    catch {
        return $null
    }
}

$isAdmin = Test-IsAdmin

Write-Section 'Resumo'
Write-Host "Modo selecionado: $Mode"
Write-Host "Executando como administrador: $isAdmin"

if (-not $isAdmin) {
    Write-Warning 'Abra o PowerShell como Administrador. Sem isso, firewall e servicos podem falhar.'
}

$services = Get-AspiaServices
$executables = Get-AspiaExecutables
$serviceCount = @($services).Count
$executableCount = @($executables).Count

$hostConfigPath = 'C:\ProgramData\aspia\host.json'
$routerConfigPath = 'C:\ProgramData\aspia\router.json'
$relayConfigPath = 'C:\ProgramData\aspia\relay.json'

$resolvedHostPort = if ($PSBoundParameters.ContainsKey('HostPort')) {
    $HostPort
}
else {
    Get-JsonPort -Path $hostConfigPath -Keys @('Port', 'IncomingPort', 'TcpPort', 'ListenPort') -DefaultValue 8050
}

$resolvedRouterPort = Get-JsonPort -Path $routerConfigPath -Keys @('Port') -DefaultValue $RouterPort
$resolvedRelayPort = Get-JsonPort -Path $relayConfigPath -Keys @('PeerPort', 'Port') -DefaultValue $RelayPort

$componentEnabled = @{
    Host   = $false
    Router = $false
    Relay  = $false
}

if ($Mode -eq 'All') {
    $componentEnabled.Host = $true
    $componentEnabled.Router = $true
    $componentEnabled.Relay = $true
}
elseif ($Mode -in @('Host', 'Router', 'Relay')) {
    $componentEnabled[$Mode] = $true
}
else {
    $componentEnabled.Host = (Test-Path -LiteralPath $hostConfigPath) -or (Test-ExecutableMatch -Paths $executables -Pattern 'aspia_host\.exe')
    $componentEnabled.Router = (Test-Path -LiteralPath $routerConfigPath) -or (Test-ExecutableMatch -Paths $executables -Pattern 'aspia_router\.exe')
    $componentEnabled.Relay = (Test-Path -LiteralPath $relayConfigPath) -or (Test-ExecutableMatch -Paths $executables -Pattern 'aspia_relay\.exe')
}

Write-Section 'Deteccao'
Write-Host "Servicos encontrados: $serviceCount"
foreach ($service in $services) {
    Write-Host " - $($service.Name) [$($service.Status)]"
}

Write-Host "Executaveis encontrados: $executableCount"
foreach ($exe in $executables) {
    Write-Host " - $exe"
}

Write-Host "Host ativo: $($componentEnabled.Host) | Porta: $resolvedHostPort"
Write-Host "Router ativo: $($componentEnabled.Router) | Porta: $resolvedRouterPort"
Write-Host "Relay ativo: $($componentEnabled.Relay) | Porta: $resolvedRelayPort"

if (-not $SkipFirewall) {
    Write-Section 'Firewall'

    if (-not $isAdmin) {
        Write-Warning 'Pulando firewall porque o script nao esta em modo administrador.'
    }
    else {
        foreach ($exe in $executables) {
            $name = [System.IO.Path]::GetFileNameWithoutExtension($exe)
            Add-FirewallRuleIfMissing -DisplayName "Aspia Program Inbound - $name" -Program $exe -Direction Inbound
        }

        if ($componentEnabled.Host) {
            Add-FirewallRuleIfMissing -DisplayName "Aspia Host TCP $resolvedHostPort" -LocalPort $resolvedHostPort -Direction Inbound
        }

        if ($componentEnabled.Router) {
            Add-FirewallRuleIfMissing -DisplayName "Aspia Router TCP $resolvedRouterPort" -LocalPort $resolvedRouterPort -Direction Inbound
        }

        if ($componentEnabled.Relay) {
            Add-FirewallRuleIfMissing -DisplayName "Aspia Relay TCP $resolvedRelayPort" -LocalPort $resolvedRelayPort -Direction Inbound
        }
    }
}

if (-not $SkipServiceStart) {
    Write-Section 'Servicos'

    if (-not $isAdmin) {
        Write-Warning 'Pulando inicializacao de servicos porque o script nao esta em modo administrador.'
    }
    elseif ($serviceCount -eq 0) {
        Write-Warning 'Nenhum servico do Aspia foi encontrado.'
    }
    else {
        if (-not $SkipServiceConfig) {
            Set-AspiaServiceStartupType -Services $services
            $services = Get-AspiaServices
        }

        Start-AspiaServices -Services $services
    }
}

Write-Section 'Diagnostico'
Write-Host 'Portas em escuta relacionadas ao Aspia:'
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -in @($resolvedHostPort, $resolvedRouterPort, $resolvedRelayPort) } |
    Sort-Object LocalPort |
    Format-Table -AutoSize LocalAddress, LocalPort, State, OwningProcess

Write-Host ''
Write-Host 'Logs comuns do Aspia:'
Write-Host ' - C:\Users\<seu_usuario>\AppData\Local\Temp\aspia\aspia_host-*.log'
Write-Host ' - C:\Windows\Temp\aspia\aspia_host_service-*.log'
Write-Host ' - C:\Windows\Temp\aspia\aspia_router-*.log'
Write-Host ' - C:\Windows\Temp\aspia\aspia_relay-*.log'

Write-Host ''
Write-Host 'Se ainda nao conectar, revise:'
Write-Host ' - Porta configurada no Host'
Write-Host ' - Endereco/public key do Router'
Write-Host ' - NAT/port forwarding no roteador da rede'
Write-Host ' - Bloqueio por antivirus/EDR corporativo'

if (-not $SkipAccessTest) {
    Write-Section 'Acesso'

    Start-Sleep -Seconds 2

    if ($componentEnabled.Host) {
        $localAccess = Test-PortOpen -ComputerName '127.0.0.1' -Port $resolvedHostPort
        Write-Host "Host acessivel localmente em 127.0.0.1:$resolvedHostPort : $localAccess"

        $lanIPs = @(Get-LanIPv4Addresses)
        if ($lanIPs.Count -gt 0) {
            Write-Host 'Enderecos LAN para teste:'
            foreach ($entry in $lanIPs) {
                Write-Host " - $($entry.IPAddress):$resolvedHostPort [$($entry.InterfaceAlias)]"
            }
        }

        $publicIP = Get-PublicIPAddress
        if ($publicIP) {
            Write-Host "IP publico atual: $publicIP"
            Write-Host "Acesso externo exige redirecionamento TCP $resolvedHostPort no roteador para esta maquina."
        }

        if (-not $localAccess) {
            Write-Error "O Aspia Host ainda nao ficou acessivel na porta $resolvedHostPort."
        }
    }
}
