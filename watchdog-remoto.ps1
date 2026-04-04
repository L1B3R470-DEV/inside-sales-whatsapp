# watchdog-remoto.ps1
# Mantem o poller remoto vivo e tenta reinicia-lo quando o processo cair.

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TaskName = "OpenClaw-CodexRemotoPoller"
$Launcher = Join-Path $RepoDir "start-poller-remoto.bat"
$PythonExe = "C:\Python310\python.exe"
$PollerScript = Join-Path $RepoDir "poller-codex-remoto.py"
$SupervisorScript = Join-Path $RepoDir "orq-supervisor.py"
$LogFile = Join-Path $RepoDir "watchdog-remoto.log"
$IntervalSeconds = 60

function Write-Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Get-PollerProcess {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -ieq "python.exe" -and
            $_.CommandLine -and
            $_.CommandLine -like "*poller-codex-remoto.py*" -and
            $_.CommandLine -like "*--relay true*"
        }
}

function Get-SupervisorProcess {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -ieq "python.exe" -and
            $_.CommandLine -and
            $_.CommandLine -like "*orq-supervisor.py*"
        }
}

function Get-ProcessCreationTime {
    param([Parameter(Mandatory = $true)]$ProcessRecord)

    $raw = $ProcessRecord.CreationDate
    if (-not $raw) {
        throw "CreationDate ausente no processo."
    }

    if ($raw -is [datetime]) {
        return $raw
    }

    try {
        return [datetime]$raw
    } catch {
        return [Management.ManagementDateTimeConverter]::ToDateTime([string]$raw)
    }
}

function Restart-TrackedPythonProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$FriendlyName
    )

    $proc = Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -ieq "python.exe" -and
            $_.CommandLine -and
            $_.CommandLine -like $Pattern
        } |
        Select-Object -First 1

    if (-not $proc) {
        return $false
    }

    try {
        $created = Get-ProcessCreationTime -ProcessRecord $proc
        $scriptWrite = (Get-Item $ScriptPath).LastWriteTime
        if ($scriptWrite -le $created) {
            return $false
        }

        Write-Log "$FriendlyName com codigo desatualizado. Reiniciando para carregar $ScriptPath..."
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        Start-Sleep -Seconds 2
        Start-Process -FilePath $PythonExe -ArgumentList $ArgumentList -WorkingDirectory $RepoDir -WindowStyle Hidden
        Start-Sleep -Seconds 5
        Write-Log "$FriendlyName reiniciado apos atualizacao de script."
        return $true
    } catch {
        Write-Log "Falha ao reiniciar $FriendlyName apos mudanca de script: $($_.Exception.Message)"
        return $false
    }
}

Write-Log "=== watchdog-remoto iniciado ==="
Write-Log "Repo: $RepoDir"
Write-Log "Task monitorada: $TaskName"

while ($true) {
    try {
        Restart-TrackedPythonProcess -Pattern "*poller-codex-remoto.py*" -ScriptPath $PollerScript -ArgumentList @("`"$PollerScript`"","--relay","true","--repo-dir",".","--interval","60") -FriendlyName "Poller remoto" | Out-Null
        Restart-TrackedPythonProcess -Pattern "*orq-supervisor.py*" -ScriptPath $SupervisorScript -ArgumentList @("`"$SupervisorScript`"","--interval","60") -FriendlyName "Supervisor remoto" | Out-Null

        $poller = Get-PollerProcess
        if (-not $poller) {
            Write-Log "Poller remoto ausente. Tentando reiniciar pela tarefa agendada..."
            try {
                Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
                Start-Sleep -Seconds 5
            } catch {
                Write-Log "Falha ao iniciar tarefa '$TaskName': $($_.Exception.Message)"
            }

            $poller = Get-PollerProcess
            if (-not $poller) {
                Write-Log "Tarefa agendada nao reergueu o poller. Iniciando launcher direto..."
                Start-Process -FilePath $Launcher -WorkingDirectory $RepoDir -WindowStyle Hidden
                Start-Sleep -Seconds 5
                $poller = Get-PollerProcess
            }

            if ($poller) {
                Write-Log "Poller remoto reerguido com sucesso."
            } else {
                Write-Log "ERRO: watchdog nao conseguiu reerguer o poller remoto nesta tentativa."
            }
        }

        $supervisor = Get-SupervisorProcess
        if (-not $supervisor) {
            Write-Log "Supervisor remoto ausente. Iniciando processo destacado..."
            Start-Process -FilePath $PythonExe -ArgumentList "`"$SupervisorScript`"","--interval","60" -WorkingDirectory $RepoDir -WindowStyle Hidden
            Start-Sleep -Seconds 5
            $supervisor = Get-SupervisorProcess
            if ($supervisor) {
                Write-Log "Supervisor remoto reerguido com sucesso."
            } else {
                Write-Log "ERRO: watchdog nao conseguiu reerguer o supervisor remoto nesta tentativa."
            }
        }
    } catch {
        Write-Log "ERRO inesperado no watchdog: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds $IntervalSeconds
}
