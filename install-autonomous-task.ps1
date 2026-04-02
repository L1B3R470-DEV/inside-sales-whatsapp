# install-autonomous-task.ps1
# Registra o poller-autonomous.ps1 como tarefa agendada do Windows.
# Execução: uma vez como administrador.
# Complementa a tarefa "OpenClaw-AutoSync" já existente.

$TaskName    = "OpenClaw-PollerAutonomous"
$ScriptPath  = "C:\Users\User\.openclaw\workspace-integration\poller-autonomous.ps1"
$WorkDir     = "C:\Users\User\.openclaw\workspace-integration"
$Description = "Poller autonomo OpenClaw: monitora inbox coordination/ e aciona Claude Code e CODEX LOCAL"

# Remove se já existir
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
    -WorkingDirectory $WorkDir

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 5 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
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
Write-Host ""
Write-Host "Para iniciar agora:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Para verificar status:"
Write-Host "  Get-ScheduledTask -TaskName '$TaskName' | Select-Object State"
Write-Host ""
Write-Host "Para ver o log em tempo real:"
Write-Host "  Get-Content $WorkDir\poller-autonomous.log -Wait"
Write-Host ""
Write-Host "Para desinstalar:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
