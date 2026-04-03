# install-poller-remoto-task.ps1
# Registra o poller remoto desta maquina como tarefa agendada do Windows.
# Execucao: uma vez, preferencialmente em PowerShell elevado.

$TaskName    = "OpenClaw-CodexRemotoPoller"
$RepoDir     = "C:\Users\murdo\workspace-integration"
$PythonExe   = "C:\Python310\python.exe"
$ScriptPath  = Join-Path $RepoDir "poller-codex-remoto.py"
$Description = "Poller remoto OpenClaw em modo relay no PC murdo"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ScriptPath`" --relay true --repo-dir . --interval 60" `
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
Write-Host ""
Write-Host "Para iniciar agora:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Para verificar status:"
Write-Host "  Get-ScheduledTask -TaskName '$TaskName' | Select-Object State"
Write-Host ""
Write-Host "Para desinstalar:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
