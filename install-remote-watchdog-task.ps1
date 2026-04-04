# install-remote-watchdog-task.ps1
# Registra o watchdog remoto para iniciar em cada login e manter o poller vivo.

$TaskName    = "OpenClaw-RemoteWatchdog"
$RepoDir     = "C:\Users\murdo\workspace-integration"
$ScriptPath  = Join-Path $RepoDir "watchdog-remoto.ps1"
$Description = "Watchdog remoto OpenClaw para reerguer o poller em relay quando necessario"

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
