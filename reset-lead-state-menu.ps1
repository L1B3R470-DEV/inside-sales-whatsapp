param(
  [string]$ProjectDir = "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES",
  [string]$RuntimeRoot = "C:\AUTOMACAO",
  [string]$WorkflowId = "zN3heKJVLO8w4dG6"
)

$resetScript = Join-Path $ProjectDir "reset-lead-state.ps1"

if (-not (Test-Path $resetScript)) {
  Write-Host ""
  Write-Host "Arquivo nao encontrado:"
  Write-Host $resetScript
  exit 1
}

function Normalize-Number {
  param([string]$Value)
  return (($Value -replace '\D', '').Trim())
}

function Ask-YesNo {
  param(
    [string]$Prompt,
    [string]$Default = "N"
  )

  while ($true) {
    $suffix = if ($Default -eq "S") { "[S/n]" } else { "[s/N]" }
    $answer = Read-Host "$Prompt $suffix"
    if ([string]::IsNullOrWhiteSpace($answer)) {
      $answer = $Default
    }
    $answer = $answer.Trim().ToUpperInvariant()
    if ($answer -in @("S", "N")) {
      return $answer
    }
    Write-Host "Digite apenas S ou N."
  }
}

Write-Host ""
Write-Host "==============================================="
Write-Host " Reset de Lead | WhatsApp B2B SDR"
Write-Host "==============================================="
Write-Host ""

$rawNumber = Read-Host "Cole o numero do lead/contato"
$number = Normalize-Number $rawNumber

if ([string]::IsNullOrWhiteSpace($number)) {
  Write-Host ""
  Write-Host "Numero invalido."
  exit 1
}

Write-Host ""
Write-Host "Numero normalizado: $number"
Write-Host ""

$dryRunChoice = Ask-YesNo -Prompt "Deseja executar primeiro em modo simulacao" -Default "S"
$backupChoice = Ask-YesNo -Prompt "Deseja gerar backup antes da limpeza" -Default "S"
$restartChoice = Ask-YesNo -Prompt "Deseja reiniciar n8n e Evolution ao final" -Default "S"

Write-Host ""
Write-Host "Resumo:"
Write-Host " - Numero: $number"
Write-Host " - Simulacao: $dryRunChoice"
Write-Host " - Backup: $backupChoice"
Write-Host " - Restart: $restartChoice"
Write-Host ""

$confirm = Ask-YesNo -Prompt "Confirmar execucao" -Default "N"
if ($confirm -ne "S") {
  Write-Host ""
  Write-Host "Operacao cancelada."
  exit 0
}

$argsList = @(
  "-ExecutionPolicy", "Bypass",
  "-File", $resetScript,
  "-Number", $number,
  "-ProjectDir", $ProjectDir,
  "-RuntimeRoot", $RuntimeRoot,
  "-WorkflowId", $WorkflowId
)

if ($dryRunChoice -eq "S") {
  $argsList += "-DryRun"
}
if ($backupChoice -ne "S") {
  $argsList += "-SkipBackup"
}
if ($restartChoice -ne "S") {
  $argsList += "-SkipRestart"
}

Write-Host ""
Write-Host "Executando..."
Write-Host ""

& powershell.exe @argsList

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
  Write-Host "Processo concluido."
} else {
  Write-Host "Processo finalizado com codigo $exitCode."
}

exit $exitCode
