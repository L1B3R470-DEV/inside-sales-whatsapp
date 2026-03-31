param(
  [Parameter(Mandatory = $true)]
  [string]$Number,

  [string]$Text = "",
  [string]$Instance = "ATENDIMENTO_VENDAS_CLEAN",
  [string]$SendMode = "text",
  [string]$MediaType = "image",
  [string]$MimeType = "image/jpeg",
  [string]$Media = "",
  [string]$Caption = "",
  [string]$FileName = "",
  [string]$WebhookUrl = "http://localhost:5678/webhook/manual-outbound-send"
)

$payload = @{
  instance = $Instance
  number = $Number
  sendMode = $SendMode
  replyText = $Text
  mediaType = $MediaType
  mimeType = $MimeType
  media = $Media
  caption = $Caption
  fileName = $FileName
}

$json = $payload | ConvertTo-Json -Depth 6
$bytes = [System.Text.Encoding]::UTF8.GetBytes($json)

$response = Invoke-WebRequest `
  -Method POST `
  -Uri $WebhookUrl `
  -ContentType "application/json; charset=utf-8" `
  -Body $bytes

$response.StatusCode
