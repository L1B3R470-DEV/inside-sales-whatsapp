# install-remote-watchdog-task.ps1
# Registra o bootstrap remoto para iniciar em cada login e destacar poller + watchdog.

$TaskName    = "OpenClaw-RemoteWatchdog"
$RepoDir     = "C:\Users\murdo\workspace-integration"
$ScriptPath  = Join-Path $RepoDir "bootstrap-remoto.ps1"
$Description = "Bootstrap remoto OpenClaw para iniciar poller em relay e watchdog no login"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
    -WorkingDirectory $RepoDir

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 5 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName    $TaskName `
    -Action      $action `
    -Trigger     $trigger `
    -Settings    $settings `
    -Description $Description `
    -RunLevel    Highest `
    -Force | Out-Null

Write-Host "Tarefa '$TaskName' registrada." -ForegroundColor Green
Write-Host "Para iniciar agora: Start-ScheduledTask -TaskName '$TaskName'"
