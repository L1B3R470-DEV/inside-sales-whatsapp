# Script de verificação COMPLETA para acesso TOTAL do ChatGPT CODEX

Write-Host "=== VERIFICAÇÃO COMPLETA DE ACESSO TOTAL ===" -ForegroundColor Red

$totalAccess = $true

# Teste 1: Verificar TODOS os privilégios
Write-Host "`nTeste 1: Verificando TODOS os privilégios..." -ForegroundColor Yellow
$privs = whoami /priv
$allPrivs = @(
    "SeTakeOwnershipPrivilege", "SeBackupPrivilege", "SeRestorePrivilege", "SeDebugPrivilege",
    "SeSecurityPrivilege", "SeLoadDriverPrivilege", "SeSystemProfilePrivilege", "SeSystemtimePrivilege",
    "SeCreateSymbolicLinkPrivilege", "SeCreatePagefilePrivilege", "SeIncreaseQuotaPrivilege", "SeLockMemoryPrivilege",
    "SeAssignPrimaryTokenPrivilege", "SeCreateTokenPrivilege", "SeIncreaseBasePriorityPrivilege", "SeIncreaseWorkingSetPrivilege",
    "SeImpersonatePrivilege", "SeManageVolumePrivilege", "SeProfileSingleProcessPrivilege", "SeRemoteShutdownPrivilege",
    "SeShutdownPrivilege", "SeTimeZonePrivilege", "SeUndockPrivilege", "SeTrustedCredManAccessPrivilege",
    "SeNetworkLogonRight", "SeBatchLogonRight", "SeServiceLogonRight", "SeInteractiveLogonRight"
)

foreach ($priv in $allPrivs) {
    if ($privs -match $priv -and $privs -match "Ativada") {
        Write-Host "[OK] $priv" -ForegroundColor Green
    } else {
        Write-Host "[FALHA] $priv NÃO ATIVADO!" -ForegroundColor Red
        $totalAccess = $false
    }
}

# Teste 2: Verificar acesso total ao sistema de arquivos
Write-Host "`nTeste 2: Verificando acesso TOTAL ao sistema de arquivos..." -ForegroundColor Yellow
try {
    # Tentar acessar C:\Windows\System32\config\SAM
    $samAccess = Test-Path "C:\Windows\System32\config\SAM"
    if ($samAccess) {
        Write-Host "[OK] Acesso ao SAM (banco de dados de usuários)" -ForegroundColor Green
    } else {
        Write-Host "[FALHA] Sem acesso ao SAM!" -ForegroundColor Red
        $totalAccess = $false
    }
    
    # Verificar permissões no C:\
    $acl = Get-Acl "C:\"
    $fullControl = $acl.Access | Where-Object { $_.FileSystemRights -match "FullControl" -and $_.AccessControlType -eq "Allow" }
    if ($fullControl) {
        Write-Host "[OK] FullControl em C:\" -ForegroundColor Green
    } else {
        Write-Host "[FALHA] Sem FullControl em C:\" -ForegroundColor Red
        $totalAccess = $false
    }
} catch {
    Write-Host "[FALHA] Erro ao verificar sistema de arquivos: $_" -ForegroundColor Red
    $totalAccess = $false
}

# Teste 3: Verificar UAC desativado
Write-Host "`nTeste 3: Verificando UAC..." -ForegroundColor Yellow
try {
    $uacEnabled = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA").EnableLUA
    if ($uacEnabled -eq 0) {
        Write-Host "[OK] UAC desativado" -ForegroundColor Green
    } else {
        Write-Host "[FALHA] UAC ainda ativo!" -ForegroundColor Red
        $totalAccess = $false
    }
} catch {
    Write-Host "[FALHA] Erro ao verificar UAC: $_" -ForegroundColor Red
    $totalAccess = $false
}

# Teste 4: Verificar Firewall
Write-Host "`nTeste 4: Verificando Firewall..." -ForegroundColor Yellow
try {
    $firewallStatus = Get-NetFirewallProfile
    $allDisabled = $true
    foreach ($fwProfile in $firewallStatus) {
        if ($fwProfile.Enabled) {
            Write-Host "[FALHA] Firewall $($fwProfile.Name) ainda ativo!" -ForegroundColor Red
            $allDisabled = $false
            $totalAccess = $false
        }
    }
    if ($allDisabled) {
        Write-Host "[OK] Todos os firewalls desativados" -ForegroundColor Green
    }
} catch {
    Write-Host "[FALHA] Erro ao verificar firewall: $_" -ForegroundColor Red
    $totalAccess = $false
}

