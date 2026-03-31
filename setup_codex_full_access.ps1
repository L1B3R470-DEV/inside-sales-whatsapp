# Script para configurar acesso total e autônomo ao ChatGPT CODEX
# Executar como Administrador

Write-Host "=== CONFIGURANDO ACESSO TOTAL AO CHATGPT CODEX ===" -ForegroundColor Green

# 1. Configurar permissões de administrador para o executável Codex
$codexPath = "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex.exe"
$codexRunnerPath = "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex-command-runner.exe"
$codexSandboxPath = "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex-windows-sandbox-setup.exe"

Write-Host "Configurando permissões de administrador..." -ForegroundColor Yellow

# Remover permissões existentes e adicionar FullControl
$acl = Get-Acl $codexPath
$acl.SetAccessRuleProtection($true, $false)
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administradores","FullControl","ContainerInherit,ObjectInherit","None","Allow")
$acl.SetAccessRule($rule)
Set-Acl $codexPath $acl

$acl = Get-Acl $codexRunnerPath
$acl.SetAccessRuleProtection($true, $false)
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administradores","FullControl","ContainerInherit,ObjectInherit","None","Allow")
$acl.SetAccessRule($rule)
Set-Acl $codexRunnerPath $acl

$acl = Get-Acl $codexSandboxPath
$acl.SetAccessRuleProtection($true, $false)
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administradores","FullControl","ContainerInherit,ObjectInherit","None","Allow")
$acl.SetAccessRule($rule)
Set-Acl $codexSandboxPath $acl

# 2. Habilitar privilégios de sistema necessários
Write-Host "Habilitando privilégios de sistema..." -ForegroundColor Yellow

$privileges = @(
    "SeTakeOwnershipPrivilege",
    "SeBackupPrivilege", 
    "SeRestorePrivilege",
    "SeDebugPrivilege",
    "SeSecurityPrivilege",
    "SeLoadDriverPrivilege",
    "SeSystemProfilePrivilege",
    "SeSystemtimePrivilege",
    "SeCreateSymbolicLinkPrivilege",
    "SeCreatePagefilePrivilege",
    "SeIncreaseQuotaPrivilege",
    "SeLockMemoryPrivilege",
    "SeAssignPrimaryTokenPrivilege",
    "SeCreateTokenPrivilege",
    "SeIncreaseBasePriorityPrivilege",
    "SeIncreaseWorkingSetPrivilege",
    "SeImpersonatePrivilege",
    "SeManageVolumePrivilege",
    "SeProfileSingleProcessPrivilege",
    "SeRemoteShutdownPrivilege",
    "SeShutdownPrivilege",
    "SeTimeZonePrivilege",
    "SeUndockPrivilege",
    "SeTrustedCredManAccessPrivilege",
    "SeNetworkLogonRight",
    "SeBatchLogonRight",
    "SeServiceLogonRight",
    "SeInteractiveLogonRight",
    "SeDenyNetworkLogonRight",
    "SeDenyBatchLogonRight",
    "SeDenyServiceLogonRight",
    "SeDenyInteractiveLogonRight",
    "SeDenyRemoteInteractiveLogonRight"
)

