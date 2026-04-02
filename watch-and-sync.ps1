# watch-and-sync.ps1
# Roda em background e monitora novos payloads JSON em cycle*-input/ e output/
# Quando detecta novo arquivo, extrai o cycle_id e executa sync-after-cycle.ps1
# Iniciar: .\watch-and-sync.ps1
# Parar:   Ctrl+C ou fechar a janela

$WatchPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$SyncScript = Join-Path $WatchPath "sync-after-cycle.ps1"
$LogFile = Join-Path $WatchPath "watcher.log"

function Write-Log {
    param([string]$Msg)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Write-Log "=== watch-and-sync iniciado ==="
Write-Log "Monitorando: $WatchPath"
Write-Log "Padrão: cycle*-input\*.json e output\cycle-*.json"

# Configura o watcher
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $WatchPath
$watcher.Filter = "*.json"
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true
$watcher.NotifyFilter = [System.IO.NotifyFilters]'FileName,LastWrite'

# Debounce: evita disparos duplos no mesmo arquivo
$lastFile = ""
$lastTime = [DateTime]::MinValue

$action = {
    $path    = $Event.SourceEventArgs.FullPath
    $name    = $Event.SourceEventArgs.Name
    $change  = $Event.SourceEventArgs.ChangeType

    # Só processa arquivos dentro de cycle*-input/ ou output/
    if ($path -notmatch "cycle\d+[A-Za-z-]*-input" -and $path -notmatch "\\output\\") {
        return
    }

    # Debounce: ignora se o mesmo arquivo foi processado nos últimos 5 segundos
    $now = [DateTime]::Now
    if ($path -eq $script:lastFile -and ($now - $script:lastTime).TotalSeconds -lt 5) {
        return
    }
    $script:lastFile = $path
    $script:lastTime = $now

    # Extrai cycle_id do nome do arquivo (ex: cycle-018A-..., cycle-015B-...)
    $cycleId = "unknown"
    if ($name -match "cycle-(\d+[A-Z]?)") {
        $cycleId = $matches[1]
    } elseif ($name -match "cycle(\d+[A-Z]?)") {
        $cycleId = $matches[1]
    }

    $msg = "$change detectado: $name (ciclo $cycleId)"
    Write-Log $msg

    # Aguarda 2s para o arquivo terminar de ser escrito
    Start-Sleep -Seconds 2

    Write-Log "Executando sync para ciclo $cycleId..."
    & $script:SyncScript -CycleId $cycleId -Message "auto-sync: $name"
    Write-Log "Sync concluido para $cycleId."
}

# Registra eventos
Register-ObjectEvent $watcher "Created" -Action $action | Out-Null
Register-ObjectEvent $watcher "Changed" -Action $action | Out-Null

Write-Log "Watcher ativo. Aguardando novos payloads..."
Write-Log "(Pressione Ctrl+C para parar)"

try {
    while ($true) {
        Start-Sleep -Seconds 5
    }
} finally {
    $watcher.EnableRaisingEvents = $false
    $watcher.Dispose()
    Get-EventSubscriber | Unregister-Event
    Write-Log "=== watch-and-sync encerrado ==="
}
