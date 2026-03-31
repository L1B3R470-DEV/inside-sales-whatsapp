[CmdletBinding()]
param(
    [string]$ProjectPath = "",
    [switch]$GenerateGatewayToken = $true
)

$ErrorActionPreference = "Stop"

function Invoke-TextCapture {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @()
    )

    try {
        $output = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
        if ($null -eq $output) {
            $output = @()
        }
        return [pscustomobject]@{
            Ok       = ($exitCode -eq 0)
            ExitCode = $exitCode
            Output   = ($output | Out-String).TrimEnd()
        }
    } catch {
        return [pscustomobject]@{
            Ok       = $false
            ExitCode = -1
            Output   = $_.Exception.Message
        }
    }
}

function Get-CommandPathSafe {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        return $cmd.Source
    }
    return ""
}

function New-StrongToken {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ([System.BitConverter]::ToString($bytes)).Replace("-", "").ToLowerInvariant()
}

function Find-GitRootSafe {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return ""
    }

    $result = Invoke-TextCapture -FilePath "git" -Arguments @("-C", $Path, "rev-parse", "--show-toplevel")
    if ($result.Ok -and -not [string]::IsNullOrWhiteSpace($result.Output)) {
        return $result.Output.Trim()
    }

    return ""
}

function Find-CandidateGitRepos {
    param([string[]]$Roots)

    $results = New-Object System.Collections.Generic.List[string]
    foreach ($root in $Roots) {
        if ([string]::IsNullOrWhiteSpace($root) -or -not (Test-Path -LiteralPath $root)) {
            continue
        }

        try {
            $gitDirs = Get-ChildItem -LiteralPath $root -Directory -Recurse -Depth 4 -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -eq ".git" } |
                Select-Object -First 20

            foreach ($gitDir in $gitDirs) {
                $repoRoot = Split-Path -Parent $gitDir.FullName
                if ($repoRoot -and -not $results.Contains($repoRoot)) {
                    $results.Add($repoRoot)
                }
            }
        } catch {
        }
    }

    return @($results | Select-Object -First 20)
}

function Format-Block {
    param(
        [string]$Title,
        [string]$Body
    )

    $divider = "=" * 78
    @(
        $divider
        $Title
        $divider
        if ([string]::IsNullOrWhiteSpace($Body)) { "(sem dados)" } else { $Body.TrimEnd() }
        ""
    ) -join [Environment]::NewLine
}

$desktop = [Environment]::GetFolderPath("Desktop")
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportPath = Join-Path $desktop "OPENCLAW_OFFICE_PC_INTAKE_$timestamp.txt"

$username = [Environment]::UserName
$domain = [Environment]::UserDomainName
$hostname = $env:COMPUTERNAME
$userProfile = [Environment]::GetFolderPath("UserProfile")
$currentDir = (Get-Location).Path

$ipv4Lines = @()
try {
    $ipv4Lines = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*"
        } |
        Sort-Object InterfaceAlias, IPAddress |
        ForEach-Object { "{0} -> {1}" -f $_.InterfaceAlias, $_.IPAddress }
} catch {
    $ipv4Lines = @("Falha ao coletar IPs com Get-NetIPAddress.")
}

$whoamiText = (Invoke-TextCapture -FilePath "whoami").Output
$hostnameText = (Invoke-TextCapture -FilePath "hostname").Output
$ipconfigText = (Invoke-TextCapture -FilePath "ipconfig").Output

$sshPath = Get-CommandPathSafe -Name "ssh"
$sshdPath = Get-CommandPathSafe -Name "sshd"
if (-not $sshdPath -and (Test-Path -LiteralPath "C:\Windows\System32\OpenSSH\sshd.exe")) {
    $sshdPath = "C:\Windows\System32\OpenSSH\sshd.exe"
}

$sshdService = Get-Service sshd -ErrorAction SilentlyContinue
$sshServiceSummary = if ($sshdService) {
    "Status={0}; StartType={1}" -f $sshdService.Status, $sshdService.StartType
} else {
    "Servico sshd nao encontrado"
}

$sshPortText = (Invoke-TextCapture -FilePath "powershell" -Arguments @(
    "-NoProfile",
    "-Command",
    "netstat -ano | Select-String ':22'"
)).Output

$sshPublicKeys = @()
$sshDir = Join-Path $userProfile ".ssh"
if (Test-Path -LiteralPath $sshDir) {
    $sshPublicKeys = Get-ChildItem -LiteralPath $sshDir -Filter "*.pub" -File -ErrorAction SilentlyContinue |
        ForEach-Object { $_.FullName }
}

$gitPath = Get-CommandPathSafe -Name "git"
$gitVersion = (Invoke-TextCapture -FilePath "git" -Arguments @("--version")).Output

