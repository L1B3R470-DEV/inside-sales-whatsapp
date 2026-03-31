import json
import sqlite3
import uuid

DB = '/data/database.sqlite'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'

with open('/work/manual-send-normalize.js', 'r', encoding='utf-8') as f:
    manual_normalize_code = f.read()

WEBHOOK_NAME = 'Webhook Manual Send'
WEBHOOK_ID = '9c75cc2e-7fe4-45bb-b4b7-6e9f0184afab'
NORMALIZE_NAME = 'Normalize Manual Send'
NORMALIZE_ID = 'f5ed974c-d8f8-468b-b2b0-8c26cf85d822'
MANUAL_PATH = 'manual-outbound-send'


def ensure_manual_nodes(nodes_text: str, connections_text: str):
    nodes = json.loads(nodes_text)
    connections = json.loads(connections_text)
    changed = False

    webhook_node = next((n for n in nodes if n.get('name') == WEBHOOK_NAME), None)
    if webhook_node is None:
        webhook_node = {
            'parameters': {
                'httpMethod': 'POST',
                'path': MANUAL_PATH,
                'responseMode': 'onReceived',
                'options': {},
            },
            'id': WEBHOOK_ID,
            'name': WEBHOOK_NAME,
            'type': 'n8n-nodes-base.webhook',
            'typeVersion': 2.1,
            'position': [-120, 300],
            'webhookId': MANUAL_PATH,
        }
        nodes.append(webhook_node)
        changed = True
    else:
        params = webhook_node.setdefault('parameters', {})
        desired = {
            'httpMethod': 'POST',
            'path': MANUAL_PATH,
            'responseMode': 'onReceived',
        }
        for key, value in desired.items():
            if params.get(key) != value:
                params[key] = value
                changed = True
        if webhook_node.get('webhookId') != MANUAL_PATH:
            webhook_node['webhookId'] = MANUAL_PATH
            changed = True

    normalize_node = next((n for n in nodes if n.get('name') == NORMALIZE_NAME), None)
    if normalize_node is None:
        normalize_node = {
            'parameters': {
                'language': 'javaScript',
                'jsCode': manual_normalize_code,
            },
            'id': NORMALIZE_ID,
            'name': NORMALIZE_NAME,
            'type': 'n8n-nodes-base.code',
            'typeVersion': 2,
            'position': [120, 300],
        }
        nodes.append(normalize_node)
        changed = True
    else:
        params = normalize_node.setdefault('parameters', {})
        if params.get('language') != 'javaScript':
            params['language'] = 'javaScript'
            changed = True
        if params.get('jsCode') != manual_normalize_code:
            params['jsCode'] = manual_normalize_code
            changed = True

    if connections.get(WEBHOOK_NAME) != {'main': [[{'node': NORMALIZE_NAME, 'type': 'main', 'index': 0}]]}:
        connections[WEBHOOK_NAME] = {'main': [[{'node': NORMALIZE_NAME, 'type': 'main', 'index': 0}]]}
        changed = True

    if connections.get(NORMALIZE_NAME) != {'main': [[{'node': 'Can Send?', 'type': 'main', 'index': 0}]]}:
        connections[NORMALIZE_NAME] = {'main': [[{'node': 'Can Send?', 'type': 'main', 'index': 0}]]}
        changed = True

    if not changed:
        return None, None

    return (
        json.dumps(nodes, ensure_ascii=False, separators=(',', ':')),
        json.dumps(connections, ensure_ascii=False, separators=(',', ':')),
    )


conn = sqlite3.connect(DB)
cur = conn.cursor()

entity_changes = 0
history_changes = 0

cur.execute('SELECT nodes, connections FROM workflow_entity WHERE id = ?', (WORKFLOW_ID,))
row = cur.fetchone()
if row:
    patched_nodes, patched_connections = ensure_manual_nodes(row[0], row[1])
    if patched_nodes is not None:
        cur.execute(
            'UPDATE workflow_entity SET nodes = ?, connections = ?, versionId = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW"), versionCounter = versionCounter + 1 WHERE id = ?',
            (patched_nodes, patched_connections, str(uuid.uuid4()), WORKFLOW_ID),
        )
        entity_changes = cur.rowcount

cur.execute('SELECT versionId, nodes, connections FROM workflow_history WHERE workflowId = ?', (WORKFLOW_ID,))
for version_id, nodes_text, connections_text in cur.fetchall():
    patched_nodes, patched_connections = ensure_manual_nodes(nodes_text, connections_text)
    if patched_nodes is not None:
        cur.execute(
            'UPDATE workflow_history SET nodes = ?, connections = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE versionId = ?',
            (patched_nodes, patched_connections, version_id),
        )
        history_changes += cur.rowcount

conn.commit()
print(f'entity_changes={entity_changes}')
print(f'history_changes={history_changes}')
conn.close()
