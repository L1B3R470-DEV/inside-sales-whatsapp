# bootstrap-remoto.ps1
# Inicia poller e watchdog remoto de forma destacada no login.

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = "C:\Python310\python.exe"
$PollerScript = Join-Path $RepoDir "poller-codex-remoto.py"
$WatchdogScript = Join-Path $RepoDir "watchdog-remoto.ps1"
$LogFile = Join-Path $RepoDir "bootstrap-remoto.log"

function Write-Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Test-ProcessByPattern {
    param([string]$Pattern)
    return [bool](Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -like $Pattern })
}

Write-Log "=== bootstrap-remoto iniciado ==="

if (-not (Test-ProcessByPattern "*poller-codex-remoto.py*")) {
    Write-Log "Poller remoto ausente. Iniciando processo destacado..."
    Start-Process -FilePath $PythonExe -ArgumentList "`"$PollerScript`"","--relay","true","--repo-dir",".","--interval","60" -WorkingDirectory $RepoDir -WindowStyle Hidden
} else {
    Write-Log "Poller remoto ja estava ativo."
}

if (-not (Test-ProcessByPattern "*watchdog-remoto.ps1*")) {
    Write-Log "Watchdog remoto ausente. Iniciando processo destacado..."
    Start-Process -FilePath "powershell.exe" -ArgumentList "-WindowStyle","Hidden","-NonInteractive","-ExecutionPolicy","Bypass","-File","`"$WatchdogScript`"" -WorkingDirectory $RepoDir -WindowStyle Hidden
} else {
    Write-Log "Watchdog remoto ja estava ativo."
}

Write-Log "=== bootstrap-remoto concluido ==="
