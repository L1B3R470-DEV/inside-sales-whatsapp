@echo off
setlocal

echo ==========================================
echo  CORRECAO DE ACESSO GUEST SMB (CLIENTE)
echo ==========================================
echo.

net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo [ERRO] Execute este arquivo como ADMINISTRADOR.
    echo Clique com botao direito ^> Executar como administrador.
    pause
    exit /b 1
)

echo [1/5] Aplicando politica local para permitir guest SMB...
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\LanmanWorkstation" /v AllowInsecureGuestAuth /t REG_DWORD /d 1 /f >nul
reg add "HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" /v AllowInsecureGuestAuth /t REG_DWORD /d 1 /f >nul

echo [2/5] Evitando exigencia de assinatura SMB no cliente...
reg add "HKLM\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" /v RequireSecuritySignature /t REG_DWORD /d 0 /f >nul

echo [3/5] Atualizando politicas...
gpupdate /target:computer /force >nul

echo [4/5] Reiniciando servico de estacao de trabalho...
sc stop LanmanWorkstation >nul 2>&1
sc start LanmanWorkstation >nul 2>&1

echo [5/5] Testando acesso ao compartilhamento...
net use * /delete /y >nul 2>&1
net use "\\DESKTOP-2BIV5RS\INTELIGENCIA_COMERCIAL" "" /user:"" >nul 2>&1

if "%errorlevel%"=="0" (
    echo.
    echo [OK] Acesso sem credencial habilitado com sucesso.
    echo Tente abrir: \\DESKTOP-2BIV5RS\INTELIGENCIA_COMERCIAL
) else (
    echo.
    echo [ATENCAO] Ainda houve bloqueio local.
    echo Se o computador estiver em dominio/corporativo, a politica da empresa pode reverter este ajuste.
    echo Nesse caso, o TI local precisa liberar:
    echo Computer Configuration ^> Administrative Templates ^> Network ^> Lanman Workstation ^> Enable insecure guest logons = Enabled
)

echo.
pause
exit /b 0