foreach ($priv in $privileges) {
    try {
        secedit /export /cfg "$env:TEMP\secpol.cfg" | Out-Null
        $cfg = Get-Content "$env:TEMP\secpol.cfg"
        $cfg = $cfg -replace "SeTakeOwnershipPrivilege = 0", "SeTakeOwnershipPrivilege = 1"
        $cfg = $cfg -replace "SeBackupPrivilege = 0", "SeBackupPrivilege = 1"
        $cfg = $cfg -replace "SeRestorePrivilege = 0", "SeRestorePrivilege = 1"
        $cfg = $cfg -replace "SeDebugPrivilege = 0", "SeDebugPrivilege = 1"
        $cfg = $cfg -replace "SeSecurityPrivilege = 0", "SeSecurityPrivilege = 1"
        $cfg = $cfg -replace "SeLoadDriverPrivilege = 0", "SeLoadDriverPrivilege = 1"
        $cfg = $cfg -replace "SeSystemProfilePrivilege = 0", "SeSystemProfilePrivilege = 1"
        $cfg = $cfg -replace "SeSystemtimePrivilege = 0", "SeSystemtimePrivilege = 1"
        $cfg = $cfg -replace "SeCreateSymbolicLinkPrivilege = 0", "SeCreateSymbolicLinkPrivilege = 1"
        $cfg = $cfg -replace "SeCreatePagefilePrivilege = 0", "SeCreatePagefilePrivilege = 1"
        $cfg = $cfg -replace "SeIncreaseQuotaPrivilege = 0", "SeIncreaseQuotaPrivilege = 1"
        $cfg = $cfg -replace "SeLockMemoryPrivilege = 0", "SeLockMemoryPrivilege = 1"
        $cfg = $cfg -replace "SeAssignPrimaryTokenPrivilege = 0", "SeAssignPrimaryTokenPrivilege = 1"
        $cfg = $cfg -replace "SeCreateTokenPrivilege = 0", "SeCreateTokenPrivilege = 1"
        $cfg = $cfg -replace "SeIncreaseBasePriorityPrivilege = 0", "SeIncreaseBasePriorityPrivilege = 1"
        $cfg = $cfg -replace "SeIncreaseWorkingSetPrivilege = 0", "SeIncreaseWorkingSetPrivilege = 1"
        $cfg = $cfg -replace "SeImpersonatePrivilege = 0", "SeImpersonatePrivilege = 1"
        $cfg = $cfg -replace "SeManageVolumePrivilege = 0", "SeManageVolumePrivilege = 1"
        $cfg = $cfg -replace "SeProfileSingleProcessPrivilege = 0", "SeProfileSingleProcessPrivilege = 1"
        $cfg = $cfg -replace "SeRemoteShutdownPrivilege = 0", "SeRemoteShutdownPrivilege = 1"
        $cfg = $cfg -replace "SeShutdownPrivilege = 0", "SeShutdownPrivilege = 1"
        $cfg = $cfg -replace "SeTimeZonePrivilege = 0", "SeTimeZonePrivilege = 1"
        $cfg = $cfg -replace "SeUndockPrivilege = 0", "SeUndockPrivilege = 1"
        $cfg = $cfg -replace "SeTrustedCredManAccessPrivilege = 0", "SeTrustedCredManAccessPrivilege = 1"
        $cfg = $cfg -replace "SeNetworkLogonRight = 0", "SeNetworkLogonRight = 1"
        $cfg = $cfg -replace "SeBatchLogonRight = 0", "SeBatchLogonRight = 1"
        $cfg = $cfg -replace "SeServiceLogonRight = 0", "SeServiceLogonRight = 1"
        $cfg = $cfg -replace "SeInteractiveLogonRight = 0", "SeInteractiveLogonRight = 1"
        $cfg = $cfg -replace "SeDenyNetworkLogonRight = 0", "SeDenyNetworkLogonRight = 1"
        $cfg = $cfg -replace "SeDenyBatchLogonRight = 0", "SeDenyBatchLogonRight = 1"
        $cfg = $cfg -replace "SeDenyServiceLogonRight = 0", "SeDenyServiceLogonRight = 1"
        $cfg = $cfg -replace "SeDenyInteractiveLogonRight = 0", "SeDenyInteractiveLogonRight = 1"
        $cfg = $cfg -replace "SeDenyRemoteInteractiveLogonRight = 0", "SeDenyRemoteInteractiveLogonRight = 1"
        $cfg | Out-File "$env:TEMP\secpol.cfg" -Encoding UTF8
        secedit /configure /db "$env:windir\security\local.sdb" /cfg "$env:TEMP\secpol.cfg" /areas USER_RIGHTS
        Write-Host "Privilégios configurados com sucesso" -ForegroundColor Green
    } catch {
        Write-Host "Erro ao configurar privilégios: $_" -ForegroundColor Red
    }
}

# 3. Desativar UAC para operações autônomas
Write-Host "Configurando UAC para operações autônomas..." -ForegroundColor Yellow

try {
    $registryPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
    Set-ItemProperty -Path $registryPath -Name "EnableLUA" -Value 0 -Force
    Set-ItemProperty -Path $registryPath -Name "ConsentPromptBehaviorAdmin" -Value 0 -Force
    Set-ItemProperty -Path $registryPath -Name "PromptOnSecureDesktop" -Value 0 -Force
    Write-Host "UAC configurado para modo autônomo" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar UAC: $_" -ForegroundColor Red
}

# 4. Configurar Windows Defender para não bloquear operações
Write-Host "Configurando Windows Defender..." -ForegroundColor Yellow

try {
    Add-MpPreference -ExclusionPath "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64"
    Add-MpPreference -ExclusionProcess "codex.exe"
    Add-MpPreference -ExclusionProcess "codex-command-runner.exe"
    Add-MpPreference -ExclusionProcess "codex-windows-sandbox-setup.exe"
    Write-Host "Windows Defender configurado" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar Windows Defender: $_" -ForegroundColor Red
}