$projectGitRoot = ""
if (-not [string]::IsNullOrWhiteSpace($ProjectPath)) {
    $projectGitRoot = Find-GitRootSafe -Path $ProjectPath
} else {
    $projectGitRoot = Find-GitRootSafe -Path $currentDir
}

$candidateRepos = @()
if (-not $projectGitRoot) {
    $candidateRepos = Find-CandidateGitRepos -Roots @(
        (Join-Path $userProfile "Desktop"),
        (Join-Path $userProfile "Documents"),
        (Join-Path $userProfile "source"),
        (Join-Path $userProfile "projects"),
        (Join-Path $userProfile "workspace")
    )
}

$repoRemoteText = ""
$repoBranchText = ""
if ($projectGitRoot) {
    $repoRemoteText = (Invoke-TextCapture -FilePath "git" -Arguments @("-C", $projectGitRoot, "remote", "-v")).Output
    $repoBranchText = (Invoke-TextCapture -FilePath "git" -Arguments @("-C", $projectGitRoot, "branch", "--show-current")).Output
}

$openclawPath = Get-CommandPathSafe -Name "openclaw"
$openclawVersion = ""
$openclawConfigFile = ""
$openclawGatewayStatus = ""
$openclawAgents = ""
$openclawStatus = ""
$openclawModelsStatus = ""

if ($openclawPath) {
    $openclawVersion = (Invoke-TextCapture -FilePath "openclaw" -Arguments @("--version")).Output
    $openclawConfigFile = (Invoke-TextCapture -FilePath "openclaw" -Arguments @("config", "file")).Output
    $openclawGatewayStatus = (Invoke-TextCapture -FilePath "openclaw" -Arguments @("gateway", "status")).Output
    $openclawAgents = (Invoke-TextCapture -FilePath "openclaw" -Arguments @("agents", "list", "--bindings")).Output
    $openclawStatus = (Invoke-TextCapture -FilePath "openclaw" -Arguments @("status")).Output
    $openclawModelsStatus = (Invoke-TextCapture -FilePath "openclaw" -Arguments @("models", "status")).Output
}

$gatewayToken = if ($GenerateGatewayToken) { New-StrongToken } else { "" }

$manualTemplate = @"
Preencha ou confirme manualmente, se necessario:

usuario_ssh:
host_ou_ip:
porta_ssh: 22
autenticacao: senha ou chave
caminho_chave_privada_local:
workspace_escritorio:
repo_git_escritorio:
git_remote_url:
branch_principal:
openclaw_instalado:
agents_existentes:
gateway_token:
"@

$content = @(
    Format-Block -Title "RESUMO BASICO" -Body @"
Gerado em: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz")
Usuario local: $username
Dominio/maquina: $domain
Hostname (env): $hostname
Current directory: $currentDir
Desktop: $desktop
UserProfile: $userProfile
"@
    Format-Block -Title "IDENTIDADE DA MAQUINA" -Body @"
whoami:
$whoamiText

hostname:
$hostnameText
"@
    Format-Block -Title "REDE E IPS" -Body @"
IPs IPv4 detectados:
$($ipv4Lines -join [Environment]::NewLine)

ipconfig:
$ipconfigText
"@
    Format-Block -Title "SSH" -Body @"
ssh.exe:
$sshPath

sshd.exe:
$sshdPath

Servico sshd:
$sshServiceSummary

Escuta porta 22:
$sshPortText

Chaves publicas encontradas:
$($sshPublicKeys -join [Environment]::NewLine)
"@
    Format-Block -Title "GIT" -Body @"
git.exe:
$gitPath

git --version:
$gitVersion

ProjectPath informado:
$ProjectPath

Git root detectado:
$projectGitRoot

Branch atual:
$repoBranchText

Remote(s):
$repoRemoteText

Repos candidatos, se o projeto nao foi detectado:
$($candidateRepos -join [Environment]::NewLine)
"@
    Format-Block -Title "OPENCLAW" -Body @"
openclaw path:
$openclawPath

openclaw --version:
$openclawVersion

openclaw config file:
$openclawConfigFile

openclaw gateway status:
$openclawGatewayStatus

openclaw agents list --bindings:
$openclawAgents

openclaw status:
$openclawStatus

openclaw models status:
$openclawModelsStatus
"@
    Format-Block -Title "TOKEN SUGERIDO PARA O GATEWAY" -Body @"
$gatewayToken
"@
    Format-Block -Title "CHECKLIST PARA ENVIAR DE VOLTA" -Body $manualTemplate
) -join [Environment]::NewLine

Set-Content -LiteralPath $reportPath -Value $content -Encoding UTF8

Write-Host ""
Write-Host "Relatorio gerado com sucesso:" -ForegroundColor Green
Write-Host $reportPath -ForegroundColor Cyan
Write-Host ""
Write-Host "Envie esse arquivo de volta para continuarmos a configuracao do cowork." -ForegroundColor Yellow
