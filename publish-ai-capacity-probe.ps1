param(
  [Parameter(Mandatory = $true)]
  [string]$AgentId,
  [Parameter(Mandatory = $true)]
  [string]$Status,
  [string]$Reason = "manual_probe",
  [string]$BridgeRoot = "C:\AUTOMACAO\cowork\claude_bridge",
  [string]$MetadataJson = "{}"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BridgeRoot)) {
  New-Item -ItemType Directory -Path $BridgeRoot | Out-Null
}

$metadata = @{}
if ($MetadataJson) {
  try {
    $parsed = $MetadataJson | ConvertFrom-Json
    if ($null -ne $parsed) {
      $metadata = @{}
      foreach ($prop in $parsed.PSObject.Properties) {
        $metadata[$prop.Name] = $prop.Value
      }
    }
  } catch {
    throw "MetadataJson invalido: $MetadataJson"
  }
}

$available = $Status -in @("available", "recovered", "degraded")
$payload = @{
  agent_id = $AgentId
  status = $Status
  available = $available
  reason = $Reason
  created_at = (Get-Date).ToString("o")
  metadata = $metadata
}

$target = Join-Path $BridgeRoot ("{0}_probe.json" -f $AgentId)
($payload | ConvertTo-Json -Depth 8) | Set-Content -Path $target -Encoding UTF8
Write-Output "probe=$target"
