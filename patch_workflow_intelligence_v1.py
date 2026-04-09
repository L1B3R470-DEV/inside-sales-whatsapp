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
with open('/work/workflow-send-gate.js', 'r', encoding='utf-8') as f:
    send_gate_code = f.read()

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

evolution_send_json_body = '''={{ $json.sendMode === "buttons"
  ? {
      "number": String($json.number || "").trim(),
      "title": String($json.title || "").trim(),
      "description": String($json.description || "").trim(),
      "footer": String($json.footer || "").trim(),
      "buttons": Array.isArray($json.buttons)
        ? $json.buttons.map((btn) => ({
            "type": String(btn.type || "reply"),
            "displayText": String(btn.displayText || "").trim(),
            "id": String(btn.id || "").trim()
          }))
        : [],
      "delay": 1200
    }
  : ($json.sendMode === "media"
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
      }) }}'''

router_base_expr = "={{ String($env.ROUTER_BASE_URL || 'http://router:8091').replace(/\\/$/, '') }}"


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

        if name == 'DEBUG Payload Before Can Send' and ntype == 'n8n-nodes-base.code':
            if params.get('language') != 'javaScript':
                params['language'] = 'javaScript'
                changed = True
            if params.get('jsCode') != send_gate_code:
                params['jsCode'] = send_gate_code
                changed = True

        if name in {'Resolve Recipient API', 'Router Decision', 'Router Learn'} and ntype == 'n8n-nodes-base.httpRequest':
            if name == 'Resolve Recipient API':
                desired_url = router_base_expr + " + '/resolve-recipient'"
                if params.get('url') != desired_url:
                    params['url'] = desired_url
                    changed = True
            if name == 'Router Decision':
                desired_url = router_base_expr + " + '/route'"
                if params.get('url') != desired_url:
                    params['url'] = desired_url
                    changed = True
            if name == 'Router Learn':
                desired_url = router_base_expr + " + '/learn-response'"
                if params.get('url') != desired_url:
                    params['url'] = desired_url
                    changed = True
            if int(node.get('timeout', 0) or 0) != 5000:
                node['timeout'] = 5000
                changed = True
            if node.get('retryOnFail') is not True:
                node['retryOnFail'] = True
                changed = True
            if int(node.get('maxTries', 0) or 0) != 3:
                node['maxTries'] = 3
                changed = True
            if int(node.get('waitBetweenTries', 0) or 0) != 300:
                node['waitBetweenTries'] = 300
                changed = True
            if node.get('continueOnFail') is not True:
                node['continueOnFail'] = True
                changed = True
            if node.get('onError') != 'continueRegularOutput':
                node['onError'] = 'continueRegularOutput'
                changed = True

        if name == 'OpenAI Responses' and ntype == 'n8n-nodes-base.httpRequest':
            if params.get('jsonBody') != openai_json_body:
                params['jsonBody'] = openai_json_body
                changed = True

            # The downstream Extract Reply node already knows how to recover from
            # OpenAI request failures using router-generated text/fallbacks, so
            # the HTTP request must never abort the whole execution.
            if node.get('continueOnFail') is not True:
                node['continueOnFail'] = True
                changed = True
            if node.get('onError') != 'continueRegularOutput':
                node['onError'] = 'continueRegularOutput'
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
            url_value = "={{ 'http://evolution:8080'.replace(/\\/$/, '') + '/message/' + ($json.sendMode === 'buttons' ? 'sendButtons' : ($json.sendMode === 'media' ? 'sendMedia' : 'sendText')) + '/' + ($json.instance || 'ATENDIMENTO_VENDAS_CLEAN') }}"
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
        print('openai_continue_on_fail=' + str(n.get('continueOnFail') is True and n.get('onError') == 'continueRegularOutput'))

conn.close()
