[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepoPath,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Ensure-Dir {
    param([string]$Path)
    Write-Host "mkdir $Path" -ForegroundColor DarkGray
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Ensure-File {
    param(
        [string]$Path,
        [string]$Content
    )

    if (Test-Path -LiteralPath $Path) {
        Write-Host "exists $Path" -ForegroundColor Yellow
        return
    }

    Write-Host "write $Path" -ForegroundColor DarkGray
    if (-not $DryRun) {
        Set-Content -LiteralPath $Path -Value $Content -NoNewline
    }
}

$dirs = @(
    "agents",
    "agents\configs",
    "docs",
    "docs\architecture",
    "docs\runbooks",
    "docs\decisions",
    "knowledge",
    "integrations",
    "integrations\evolution",
    "integrations\n8n",
    "ops",
    "ops\openclaw",
    "ops\ssh",
    "prompts",
    "scripts",
    "scripts\dev",
    "scripts\ops",
    "tests",
    "tests\manual",
    "tmp"
)

foreach ($dir in $dirs) {
    Ensure-Dir -Path (Join-Path $RepoPath $dir)
}

Ensure-File -Path (Join-Path $RepoPath "agents\README.md") -Content @"
# Agents

- `claude-office`: implementacao principal no host do escritorio.
- `architect`: desenho de arquitetura e decisoes tecnicas.
- `integration`: ligacao com canais, n8n, webhooks e CRM.
- `qa`: testes, regressao e validacao.
"@

Ensure-File -Path (Join-Path $RepoPath "docs\runbooks\openclaw-cowork.md") -Content @"
# OpenClaw Cowork

- Gateway remoto acessado apenas por SSH tunnel + loopback.
- Sessao principal: `agent:claude-office:main`
- Sessao de arquitetura: `agent:architect:roadmap`
- Sessao de integracao: `agent:integration:bridge`
- Sessao de QA: `agent:qa:regression`
"@

Ensure-File -Path (Join-Path $RepoPath ".gitignore") -Content @"
.env
.env.*
!.env.example
.openclaw/
tmp/
node_modules/
dist/
build/
coverage/
*.log
*.sqlite
*.db
*.bak
*.tmp
"@

Write-Host ""
Write-Host "Estrutura Git basica criada em $RepoPath" -ForegroundColor Green
