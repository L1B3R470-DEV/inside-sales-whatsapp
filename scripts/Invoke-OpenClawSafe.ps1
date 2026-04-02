param(
  [Parameter(Mandatory=$true)]
  [string[]]$CliArgs,
  [string]$WorkingDirectory = 'C:\Users\User\.openclaw\workspace-integration',
  [string]$StdoutPath = '',
  [string]$StderrPath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Quote-WindowsArg {
  param([string]$Value)
  if ($null -eq $Value) { return '""' }
  if ($Value -eq '') { return '""' }
  if ($Value -notmatch '[\s"]') { return $Value }
  $escaped = $Value -replace '(\\*)"', '$1$1\"'
  $escaped = $escaped -replace '(\\+)$', '$1$1'
  return '"' + $escaped + '"'
}

$node = (Get-Command node.exe | Select-Object -First 1 -ExpandProperty Source)
$openclawCmd = (Get-Command openclaw.cmd | Select-Object -First 1 -ExpandProperty Source)
$openclawBin = Split-Path -Parent $openclawCmd
$openclawJs = Join-Path $openclawBin 'node_modules\openclaw\dist\index.js'
if (-not (Test-Path $openclawJs)) {
  throw "OpenClaw entrypoint not found at $openclawJs"
}

$allArgs = @($openclawJs) + $CliArgs
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $node
$psi.Arguments = (($allArgs | ForEach-Object { Quote-WindowsArg $_ }) -join ' ')
$psi.WorkingDirectory = $WorkingDirectory
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true

$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
$null = $p.Start()
$stdout = $p.StandardOutput.ReadToEnd()
$stderr = $p.StandardError.ReadToEnd()
$p.WaitForExit()

if ($StdoutPath) { Set-Content -LiteralPath $StdoutPath -Value $stdout -Encoding UTF8 }
if ($StderrPath) { Set-Content -LiteralPath $StderrPath -Value $stderr -Encoding UTF8 }

[pscustomobject]@{
  fileName = $psi.FileName
  entrypoint = $openclawJs
  workingDirectory = $WorkingDirectory
  exitCode = $p.ExitCode
  stdoutLength = $stdout.Length
  stderrLength = $stderr.Length
  stdoutPath = $StdoutPath
  stderrPath = $StderrPath
}
