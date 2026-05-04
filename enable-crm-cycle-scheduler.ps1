param(
  [int]$EveryMinutes = 15
)

$ErrorActionPreference = 'Stop'

if ($EveryMinutes -lt 5) {
  throw 'EveryMinutes deve ser >= 5'
}

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskName = 'CRM_CYCLE_N8N'
$script = Join-Path $ProjectDir 'run-crm-cycle-with-sheets.ps1'

if (-not (Test-Path -LiteralPath $script)) {
  throw "Script do ciclo nao encontrado: $script"
}

$cmd = "powershell.exe -WindowStyle Hidden -NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$script`""

# SYSTEM mantem o ciclo rodando mesmo sem sessao interativa do usuario.
$args = @(
  '/Create',
  '/TN', $taskName,
  '/TR', $cmd,
  '/SC', 'MINUTE',
  '/MO', $EveryMinutes,
  '/RU', 'SYSTEM',
  '/RL', 'HIGHEST',
  '/F'
)
$proc = Start-Process -FilePath 'schtasks.exe' -ArgumentList $args -WindowStyle Hidden -Wait -PassThru
if ($proc.ExitCode -ne 0) {
  throw "Falha ao criar tarefa agendada $taskName"
}

Write-Host "Tarefa $taskName criada com sucesso (intervalo: $EveryMinutes min; script=$script)."
\n
