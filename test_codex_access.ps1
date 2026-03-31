# Script de teste para verificar acesso autônomo do ChatGPT CODEX

Write-Host "=== TESTANDO ACESSO AUTÔNOMO DO CHATGPT CODEX ===" -ForegroundColor Cyan

$codexPath = "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64\bin\windows-x86_64\codex.exe"

# Teste 1: Verificar se o executável existe e tem permissões
Write-Host "Teste 1: Verificando executável..." -ForegroundColor Yellow
if (Test-Path $codexPath) {
    Write-Host "[OK] Executável encontrado" -ForegroundColor Green
    
    $acl = Get-Acl $codexPath
    $access = $acl.Access | Where-Object { $_.FileSystemRights -eq "FullControl" -and $_.AccessControlType -eq "Allow" }
    
    if ($access) {
        Write-Host "[OK] Permissões de FullControl configuradas" -ForegroundColor Green
    } else {
        Write-Host "[ERRO] Permissões não configuradas corretamente" -ForegroundColor Red
    }
} else {
    Write-Host "[ERRO] Executável não encontrado" -ForegroundColor Red
}

# Teste 2: Verificar privilégios do usuário atual
Write-Host "`nTeste 2: Verificando privilégios..." -ForegroundColor Yellow
$privs = whoami /priv
$requiredPrivs = @("SeDebugPrivilege", "SeTakeOwnershipPrivilege", "SeBackupPrivilege", "SeRestorePrivilege")

foreach ($priv in $requiredPrivs) {
    if ($privs -match $priv -and $privs -match "Ativada") {
        Write-Host "[OK] $priv está ativado" -ForegroundColor Green
    } else {
        Write-Host "[AVISO] $priv não está ativado" -ForegroundColor Yellow
    }
}

# Teste 3: Verificar configurações do Windows Defender
Write-Host "`nTeste 3: Verificando Windows Defender..." -ForegroundColor Yellow
try {
    $exclusions = Get-MpPreference
    if ($exclusions.ExclusionPath -contains "C:\Users\murdo\.windsurf\extensions\openai.chatgpt-26.318.11754-win32-x64") {
        Write-Host "[OK] Caminho excluído do Windows Defender" -ForegroundColor Green
    } else {
        Write-Host "[AVISO] Caminho não excluído do Windows Defender" -ForegroundColor Yellow
    }
    
    if ($exclusions.ExclusionProcess -contains "codex.exe") {
        Write-Host "[OK] Processo excluído do Windows Defender" -ForegroundColor Green
    } else {
        Write-Host "[AVISO] Processo não excluído do Windows Defender" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERRO] Não foi possível verificar Windows Defender: $_" -ForegroundColor Red
}

# Teste 4: Verificar UAC
Write-Host "`nTeste 4: Verificando UAC..." -ForegroundColor Yellow
try {
    $uacEnabled = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA").EnableLUA
    if ($uacEnabled -eq 0) {
        Write-Host "[OK] UAC desativado para operações autônomas" -ForegroundColor Green
    } else {
        Write-Host "[AVISO] UAC ainda está ativo" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERRO] Não foi possível verificar UAC: $_" -ForegroundColor Red
}

# Teste 5: Verificar política de execução
Write-Host "`nTeste 5: Verificando política de execução..." -ForegroundColor Yellow
$policy = Get-ExecutionPolicy -Scope LocalMachine
if ($policy -eq "Unrestricted") {
    Write-Host "[OK] Política de execução irrestrita" -ForegroundColor Green
} else {
    Write-Host "[AVISO] Política de execução: $policy" -ForegroundColor Yellow
}

# Teste 6: Verificar tarefa agendada
Write-Host "`nTeste 6: Verificando tarefa agendada..." -ForegroundColor Yellow
try {
    $task = Get-ScheduledTask -TaskName "ChatGPT-Codex-Autonomous" -ErrorAction SilentlyContinue
    if ($task) {
        Write-Host "[OK] Tarefa agendada encontrada" -ForegroundColor Green
        Write-Host "    Estado: $($task.State)" -ForegroundColor White
        Write-Host "    Usuário: $($task.Principal.UserId)" -ForegroundColor White
    } else {
        Write-Host "[AVISO] Tarefa agendada não encontrada" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERRO] Não foi possível verificar tarefa agendada: $_" -ForegroundColor Red
}

# Teste 7: Verificar registro do Windows
Write-Host "`nTeste 7: Verificando registro do Windows..." -ForegroundColor Yellow
try {
    $regPath = "HKLM:\SOFTWARE\ChatGPT-Codex\Permissions"
    if (Test-Path $regPath) {
        $fullAccess = (Get-ItemProperty -Path $regPath -Name "FullSystemAccess" -ErrorAction SilentlyContinue).FullSystemAccess
        $autonomous = (Get-ItemProperty -Path $regPath -Name "AutonomousMode" -ErrorAction SilentlyContinue).AutonomousMode
        $bypass = (Get-ItemProperty -Path $regPath -Name "BypassRestrictions" -ErrorAction SilentlyContinue).BypassRestrictions
        
        if ($fullAccess -eq 1 -and $autonomous -eq 1 -and $bypass -eq 1) {
            Write-Host "[OK] Registro configurado para acesso total" -ForegroundColor Green
        } else {
            Write-Host "[AVISO] Registro não configurado completamente" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[AVISO] Registro não encontrado" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERRO] Não foi possível verificar registro: $_" -ForegroundColor Red
}

# Teste 8: Tentar executar o Codex em modo autônomo
Write-Host "`nTeste 8: Testando execução do Codex..." -ForegroundColor Yellow
try {
    $process = Start-Process -FilePath $codexPath -ArgumentList "--help" -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2
    
    if (!$process.HasExited) {
        $process.Kill()
        Write-Host "[OK] Codex pode ser executado" -ForegroundColor Green
    } else {
        Write-Host "[AVISO] Codex executou e saiu rapidamente (pode ser normal para --help)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERRO] Não foi possível executar Codex: $_" -ForegroundColor Red
}

Write-Host "`n=== TESTE CONCLUÍDO ===" -ForegroundColor Cyan
Write-Host "Se todos os testes mostraram [OK], o acesso autônomo está configurado!" -ForegroundColor Green
Write-Head "Se houver avisos ou erros, verifique a configuração correspondente." -ForegroundColor Yellow
