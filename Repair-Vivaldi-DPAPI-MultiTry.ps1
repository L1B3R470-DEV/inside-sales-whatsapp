$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Security

$source = @"
using System;
using System.Runtime.InteropServices;

public static class DpapiNative
{
    [DllImport("Crypt32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool CryptUpdateProtectedState(
        IntPtr pOldSid,
        string pwszOldPassword,
        uint dwFlags,
        out uint pdwSuccessCount,
        out uint pdwFailureCount);
}
"@

Add-Type -TypeDefinition $source

function ConvertTo-PlainText {
    param(
        [Parameter(Mandatory = $true)]
        [System.Security.SecureString]$SecureString
    )

    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureString)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringUni($bstr)
    }
    finally {
        if ($bstr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }
}

function Test-VivaldiKey {
    $localState = Join-Path $env:LOCALAPPDATA 'Vivaldi\User Data\Local State'
    if (-not (Test-Path -LiteralPath $localState)) {
        return $false
    }

    $json = Get-Content -LiteralPath $localState -Raw | ConvertFrom-Json
    $encryptedKey = $json.os_crypt.encrypted_key
    if (-not $encryptedKey) {
        return $false
    }

    $raw = [Convert]::FromBase64String($encryptedKey)
    if ($raw.Length -lt 6) {
        return $false
    }

    $prefix = [System.Text.Encoding]::ASCII.GetString($raw, 0, 5)
    if ($prefix -ne 'DPAPI') {
        return $false
    }

    $payload = [byte[]]($raw[5..($raw.Length - 1)])
    try {
        [void][System.Security.Cryptography.ProtectedData]::Unprotect(
            $payload,
            $null,
            [System.Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        return $true
    }
    catch {
        return $false
    }
}

function Invoke-DpapiMigrationAttempt {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Password
    )

    [uint32]$success = 0
    [uint32]$failure = 0
    $ok = [DpapiNative]::CryptUpdateProtectedState(
        [IntPtr]::Zero,
        $Password,
        0,
        [ref]$success,
        [ref]$failure
    )

    if (-not $ok) {
        $win32 = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        throw "CryptUpdateProtectedState falhou com Win32=$win32."
    }

    return [PSCustomObject]@{
        Success = $success
        Failure = $failure
        VivaldiKeyOk = (Test-VivaldiKey)
    }
}

Write-Host ''
Write-Host 'Reparo DPAPI do Vivaldi - varias tentativas' -ForegroundColor Cyan
Write-Host 'Tente senhas antigas do Windows, comecando pela que voce usava por volta de 28/11/2025.' -ForegroundColor Yellow
Write-Host ''

if (Get-Process vivaldi -ErrorAction SilentlyContinue) {
    Write-Host 'Feche o Vivaldi antes de continuar.' -ForegroundColor Yellow
    exit 1
}

if (Test-VivaldiKey) {
    Write-Host 'A chave do Vivaldi ja esta abrindo. Nao ha nada para migrar.' -ForegroundColor Green
    exit 0
}

$attempt = 1
while ($true) {
    Write-Host ''
    Write-Host "Tentativa $attempt" -ForegroundColor Cyan
    $secureOldPassword = Read-Host 'Digite uma senha antiga do Windows' -AsSecureString
    $oldPassword = ConvertTo-PlainText -SecureString $secureOldPassword

    try {
        $result = Invoke-DpapiMigrationAttempt -Password $oldPassword
        Write-Host "Master keys migradas com sucesso: $($result.Success)"
        Write-Host "Master keys que nao puderam ser migradas: $($result.Failure)"
        Write-Host ("Estado final da chave do Vivaldi: " + ($(if ($result.VivaldiKeyOk) { 'OK' } else { 'FALHA' })))

        if ($result.VivaldiKeyOk) {
            Write-Host ''
            Write-Host 'A chave do Vivaldi voltou a abrir. Pode iniciar o navegador.' -ForegroundColor Green
            break
        }
    }
    catch {
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
    finally {
        if ($oldPassword) {
            $oldPassword = $null
        }
    }

    $retry = Read-Host 'Tentar outra senha? (S/N)'
    if ($retry -notmatch '^[SsYy]$') {
        break
    }

    $attempt += 1
}
