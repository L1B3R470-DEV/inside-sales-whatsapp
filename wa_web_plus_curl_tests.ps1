param(
  [ValidateSet("text", "media", "label", "workflow")]
  [string]$Action = "text"
)

$IncomingApiUrl = $env:INCOMING_API_URL
$AuthHeaderName = $env:AUTH_HEADER_NAME
$AuthToken = $env:AUTH_TOKEN
$TargetPhone = if ($env:TARGET_PHONE) { $env:TARGET_PHONE } else { "905366365288" }
$MediaUrl = if ($env:MEDIA_URL) { $env:MEDIA_URL } else { "https://example.com/image.jpg" }
$LabelName = if ($env:LABEL_NAME) { $env:LABEL_NAME } else { "API-Test" }
$WorkflowName = if ($env:WORKFLOW_NAME) { $env:WORKFLOW_NAME } else { "Refund Workflow" }

if (-not $IncomingApiUrl) { throw "Set env var INCOMING_API_URL" }
if (-not $AuthHeaderName) { throw "Set env var AUTH_HEADER_NAME" }
if (-not $AuthToken) { throw "Set env var AUTH_TOKEN" }

switch ($Action) {
  "text" {
    $payload = @{
      action = "send-message"
      type = "text"
      content = "Webhook test from PowerShell curl.exe"
      phone = $TargetPhone
    } | ConvertTo-Json
  }
  "media" {
    $payload = @{
      action = "send-message"
      type = "media"
      content = "Media test from PowerShell curl.exe"
      phone = $TargetPhone
      attachments = @($MediaUrl)
    } | ConvertTo-Json
  }
  "label" {
    $payload = @{
      action = "label-chat"
      label = $LabelName
      phone = $TargetPhone
    } | ConvertTo-Json
  }
  "workflow" {
    $payload = @{
      action = "run-workflow"
      workflow = $WorkflowName
      phone = $TargetPhone
    } | ConvertTo-Json
  }
}

curl.exe -i -X POST $IncomingApiUrl `
  -H "Content-Type: application/json" `
  -H "$AuthHeaderName`: $AuthToken" `
  --data $payload

