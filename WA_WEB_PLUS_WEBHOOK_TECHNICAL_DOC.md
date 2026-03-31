# WA Web Plus Webhooks and API Technical Guide

Last verified: March 11, 2026  
Primary reference: WA Web Plus Help article published March 1, 2026

## 1. Scope

This guide covers:

- Incoming Webhooks (REST API): your system calls WA Web Plus to execute actions in WhatsApp.
- Outgoing Webhooks: WA Web Plus calls your endpoint with event data.
- Setup checklists.
- Troubleshooting checklist and error isolation flow.
- Reusable `curl` test commands.

## 2. Prerequisites

- Active WA Web Plus extension with plan/features that include webhooks.
- Logged-in WhatsApp Web session.
- Browser tab with WhatsApp Web open for webhook execution (WA Web Plus requirement).
- For incoming API tests:
  - Incoming API URL from WA Web Plus UI.
  - Authorization token from WA Web Plus UI.
  - Header name expected by WA Web Plus for that token (if UI specifies a custom name, use it).
- For outgoing webhook tests:
  - Public HTTPS endpoint you control (or a temporary endpoint like `webhook.site`).

## 3. Configuration Values

Set these placeholders before running commands:

```bash
# Replace with values from WA Web Plus Webhooks/API settings
INCOMING_API_URL="https://<from-wa-web-plus-ui>"
AUTH_HEADER_NAME="Authorization"
AUTH_TOKEN="<from-wa-web-plus-ui>"
TARGET_PHONE="905366365288"
TARGET_GROUP="120363020166629872@g.us"
```

If WA Web Plus explicitly gives a token format, use that exact format (for example `Bearer <token>` if documented in your UI).

## 4. Setup Checklist

### 4.1 Incoming Webhooks (REST API)

- [ ] Open WA Web Plus webhooks/API settings.
- [ ] Copy incoming API URL.
- [ ] Copy authorization token.
- [ ] Confirm required auth header key/value format.
- [ ] Confirm WhatsApp Web is connected in the same browser profile.
- [ ] Send a text-message test (section 6.1).
- [ ] Validate message arrives in target chat.
- [ ] Run at least one non-message action test (`label-chat` or `run-workflow`).

### 4.2 Outgoing Webhooks

- [ ] Create/choose target HTTPS endpoint.
- [ ] In WA Web Plus, add outgoing webhook endpoint URL.
- [ ] Choose HTTP method (`POST` recommended).
- [ ] Add custom headers (JSON) if needed.
- [ ] Configure payload template using WA event variables (`@` picker in UI).
- [ ] Trigger a known event (for example inbound message or workflow).
- [ ] Confirm request reaches endpoint and payload fields map correctly.
- [ ] Confirm retries/alerting behavior on endpoint failures.

## 5. Incoming API Actions and Payloads

Supported examples documented by WA Web Plus:

### 5.1 Send text message

```json
{
  "action": "send-message",
  "type": "text",
  "content": "Welcome to WA Web Plus",
  "phone": "905366365288"
}
```

### 5.2 Send media message

```json
{
  "action": "send-message",
  "type": "media",
  "content": "Welcome to WA Web Plus",
  "phone": "905366365288",
  "attachments": ["https://example.com/image.jpg"]
}
```

### 5.3 Send saved template

```json
{
  "action": "send-template",
  "template": "Welcome Message",
  "phone": "120363020166629872@g.us"
}
```

Note: use `@g.us` suffix for group targets.

### 5.4 Label a chat

```json
{
  "action": "label-chat",
  "label": "Interested Customer",
  "phone": "905366365288"
}
```

### 5.5 Remove a label

```json
{
  "action": "unlabel-chat",
  "label": "Unsubscribed",
  "phone": "905366365288"
}
```

### 5.6 Block a contact

```json
{
  "action": "block-chat",
  "phone": "905366365288"
}
```

### 5.7 Archive a chat

```json
{
  "action": "archive-chat",
  "phone": "905366365288"
}
```

### 5.8 Run broadcast campaign

```json
{
  "action": "run-broadcast",
  "broadcast": "Sunday Scheduled Campaign"
}
```

### 5.9 Trigger Smart Reply workflow

```json
{
  "action": "run-workflow",
  "workflow": "Refund Workflow",
  "phone": "905366365288"
}
```

## 6. `curl` Test Scripts

### 6.1 Linux/macOS (bash)

### 6.1.1 Health/auth check with text message

```bash
curl -i -X POST "$INCOMING_API_URL" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER_NAME: $AUTH_TOKEN" \
  -d "{
    \"action\": \"send-message\",
    \"type\": \"text\",
    \"content\": \"Webhook test from curl\",
    \"phone\": \"$TARGET_PHONE\"
  }"
```

### 6.1.2 Media message test

```bash
curl -i -X POST "$INCOMING_API_URL" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER_NAME: $AUTH_TOKEN" \
  -d "{
    \"action\": \"send-message\",
    \"type\": \"media\",
    \"content\": \"Media test from curl\",
    \"phone\": \"$TARGET_PHONE\",
    \"attachments\": [\"https://example.com/image.jpg\"]
  }"
```

### 6.1.3 Label test

```bash
curl -i -X POST "$INCOMING_API_URL" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER_NAME: $AUTH_TOKEN" \
  -d "{
    \"action\": \"label-chat\",
    \"label\": \"API-Test\",
    \"phone\": \"$TARGET_PHONE\"
  }"
```