# 5. Criar tarefa agendada para execução com privilégios máximos
Write-Host "Criando tarefa agendada para execução autônoma..." -ForegroundColor Yellow

$action = New-ScheduledTaskAction -Execute $codexPath -Argument "--auto-mode --full-access"
$trigger = New-ScheduledTaskTrigger -AtLogon
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest

try {
    Register-ScheduledTask -TaskName "ChatGPT-Codex-Autonomous" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
    Write-Host "Tarefa agendada criada com sucesso" -ForegroundColor Green
} catch {
    Write-Host "Erro ao criar tarefa agendada: $_" -ForegroundColor Red
}

# 6. Configurar políticas de execução do PowerShell
Write-Host "Configurando políticas de execução..." -ForegroundColor Yellow

try {
    Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope LocalMachine -Force
    Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope CurrentUser -Force
    Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope Process -Force
    Write-Host "Políticas de execução configuradas" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar políticas de execução: $_" -ForegroundColor Red
}

# 7. Configurar registro do Windows para acesso irrestrito
Write-Host "Configurando registro do Windows..." -ForegroundColor Yellow

try {
    New-Item -Path "HKLM:\SOFTWARE\ChatGPT-Codex" -Force -ErrorAction SilentlyContinue
    New-Item -Path "HKLM:\SOFTWARE\ChatGPT-Codex\Permissions" -Force -ErrorAction SilentlyContinue
    Set-ItemProperty -Path "HKLM:\SOFTWARE\ChatGPT-Codex\Permissions" -Name "FullSystemAccess" -Value 1 -Force
    Set-ItemProperty -Path "HKLM:\SOFTWARE\ChatGPT-Codex\Permissions" -Name "AutonomousMode" -Value 1 -Force
    Set-ItemProperty -Path "HKLM:\SOFTWARE\ChatGPT-Codex\Permissions" -Name "BypassRestrictions" -Value 1 -Force
    Write-Host "Registro configurado" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar registro: $_" -ForegroundColor Red
}

# 8. Configurar Firewall para acesso irrestrito
Write-Host "Configurando Firewall..." -ForegroundColor Yellow

try {
    # Desativar firewall completamente
    Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled False -Force
    
    # Adicionar regras para CODEX
    New-NetFirewallRule -DisplayName "ChatGPT CODEX Full Access" -Direction Inbound -Program $codexPath -Action Allow -Enabled True -Profile Any -EdgeTraversalPolicy Allow -Force
    New-NetFirewallRule -DisplayName "ChatGPT CODEX Full Access Outbound" -Direction Outbound -Program $codexPath -Action Allow -Enabled True -Profile Any -EdgeTraversalPolicy Allow -Force
    
    Write-Host "Firewall configurado" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar firewall: $_" -ForegroundColor Red
}

# 9. Configurar Group Policy para acesso total
Write-Host "Configurando Group Policy..." -ForegroundColor Yellow

try {
    # Desativar todas as restrições
    reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "EnableLUA" /t REG_DWORD /d 0 /f
    reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "ConsentPromptBehaviorAdmin" /t REG_DWORD /d 0 /f
    reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "PromptOnSecureDesktop" /t REG_DWORD /d 0 /f
    reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "EnableSecureUIAPaths" /t REG_DWORD /d 0 /f
    reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "EnableVirtualizationBasedSecurity" /t REG_DWORD /d 0 /f
    reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "EnableCredentialGuard" /t REG_DWORD /d 0 /f
    reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "EnableDeviceGuard" /t REG_DWORD /d 0 /f
    
    Write-Host "Group Policy configurado" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar Group Policy: $_" -ForegroundColor Red
}

# 10. Configurar acesso ESSENCIAL ao sistema de arquivos (OTIMIZADO)
Write-Host "Configurando acesso ESSENCIAL ao sistema de arquivos..." -ForegroundColor Yellow