# Teste 5: Verificar Windows Defender
Write-Host "`nTeste 5: Verificando Windows Defender..." -ForegroundColor Yellow
try {
    $defenderStatus = Get-MpComputerStatus
    if ($defenderStatus.RealTimeProtectionEnabled -eq $false) {
        Write-Host "[OK] Proteção em tempo real desativada" -ForegroundColor Green
    } else {
        Write-Host "[FALHA] Proteção em tempo real ainda ativa!" -ForegroundColor Red
        $totalAccess = $false
    }
    
    $exclusions = Get-MpPreference
    if ($exclusions.ExclusionPath -contains "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64") {
        Write-Host "[OK] Caminho do CODEX excluído" -ForegroundColor Green
    } else {
        Write-Host "[FALHA] Caminho do CODEX não excluído!" -ForegroundColor Red
        $totalAccess = $false
    }
} catch {
    Write-Host "[FALHA] Erro ao verificar Windows Defender: $_" -ForegroundColor Red
    $totalAccess = $false
}

# Teste 6: Verificar Group Policy
Write-Host "`nTeste 6: Verificando Group Policy..." -ForegroundColor Yellow
try {
    $gpSettings = @(
        "EnableLUA", "ConsentPromptBehaviorAdmin", "PromptOnSecureDesktop",
        "EnableSecureUIAPaths", "EnableVirtualizationBasedSecurity",
        "EnableCredentialGuard", "EnableDeviceGuard"
    )
    
    $allDisabled = $true
    foreach ($setting in $gpSettings) {
        $value = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name $setting -ErrorAction SilentlyContinue).$setting
        if ($value -ne 0) {
            Write-Host "[FALHA] $setting não está desativado!" -ForegroundColor Red
            $allDisabled = $false
            $totalAccess = $false
        }
    }
    if ($allDisabled) {
        Write-Host "[OK] Todas as restrições de Group Policy desativadas" -ForegroundColor Green
    }
} catch {
    Write-Host "[FALHA] Erro ao verificar Group Policy: $_" -ForegroundColor Red
    $totalAccess = $false
}

# Teste 7: Verificar serviços essenciais
Write-Host "`nTeste 7: Verificando serviços essenciais..." -ForegroundColor Yellow
$essentialServices = @("Winmgmt", "Schedule", "RpcSs", "RpcEptMapper", "DcomLaunch", "PlugPlay", "Power", "EventLog")
foreach ($service in $essentialServices) {
    try {
        $svc = Get-Service -Name $service -ErrorAction SilentlyContinue
        if ($svc.Status -eq "Running" -and $svc.StartType -eq "Automatic") {
            Write-Host "[OK] $service" -ForegroundColor Green
        } else {
            Write-Host "[FALHA] $service não está rodando/automático!" -ForegroundColor Red
            $totalAccess = $false
        }
    } catch {
        Write-Host "[FALHA] Erro ao verificar $service!" -ForegroundColor Red
        $totalAccess = $false
    }
}

# Teste 8: Verificar variáveis de ambiente
Write-Host "`nTeste 8: Verificando variáveis de ambiente..." -ForegroundColor Yellow
$envVars = @("CODEX_FULL_ACCESS", "CODEX_AUTONOMOUS", "CODEX_BYPASS_SECURITY", "CODEX_SYSTEM_LEVEL")
foreach ($var in $envVars) {
    $value = [Environment]::GetEnvironmentVariable($var, "Machine")
    if ($value -eq "1") {
        Write-Host "[OK] $var" -ForegroundColor Green
    } else {
        Write-Host "[FALHA] $var não configurado!" -ForegroundColor Red
        $totalAccess = $false
    }
}

# Teste 9: Verificar configurações do kernel
Write-Host "`nTeste 9: Verificando configurações do kernel..." -ForegroundColor Yellow
try {
    $bcdTest = bcdedit /enum | Select-String "testsigning"
    if ($bcdTest -match "Yes") {
        Write-Host "[OK] Test signing habilitado" -ForegroundColor Green
    } else {
        Write-Host "[FALHA] Test signing não habilitado!" -ForegroundColor Red
        $totalAccess = $false
    }
} catch {
    Write-Host "[FALHA] Erro ao verificar configurações do kernel: $_" -ForegroundColor Red
    $totalAccess = $false
}

