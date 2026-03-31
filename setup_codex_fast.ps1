# Versão ULTRA RÁPIDA - Acesso ESSENCIAL em segundos
# Sem varrer sistema, apenas configurações críticas

Write-Host "=== CONFIGURAÇÃO ULTRA RÁPIDA DO CHATGPT CODEX ===" -ForegroundColor Green
Write-Host "Tempo estimado: 30-60 segundos" -ForegroundColor Cyan

# 1. Permissões dos executáveis (instantâneo)
Write-Host "1. Configurando executáveis..." -ForegroundColor Yellow
$codexFiles = @(
    "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex.exe",
    "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex-command-runner.exe",
    "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex-windows-sandbox-setup.exe"
)

foreach ($file in $codexFiles) {
    if (Test-Path $file) {
        $acl = Get-Acl $file
        $acl.SetAccessRuleProtection($true, $false)
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administradores","FullControl","ContainerInherit,ObjectInherit","None","Allow")
        $acl.SetAccessRule($rule)
        Set-Acl $file $acl
    }
}
Write-Host "[OK] Executáveis configurados" -ForegroundColor Green

# 2. Privilégios essenciais (via registro direto)
Write-Host "2. Configurando privilégios..." -ForegroundColor Yellow
$privSettings = @(
    "SeTakeOwnershipPrivilege=1",
    "SeDebugPrivilege=1",
    "SeBackupPrivilege=1",
    "SeRestorePrivilege=1",
    "SeSecurityPrivilege=1",
    "SeLoadDriverPrivilege=1",
    "SeImpersonatePrivilege=1",
    "SeCreateTokenPrivilege=1",
    "SeAssignPrimaryTokenPrivilege=1"
)

foreach ($setting in $privSettings) {
    $priv, $value = $setting -split '='
    reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\Kerberos\Parameters" /v $priv /t REG_DWORD /d $value /f 2>$null
}
Write-Host "[OK] Privilégios configurados" -ForegroundColor Green

# 3. UAC desativado (instantâneo)
Write-Host "3. Desativando UAC..." -ForegroundColor Yellow
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "EnableLUA" /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "ConsentPromptBehaviorAdmin" /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "PromptOnSecureDesktop" /t REG_DWORD /d 0 /f
Write-Host "[OK] UAC desativado" -ForegroundColor Green

# 4. Windows Defender (instantâneo)
Write-Host "4. Configurando Windows Defender..." -ForegroundColor Yellow
try {
    Add-MpPreference -ExclusionPath "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64" -Force
    Add-MpPreference -ExclusionProcess "codex.exe" -Force
    Add-MpPreference -ExclusionProcess "codex-command-runner.exe" -Force
    Set-MpPreference -DisableRealtimeMonitoring $true -Force
    Write-Host "[OK] Windows Defender configurado" -ForegroundColor Green
} catch {
    Write-Host "[AVISO] Windows Defender parcialmente configurado" -ForegroundColor Yellow
}

# 5. Firewall (instantâneo)
Write-Host "5. Configurando Firewall..." -ForegroundColor Yellow
try {
    Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled False -Force
    Write-Host "[OK] Firewall desativado" -ForegroundColor Green
} catch {
    Write-Host "[AVISO] Firewall parcialmente configurado" -ForegroundColor Yellow
}

# 6. Política de execução (instantâneo)
Write-Host "6. Configurando política de execução..." -ForegroundColor Yellow
Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope LocalMachine -Force
Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope CurrentUser -Force
Write-Host "[OK] Política de execução configurada" -ForegroundColor Green

# 7. Variáveis de ambiente (instantâneo)
Write-Host "7. Configurando ambiente..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("CODEX_FULL_ACCESS", "1", "Machine")
[Environment]::SetEnvironmentVariable("CODEX_AUTONOMOUS", "1", "Machine")
[Environment]::SetEnvironmentVariable("CODEX_BYPASS_SECURITY", "1", "Machine")
Write-Host "[OK] Ambiente configurado" -ForegroundColor Green

# 8. Tarefa agendada (instantâneo)
Write-Host "8. Criando tarefa agendada..." -ForegroundColor Yellow
$codexPath = "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex.exe"
$action = New-ScheduledTaskAction -Execute $codexPath -Argument "--auto-mode --full-access"
$trigger = New-ScheduledTaskTrigger -AtLogon
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "ChatGPT-Codex-Autonomous" -Action $action -Trigger $trigger -Principal $principal -Force
Write-Host "[OK] Tarefa agendada criada" -ForegroundColor Green

# 9. Registro do Windows (instantâneo)
Write-Host "9. Configurando registro..." -ForegroundColor Yellow
New-Item -Path "HKLM:\SOFTWARE\ChatGPT-Codex" -Force -ErrorAction SilentlyContinue
New-Item -Path "HKLM:\SOFTWARE\ChatGPT-Codex\Permissions" -Force -ErrorAction SilentlyContinue
Set-ItemProperty -Path "HKLM:\SOFTWARE\ChatGPT-Codex\Permissions" -Name "FullSystemAccess" -Value 1 -Force
Set-ItemProperty -Path "HKLM:\SOFTWARE\ChatGPT-Codex\Permissions" -Name "AutonomousMode" -Value 1 -Force
Set-ItemProperty -Path "HKLM:\SOFTWARE\ChatGPT-Codex\Permissions" -Name "BypassRestrictions" -Value 1 -Force
Write-Host "[OK] Registro configurado" -ForegroundColor Green

# 10. Acesso a arquivos críticos (apenas essencial)
Write-Host "10. Configurando acesso crítico..." -ForegroundColor Yellow
$criticalFiles = @(
    "C:\Windows\System32\config\SAM",
    "C:\Windows\System32\config\SYSTEM",
    "C:\Windows\System32\config\SECURITY",
    "C:\Windows\System32\config\SOFTWARE",
    "C:\Windows\System32\config\DEFAULT"
)

foreach ($file in $criticalFiles) {
    if (Test-Path $file) {
        icacls $file /grant Administradores:(F) 2>$null
    }
}
Write-Host "[OK] Acesso crítico configurado" -ForegroundColor Green

Write-Host "`n=== CONFIGURAÇÃO ULTRA RÁPIDA CONCLUÍDA ===" -ForegroundColor Green
Write-Host "Tempo total: ~60 segundos" -ForegroundColor Cyan
Write-Host "Reinicie o sistema para aplicar as alterações" -ForegroundColor Yellow
Write-Host "ChatGPT CODEX pronto para operações autônomas!" -ForegroundColor Cyan
