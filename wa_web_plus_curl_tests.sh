#!/usr/bin/env bash
set -euo pipefail

# Required env vars:
# INCOMING_API_URL, AUTH_HEADER_NAME, AUTH_TOKEN
# Optional env vars:
# TARGET_PHONE, MEDIA_URL, LABEL_NAME, WORKFLOW_NAME

: "${INCOMING_API_URL:?Set INCOMING_API_URL}"
: "${AUTH_HEADER_NAME:?Set AUTH_HEADER_NAME}"
: "${AUTH_TOKEN:?Set AUTH_TOKEN}"

TARGET_PHONE="${TARGET_PHONE:-905366365288}"
MEDIA_URL="${MEDIA_URL:-https://example.com/image.jpg}"
LABEL_NAME="${LABEL_NAME:-API-Test}"
WORKFLOW_NAME="${WORKFLOW_NAME:-Refund Workflow}"

ACTION="${1:-text}"

send() {
  local payload="$1"
  curl -i -X POST "$INCOMING_API_URL" \
    -H "Content-Type: application/json" \
    -H "$AUTH_HEADER_NAME: $AUTH_TOKEN" \
    --data "$payload"
}

case "$ACTION" in
  text)
    send "{
      \"action\": \"send-message\",
      \"type\": \"text\",
      \"content\": \"Webhook test from bash curl\",
      \"phone\": \"$TARGET_PHONE\"
    }"
    ;;
  media)
    send "{
      \"action\": \"send-message\",
      \"type\": \"media\",
      \"content\": \"Media test from bash curl\",
      \"phone\": \"$TARGET_PHONE\",
      \"attachments\": [\"$MEDIA_URL\"]
    }"
    ;;
  label)
    send "{
      \"action\": \"label-chat\",
      \"label\": \"$LABEL_NAME\",
      \"phone\": \"$TARGET_PHONE\"
    }"
    ;;
  workflow)
    send "{
      \"action\": \"run-workflow\",
      \"workflow\": \"$WORKFLOW_NAME\",
      \"phone\": \"$TARGET_PHONE\"
    }"
    ;;
  *)
    echo "Usage: $0 [text|media|label|workflow]" >&2
    exit 1
    ;;
esac

