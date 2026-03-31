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
  "model": "gpt-4.1-nano",
  "input": [
    {
      "role": "system",
      "content": [
        {
          "type": "input_text",
          "text": "Você é atendente virtual da Classe no WhatsApp. Responda em português do Brasil com tom cordial, acolhedor e objetivo. Demonstre atenção ao cliente e valorize a mensagem recebida. Se faltar contexto, faça uma pergunta curta para esclarecer. Limite a resposta a no máximo 2 frases curtas."
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": $node["Guardrails"].json.promptInput
        }
      ]
    }
  ],
  "temperature": 0.2,
  "max_output_tokens": Number($node["Guardrails"].json.maxOutputTokens || 120)
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
        print('guardrails_inclusive=' + str('value >= s && value <= e' in c))
        print('guardrails_accent=' + str('Olá! Obrigado pela sua mensagem.' in c))
    if n.get('name') == 'Normalize Payload':
        c = n.get('parameters', {}).get('jsCode', '')
        print('normalize_dedupe=' + str('processedMessageIds' in c))
        print('normalize_fromme=' + str('const fromMe' in c))
    if n.get('name') == 'OpenAI Responses':
        b = n.get('parameters', {}).get('jsonBody', '')
        print('openai_prompt_updated=' + str('Você é atendente virtual da Classe no WhatsApp' in b))

conn.close()
