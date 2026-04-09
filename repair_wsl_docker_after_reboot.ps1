$ErrorActionPreference = 'Stop'

$backupDir = 'C:\Users\User\Desktop\WSL-Backup-2026-04-04'
$ubuntuBackupVhd = Join-Path $backupDir 'Ubuntu-ext4.vhdx'
$ubuntuInstallDir = Join-Path $env:LOCALAPPDATA 'wsl\Ubuntu-restored'
$dockerExe = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
$logPath = Join-Path $backupDir 'repair-after-reboot.log'

function Write-Log {
    param([string]$Message)

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -LiteralPath $logPath -Value "[$timestamp] $Message"
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [int]$TimeoutMs = 30000
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    foreach ($argument in $Arguments) {
        [void]$psi.ArgumentList.Add($argument)
    }
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()

    if (-not $process.WaitForExit($TimeoutMs)) {
        try {
            $process.Kill($true)
        } catch {
        }

        return [PSCustomObject]@{
            TimedOut = $true
            ExitCode = $null
            StdOut = ''
            StdErr = ''
        }
    }

    return [PSCustomObject]@{
        TimedOut = $false
        ExitCode = $process.ExitCode
        StdOut = $process.StandardOutput.ReadToEnd()
        StdErr = $process.StandardError.ReadToEnd()
    }
}

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
"---" | Set-Content -LiteralPath $logPath
Write-Log 'Starting post-reboot WSL and Docker repair.'

if (-not (Test-Path -LiteralPath $ubuntuBackupVhd)) {
    Write-Log "Ubuntu backup VHD not found at $ubuntuBackupVhd"
    exit 1
}

$listResult = Invoke-External -FilePath 'wsl.exe' -Arguments @('-l', '-q') -TimeoutMs 15000
if ($listResult.TimedOut) {
    Write-Log 'wsl -l -q timed out after reboot.'
    exit 1
}

Write-Log "Current distros: $($listResult.StdOut.Trim())"

if ($listResult.ExitCode -ne 0) {
    Write-Log "wsl -l -q failed with exit code $($listResult.ExitCode). stderr: $($listResult.StdErr.Trim())"
    exit 1
}

$distros = $listResult.StdOut -split "`r?`n" | Where-Object { $_.Trim() -ne '' } | ForEach-Object { $_.Trim() }
if ($distros -notcontains 'Ubuntu') {
    New-Item -ItemType Directory -Force -Path $ubuntuInstallDir | Out-Null
    Write-Log "Importing Ubuntu from $ubuntuBackupVhd into $ubuntuInstallDir"

    $importResult = Invoke-External -FilePath 'wsl.exe' -Arguments @('--import', 'Ubuntu', $ubuntuInstallDir, $ubuntuBackupVhd, '--vhd') -TimeoutMs 180000
    if ($importResult.TimedOut -or $importResult.ExitCode -ne 0) {
        Write-Log "Ubuntu import failed. exit=$($importResult.ExitCode) timeout=$($importResult.TimedOut) stderr=$($importResult.StdErr.Trim())"
        exit 1
    }
}

$defaultResult = Invoke-External -FilePath 'wsl.exe' -Arguments @('-s', 'Ubuntu') -TimeoutMs 30000
if ($defaultResult.TimedOut -or $defaultResult.ExitCode -ne 0) {
    Write-Log "Setting Ubuntu as default failed. exit=$($defaultResult.ExitCode) timeout=$($defaultResult.TimedOut) stderr=$($defaultResult.StdErr.Trim())"
    exit 1
}

$smokeResult = Invoke-External -FilePath 'wsl.exe' -Arguments @('-d', 'Ubuntu', '--', 'echo', 'codex-wsl-ok') -TimeoutMs 30000
if ($smokeResult.TimedOut -or $smokeResult.ExitCode -ne 0) {
    Write-Log "Ubuntu smoke test failed. exit=$($smokeResult.ExitCode) timeout=$($smokeResult.TimedOut) stderr=$($smokeResult.StdErr.Trim())"
    exit 1
}
Write-Log "Ubuntu smoke test output: $($smokeResult.StdOut.Trim())"

if (Test-Path -LiteralPath $dockerExe) {
    Write-Log "Starting Docker Desktop from $dockerExe"
    Start-Process -FilePath $dockerExe
    Start-Sleep -Seconds 25

    $dockerResult = Invoke-External -FilePath 'docker.exe' -Arguments @('version') -TimeoutMs 30000
    if ($dockerResult.TimedOut -or $dockerResult.ExitCode -ne 0) {
        Write-Log "docker version failed. exit=$($dockerResult.ExitCode) timeout=$($dockerResult.TimedOut) stderr=$($dockerResult.StdErr.Trim())"
        exit 1
    }

    Write-Log 'Docker Desktop responded successfully.'
} else {
    Write-Log "Docker Desktop executable not found at $dockerExe"
}

Write-Log 'Post-reboot repair completed successfully.'
