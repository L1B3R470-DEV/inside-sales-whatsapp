param(
  [int]$EveryMinutes = 15
)

$ErrorActionPreference = 'Stop'

if ($EveryMinutes -lt 5) {
  throw 'EveryMinutes deve ser >= 5'
}

$taskName = 'CRM_CYCLE_N8N'
$script = 'C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\run-crm-cycle-with-sheets.ps1'
$cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$script`""

# SYSTEM account keeps the cycle running even when no user session is active.
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
$proc = Start-Process -FilePath 'schtasks.exe' -ArgumentList $args -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -ne 0) {
  throw "Falha ao criar tarefa agendada $taskName"
}

Write-Host "Tarefa $taskName criada com sucesso (intervalo: $EveryMinutes min)."

