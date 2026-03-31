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

Write-Host ''
Write-Host 'Reparo DPAPI para o perfil do Vivaldi' -ForegroundColor Cyan
Write-Host 'Use a senha anterior do Windows, a que estava valendo antes da troca feita em 30/03/2026.' -ForegroundColor Yellow
Write-Host ''

if (Get-Process vivaldi -ErrorAction SilentlyContinue) {
    Write-Host 'Feche o Vivaldi antes de continuar.' -ForegroundColor Yellow
    exit 1
}

$before = Test-VivaldiKey
Write-Host ("Estado atual da chave do Vivaldi: " + ($(if ($before) { 'OK' } else { 'FALHA' })))

$secureOldPassword = Read-Host 'Digite a senha antiga do Windows' -AsSecureString
$oldPassword = ConvertTo-PlainText -SecureString $secureOldPassword

try {
    [uint32]$success = 0
    [uint32]$failure = 0
    $ok = [DpapiNative]::CryptUpdateProtectedState(
        [IntPtr]::Zero,
        $oldPassword,
        0,
        [ref]$success,
        [ref]$failure
    )

    if (-not $ok) {
        $win32 = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        throw "CryptUpdateProtectedState falhou com Win32=$win32."
    }

    $after = Test-VivaldiKey
    Write-Host ''
    Write-Host "Master keys migradas com sucesso: $success"
    Write-Host "Master keys que nao puderam ser migradas: $failure"
    Write-Host ("Estado final da chave do Vivaldi: " + ($(if ($after) { 'OK' } else { 'FALHA' })))

    if ($after) {
        Write-Host ''
        Write-Host 'A chave do Vivaldi voltou a abrir. Agora voce pode iniciar o navegador.' -ForegroundColor Green
    }
    else {
        Write-Host ''
        Write-Host 'A migracao executou, mas a chave do Vivaldi ainda nao abriu.' -ForegroundColor Yellow
        Write-Host 'Isso costuma indicar senha antiga incorreta ou um reset de senha que rompeu o historico DPAPI.' -ForegroundColor Yellow
    }
}
finally {
    if ($oldPassword) {
        $oldPassword = $null
    }
}