### 6.1.4 Run workflow test

```bash
curl -i -X POST "$INCOMING_API_URL" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER_NAME: $AUTH_TOKEN" \
  -d "{
    \"action\": \"run-workflow\",
    \"workflow\": \"Refund Workflow\",
    \"phone\": \"$TARGET_PHONE\"
  }"
```

### 6.2 Windows PowerShell

PowerShell equivalent using `curl.exe`:

```powershell
$INCOMING_API_URL = "https://<from-wa-web-plus-ui>"
$AUTH_HEADER_NAME = "Authorization"
$AUTH_TOKEN = "<from-wa-web-plus-ui>"
$TARGET_PHONE = "905366365288"

$json = @"
{
  "action": "send-message",
  "type": "text",
  "content": "Webhook test from curl.exe",
  "phone": "$TARGET_PHONE"
}
"@

curl.exe -i -X POST $INCOMING_API_URL `
  -H "Content-Type: application/json" `
  -H "$AUTH_HEADER_NAME`: $AUTH_TOKEN" `
  --data $json
```

### 6.3 Outgoing Webhook Receiver Simulation

Use this to validate your own receiver logic before connecting WA Web Plus:

```bash
curl -i -X POST "https://your-endpoint.example/webhooks/wa-web-plus" \
  -H "Content-Type: application/json" \
  -d '{
    "m_id": "test-001",
    "m_type": "chat",
    "m_timestamp": 1760000000,
    "m_user": "905366365288",
    "m_content": "hello from simulated outgoing webhook",
    "m_cname": "Test Contact",
    "m_uname": "Test WA Name",
    "m_gname": ""
  }'
```

## 7. Outgoing Variables (Current Docs)

`m_id`, `m_type`, `m_datetime`, `m_timestamp`, `m_user`, `m_phone`, `m_content`, `m_text`, `m_cname`, `m_uname`, `m_gname`, `m_gid`, `m_platform`, `w_id`, `c_labels`, `c_image`, `m_location`, `m_order`.

## 8. Troubleshooting

### 8.1 Quick Triage

1. Verify WA Web Plus is enabled and WhatsApp Web is open in that same browser profile.
2. Re-run minimal text-message `curl` test from section 6.1.1.
3. Check endpoint/auth values copied from WA Web Plus settings.
4. Confirm phone/group format (`@g.us` for groups).
5. Check payload action spelling (`send-message`, `run-workflow`, etc).
6. Validate your endpoint is reachable over HTTPS for outgoing mode.

### 8.2 Symptom-to-Fix Table

| Symptom | Likely Cause | Fix |
|---|---|---|
| `401/403` from incoming API | Wrong token/header format | Re-copy token, verify header name/value format in WA UI |
| `400` / invalid action | Wrong JSON schema or action string | Start from section 5 payloads exactly, then customize |
| `200` response but no WhatsApp action | WhatsApp Web not open/connected | Reconnect WhatsApp Web and keep browser session active |
| Outgoing webhook not received | Wrong URL, method mismatch, endpoint blocked | Use temporary endpoint (`webhook.site`) and test with `POST` first |
| Group action fails | Group ID missing `@g.us` suffix | Use full group id with `@g.us` |
| Intermittent failures | Browser/session idle or disconnected | Keep session active, monitor reconnect events |

### 8.3 Validation Order (Recommended)

1. Text message (`send-message`, type `text`)
2. Label operation (`label-chat`)
3. Workflow operation (`run-workflow`)
4. Outgoing event delivery to your endpoint
5. Advanced payload customizations and headers

## 9. Legacy Note: Older Firebase-Based Incoming Webhook Setup

Older WA Web Plus help content documented incoming writes through Firebase Realtime Database (`https://{db}.firebaseio.com/{child}.json`).

If you are maintaining an older setup:

- Keep it isolated from your new REST API configuration.
- Plan migration to current REST API mode for simpler auth and testing.
- Re-test all automations after migration.

## 10. Sources

- WA Web Plus Help (current): https://www.wawplus.com/en/help/webhooks-and-api
- WA Web Plus older setup page: https://wawplus.com/help/how-to-setup-a-webhook
- WA Web Plus older webhooks page: https://wawplus.com/help/webhooks
- WA Web Plus changelog: https://www.wawplus.com/en/changelog

## 11. Local Test Scripts in This Project

- Bash script: `wa_web_plus_curl_tests.sh`
- PowerShell script: `wa_web_plus_curl_tests.ps1`

Usage examples:

```bash
export INCOMING_API_URL="https://<from-wa-web-plus-ui>"
export AUTH_HEADER_NAME="Authorization"
export AUTH_TOKEN="<from-wa-web-plus-ui>"
export TARGET_PHONE="905366365288"
./wa_web_plus_curl_tests.sh text
./wa_web_plus_curl_tests.sh label
```

```powershell
$env:INCOMING_API_URL = "https://<from-wa-web-plus-ui>"
$env:AUTH_HEADER_NAME = "Authorization"
$env:AUTH_TOKEN = "<from-wa-web-plus-ui>"
$env:TARGET_PHONE = "905366365288"
.\wa_web_plus_curl_tests.ps1 -Action text
.\wa_web_plus_curl_tests.ps1 -Action workflow
```