# Teste 10: Verificar memória e processos
Write-Host "`nTeste 10: Verificando configurações de memória..." -ForegroundColor Yellow
try {
    $pagedPool = (Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" -Name "PagedPoolSize" -ErrorAction SilentlyContinue).PagedPoolSize
    if ($pagedPool -eq 0xFFFFFFFF) {
        Write-Host "[OK] PagedPoolSize configurado" -ForegroundColor Green
    } else {
        Write-Host "[FALHA] PagedPoolSize não configurado!" -ForegroundColor Red
        $totalAccess = $false
    }
} catch {
    Write-Host "[FALHA] Erro ao verificar configurações de memória: $_" -ForegroundColor Red
    $totalAccess = $false
}

# Teste 11: Verificar tarefa agendada
Write-Host "`nTeste 11: Verificando tarefa agendada..." -ForegroundColor Yellow
try {
    $task = Get-ScheduledTask -TaskName "ChatGPT-Codex-Autonomous" -ErrorAction SilentlyContinue
    if ($task) {
        Write-Host "[OK] Tarefa agendada encontrada" -ForegroundColor Green
        if ($task.Principal.UserId -eq "NT AUTHORITY\SYSTEM" -and $task.Principal.RunLevel -eq "Highest") {
            Write-Host "[OK] Tarefa configurada com privilégios máximos" -ForegroundColor Green
        } else {
            Write-Host "[FALHA] Tarefa não tem privilégios máximos!" -ForegroundColor Red
            $totalAccess = $false
        }
    } else {
        Write-Host "[FALHA] Tarefa agendada não encontrada!" -ForegroundColor Red
        $totalAccess = $false
    }
} catch {
    Write-Host "[FALHA] Erro ao verificar tarefa agendada: $_" -ForegroundColor Red
    $totalAccess = $false
}

# Teste 12: Verificar registro do Windows
Write-Host "`nTeste 12: Verificando registro do Windows..." -ForegroundColor Yellow
try {
    $regPath = "HKLM:\SOFTWARE\ChatGPT-Codex\Permissions"
    if (Test-Path $regPath) {
        $fullAccess = (Get-ItemProperty -Path $regPath -Name "FullSystemAccess" -ErrorAction SilentlyContinue).FullSystemAccess
        $autonomous = (Get-ItemProperty -Path $regPath -Name "AutonomousMode" -ErrorAction SilentlyContinue).AutonomousMode
        $bypass = (Get-ItemProperty -Path $regPath -Name "BypassRestrictions" -ErrorAction SilentlyContinue).BypassRestrictions
        
        if ($fullAccess -eq 1 -and $autonomous -eq 1 -and $bypass -eq 1) {
            Write-Host "[OK] Registro configurado para acesso total" -ForegroundColor Green
        } else {
            Write-Host "[FALHA] Registro não configurado completamente!" -ForegroundColor Red
            $totalAccess = $false
        }
    } else {
        Write-Host "[FALHA] Registro não encontrado!" -ForegroundColor Red
        $totalAccess = $false
    }
} catch {
    Write-Host "[FALHA] Erro ao verificar registro: $_" -ForegroundColor Red
    $totalAccess = $false
}

# Teste 13: Verificar política de execução
Write-Host "`nTeste 13: Verificando política de execução..." -ForegroundColor Yellow
$policies = @("LocalMachine", "CurrentUser", "Process")
foreach ($scope in $policies) {
    $policy = Get-ExecutionPolicy -Scope $scope
    if ($policy -eq "Unrestricted") {
        Write-Host "[OK] Política ${scope}: Unrestricted" -ForegroundColor Green
    } else {
        Write-Host "[FALHA] Política ${scope}: $policy!" -ForegroundColor Red
        $totalAccess = $false
    }
}

# Teste 14: Tentativa de acesso crítico
Write-Host "`nTeste 14: Testando acesso crítico..." -ForegroundColor Yellow
try {
    # Tentar criar arquivo em System32
    $testFile = "C:\Windows\System32\codex_test_access.txt"
    "CODEX ACCESS TEST" | Out-File -FilePath $testFile -ErrorAction Stop
    if (Test-Path $testFile) {
        Write-Host "[OK] Escrita em System32 permitida" -ForegroundColor Green
        Remove-Item $testFile -Force
    } else {
        Write-Host "[FALHA] Sem permissão para escrever em System32!" -ForegroundColor Red
        $totalAccess = $false
    }
} catch {
    Write-Host "[FALHA] Erro ao testar acesso crítico: $_" -ForegroundColor Red
    $totalAccess = $false
}

# Resultado final
Write-Host "`n=== RESULTADO FINAL ===" -ForegroundColor Red
if ($totalAccess) {
    Write-Host "✅ ACESSO TOTAL CONFIGURADO COM SUCESSO!" -ForegroundColor Green
    Write-Host "O ChatGPT CODEX tem acesso COMPLETO e irrestrito ao sistema." -ForegroundColor Green
    Write-Host "Pode executar QUALQUER operação sem limitações." -ForegroundColor Green
} else {
    Write-Host "❌ ACESSO TOTAL NÃO CONFIGURADO!" -ForegroundColor Red
    Write-Host "Existem falhas críticas que impedem o acesso total." -ForegroundColor Red
    Write-Host "Verifique os itens marcados como [FALHA]." -ForegroundColor Red
}

Write-Host "`nPressione qualquer tecla para sair..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
