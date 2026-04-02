# install-watcher-task.ps1
# Registra o watch-and-sync.ps1 como tarefa agendada do Windows.
# Inicia automaticamente no login. Roda em background, invisível.
# Executar UMA VEZ como administrador.

$TaskName    = "OpenClaw-AutoSync"
$ScriptPath  = "C:\Users\User\.openclaw\workspace-integration\watch-and-sync.ps1"
$WorkDir     = "C:\Users\User\.openclaw\workspace-integration"
$Description = "Monitora novos payloads OpenClaw e faz git sync automático após cada ciclo"

# Remove se já existir
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action  = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
    -WorkingDirectory $WorkDir

# Dispara no login do usuário atual
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
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

Write-Host "Tarefa '$TaskName' registrada com sucesso." -ForegroundColor Green
Write-Host "Inicia automaticamente no proximo login."
Write-Host ""
Write-Host "Para iniciar agora sem reiniciar:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Para verificar status:"
Write-Host "  Get-ScheduledTask -TaskName '$TaskName' | Select-Object State"
Write-Host ""
Write-Host "Para desinstalar:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
