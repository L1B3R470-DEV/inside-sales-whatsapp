import json
import sqlite3

DB = '/data/database.sqlite'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'

with open('/work/normalize-payload.js', 'r', encoding='utf-8') as f:
    normalize_code = f.read()
with open('/work/guardrails.js', 'r', encoding='utf-8') as f:
    guardrails_code = f.read()
with open('/work/extract-reply.js', 'r', encoding='utf-8') as f:
    extract_code = f.read()
with open('/work/build-fallback-reply.js', 'r', encoding='utf-8') as f:
    fallback_code = f.read()

openai_json_body = '''={{ {
  "model": String($node["Guardrails"].json.openAiModel || "gpt-5.4"),
  "store": true,
  "previous_response_id": String($node["Guardrails"].json.previousOpenAiResponseId || "").trim() || undefined,
  "reasoning": {
    "effort": String($node["Guardrails"].json.openAiReasoningEffort || "medium")
  },
  "metadata": {
    "channel": "whatsapp",
    "customer_number": String($node["Guardrails"].json.customerNumber || ""),
    "message_id": String($node["Guardrails"].json.messageId || ""),
    "intent": String($node["Guardrails"].json.detectedIntent || "")
  },
  "input": [
    {
      "role": "system",
      "content": [
        {
          "type": "input_text",
          "text": $node["Guardrails"].json.aiSystemPrompt
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": $node["Guardrails"].json.aiUserPrompt
        }
      ]
    }
  ],
  "max_output_tokens": Number($node["Guardrails"].json.maxOutputTokens || 180)
} }}'''

evolution_send_json_body = '''={{ $json.sendMode === "media"
  ? {
      "number": String($json.number || "").trim(),
      "mediatype": String($json.mediaType || "image"),
      "mimetype": String($json.mimeType || "image/jpeg"),
      "media": String($json.media || "").trim(),
      "caption": String($json.caption || "").trim(),
      "fileName": String($json.fileName || ""),
      "delay": 1200
    }
  : {
      "number": String($json.number || "").trim(),
      "text": String($json.replyText || ""),
      "delay": 1200,
      "linkPreview": false
    } }}'''


def patch_nodes_json(nodes_text: str):
    nodes = json.loads(nodes_text)
    changed = False

    for node in nodes:
        name = node.get('name')
        ntype = node.get('type')
        params = node.setdefault('parameters', {})

        if name == 'Normalize Payload' and ntype == 'n8n-nodes-base.code':
            if params.get('language') != 'javaScript':
                params['language'] = 'javaScript'
                changed = True
            if params.get('jsCode') != normalize_code:
                params['jsCode'] = normalize_code
                changed = True

        if name == 'Webhook Evolution' and ntype == 'n8n-nodes-base.webhook':
            if params.get('responseMode') != 'onReceived':
                params['responseMode'] = 'onReceived'
                changed = True

        if name == 'Guardrails' and ntype == 'n8n-nodes-base.code':
            if params.get('language') != 'javaScript':
                params['language'] = 'javaScript'
                changed = True
            if params.get('jsCode') != guardrails_code:
                params['jsCode'] = guardrails_code
                changed = True

        if name == 'Extract Reply' and ntype == 'n8n-nodes-base.code':
            if params.get('language') != 'javaScript':
                params['language'] = 'javaScript'
                changed = True
            if params.get('jsCode') != extract_code:
                params['jsCode'] = extract_code
                changed = True

        if name == 'Build Fallback Reply' and ntype == 'n8n-nodes-base.code':
            if params.get('language') != 'javaScript':
                params['language'] = 'javaScript'
                changed = True
            if params.get('jsCode') != fallback_code:
                params['jsCode'] = fallback_code
                changed = True

        if name == 'OpenAI Responses' and ntype == 'n8n-nodes-base.httpRequest':
            if params.get('jsonBody') != openai_json_body:
                params['jsonBody'] = openai_json_body
                changed = True

            # Keep retry/backoff hardening
            if node.get('retryOnFail') is not True:
                node['retryOnFail'] = True
                changed = True
            if int(node.get('maxTries', 0) or 0) != 5:
                node['maxTries'] = 5
                changed = True
            if int(node.get('waitBetweenTries', 0) or 0) != 5000:
                node['waitBetweenTries'] = 5000
                changed = True

            options = params.setdefault('options', {})
            batching = options.setdefault('batching', {'batch': {}})
            batch = batching.setdefault('batch', {})
            if int(batch.get('batchSize', 0) or 0) != 1:
                batch['batchSize'] = 1
                changed = True
            if int(batch.get('batchInterval', 0) or 0) != 1200:
                batch['batchInterval'] = 1200
                changed = True

        if name == 'Evolution Send Text' and ntype == 'n8n-nodes-base.httpRequest':
            url_value = "={{ 'http://evolution:8080'.replace(/\\/$/, '') + '/message/' + ($json.sendMode === 'media' ? 'sendMedia' : 'sendText') + '/' + ($json.instance || 'ATENDIMENTO_VENDAS_CLEAN') }}"
            if params.get('url') != url_value:
                params['url'] = url_value
                changed = True
            if params.get('jsonBody') != evolution_send_json_body:
                params['jsonBody'] = evolution_send_json_body
                changed = True

    if not changed:
        return None

    return json.dumps(nodes, ensure_ascii=False, separators=(',', ':'))


conn = sqlite3.connect(DB)
cur = conn.cursor()

entity_changes = 0
history_changes = 0

cur.execute('SELECT id, nodes FROM workflow_entity WHERE id = ?', (WORKFLOW_ID,))
row = cur.fetchone()
if row and row[1]:
    patched = patch_nodes_json(row[1])
    if patched is not None:
        cur.execute(
            'UPDATE workflow_entity SET nodes = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE id = ?',
            (patched, WORKFLOW_ID),
        )
        entity_changes = cur.rowcount

cur.execute('SELECT versionId, nodes FROM workflow_history WHERE workflowId = ?', (WORKFLOW_ID,))
for version_id, nodes_text in cur.fetchall():
    if not nodes_text:
        continue
    patched = patch_nodes_json(nodes_text)
    if patched is not None:
        cur.execute(
            'UPDATE workflow_history SET nodes = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE versionId = ?',
            (patched, version_id),
        )
        history_changes += cur.rowcount

conn.commit()
print(f'entity_changes={entity_changes}')
print(f'history_changes={history_changes}')

cur.execute('SELECT nodes FROM workflow_entity WHERE id = ?', (WORKFLOW_ID,))
nodes = json.loads(cur.fetchone()[0])
for n in nodes:
    if n.get('name') == 'Guardrails':
        c = n.get('parameters', {}).get('jsCode', '')
        print('guardrails_intelligence=' + str('aiSystemPrompt' in c and 'detectIntent' in c and 'customerProfiles' in c))
    if n.get('name') == 'Extract Reply':
        c = n.get('parameters', {}).get('jsCode', '')
        print('extract_intelligence=' + str('parseModelJson' in c and 'humanQueue' in c and 'learningBacklog' in c))
    if n.get('name') == 'OpenAI Responses':
        b = n.get('parameters', {}).get('jsonBody', '')
        print('openai_dynamic_prompt=' + str('aiSystemPrompt' in b and 'aiUserPrompt' in b))

conn.close()