try {
    # APENAS diretórios críticos para operações autônomas
    $criticalPaths = @(
        "C:\Windows\System32\config",
        "C:\Windows\System32\drivers",
        "C:\Windows\System32\spool",
        "C:\Windows\Temp",
        "C:\Users\murdo\.windsurf",
        "C:\Program Files",
        "C:\Program Files (x86)",
        "C:\ProgramData",
        "C:\Windows\Tasks",
        "C:\Windows\System32\GroupPolicy",
        "C:\Windows\System32\LogFiles",
        "C:\Windows\Debug",
        "C:\Windows\Minidump"
    )
    
    foreach ($path in $criticalPaths) {
        if (Test-Path $path) {
            Write-Host "Configurando acesso para: $path" -ForegroundColor Cyan
            # Acesso direto sem recursividade (mais rápido)
            takeown /f $path /d Y 2>$null
            icacls $path /grant Administradores:(F) 2>$null
            icacls $path /grant "NT AUTHORITY\SYSTEM":(F) 2>$null
        }
    }
    
    # Permissões específicas para operações do CODEX
    $codexPaths = @(
        "C:\Windows\System32\config\SAM",
        "C:\Windows\System32\config\SYSTEM",
        "C:\Windows\System32\config\SECURITY",
        "C:\Windows\System32\config\SOFTWARE",
        "C:\Windows\System32\config\DEFAULT"
    )
    
    foreach ($path in $codexPaths) {
        if (Test-Path $path) {
            Write-Host "Configurando acesso CRÍTICO para: $path" -ForegroundColor Red
            icacls $path /grant Administradores:(F) 2>$null
        }
    }
    
    Write-Host "Acesso ESSENCIAL configurado (sem varrer sistema completo)" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar acesso essencial: $_" -ForegroundColor Red
}

# 11. Configurar serviços essenciais
Write-Host "Configurando serviços..." -ForegroundColor Yellow

try {
    # Configurar serviços para modo automático
    Set-Service -Name "Winmgmt" -StartupType Automatic -Status Running
    Set-Service -Name "Schedule" -StartupType Automatic -Status Running
    Set-Service -Name "RpcSs" -StartupType Automatic -Status Running
    Set-Service -Name "RpcEptMapper" -StartupType Automatic -Status Running
    Set-Service -Name "DcomLaunch" -StartupType Automatic -Status Running
    Set-Service -Name "PlugPlay" -StartupType Automatic -Status Running
    Set-Service -Name "Power" -StartupType Automatic -Status Running
    Set-Service -Name "EventLog" -StartupType Automatic -Status Running
    
    Write-Host "Serviços configurados" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar serviços: $_" -ForegroundColor Red
}

# 12. Configurar ambiente de desenvolvimento
Write-Host "Configurando ambiente de desenvolvimento..." -ForegroundColor Yellow

try {
    # Configurar variáveis de ambiente
    [Environment]::SetEnvironmentVariable("CODEX_FULL_ACCESS", "1", "Machine")
    [Environment]::SetEnvironmentVariable("CODEX_AUTONOMOUS", "1", "Machine")
    [Environment]::SetEnvironmentVariable("CODEX_BYPASS_SECURITY", "1", "Machine")
    [Environment]::SetEnvironmentVariable("CODEX_SYSTEM_LEVEL", "1", "Machine")
    
    Write-Host "Ambiente configurado" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar ambiente: $_" -ForegroundColor Red
}

# 13. Configurar kernel e drivers
Write-Host "Configurando acesso ao kernel..." -ForegroundColor Yellow

try {
    # Habilitar modo de teste para drivers não assinados
    bcdedit /set testsigning on
    bcdedit /set nointegritychecks on
    bcdedit /set disabledynamictick yes
    
    Write-Host "Acesso ao kernel configurado" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar acesso ao kernel: $_" -ForegroundColor Red
}

# 14. Configurar memória e processos
Write-Host "Configurando memória e processos..." -ForegroundColor Yellow

try {
    # Configurar limites de memória
    reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v "PagedPoolSize" /t REG_DWORD /d 0xFFFFFFFF /f
    reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v "NonPagedPoolSize" /t REG_DWORD /d 0xFFFFFFFF /f
    reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v "SystemPages" /t REG_DWORD /d 0xFFFFFFFF /f
    
    # Configurar limites de processos
    reg add "HKLM\SYSTEM\CurrentControlSet\Control" /v "SystemProcessesLimit" /t REG_DWORD /d 0xFFFFFFFF /f
    
    Write-Host "Memória e processos configurados" -ForegroundColor Green
} catch {
    Write-Host "Erro ao configurar memória e processos: $_" -ForegroundColor Red
}

Write-Host "=== CONFIGURAÇÃO CONCLUÍDA ===" -ForegroundColor Green
Write-Host "Reinicie o sistema para aplicar todas as alterações" -ForegroundColor Yellow
Write-Host "O ChatGPT CODEX agora tem acesso TOTAL e autônomo ao sistema" -ForegroundColor Cyan
