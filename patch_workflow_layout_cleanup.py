import json, sqlite3, uuid
from pathlib import Path

DB = '/data/database.sqlite'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
ROUTER_BASE = 'http://host.docker.internal:8091'
WORK_DIR = Path('/work')
manual_code = (WORK_DIR / 'manual-send-normalize.js').read_text(encoding='utf-8')

LAYOUT = {
    'Webhook Evolution': [-1200, 120],
    'Normalize Payload': [-960, 120],
    'Guardrails': [-720, 120],
    'AI Allowed?': [-480, 120],
    'OpenAI Responses': [-220, -20],
    'Extract Reply': [40, -20],
    'Build Fallback Reply': [-220, 260],
    'Can Send?': [280, 120],
    'Router Learn': [540, 120],
    'Evolution Send Text': [800, 120],
    'Webhook Manual Send': [-220, 420],
    'Normalize Manual Send': [40, 420],
}

CAN_SEND_NODE = {
    'parameters': {
        'conditions': {
            'options': {
                'caseSensitive': True,
                'leftValue': '',
                'typeValidation': 'strict',
                'version': 2,
            },
            'conditions': [{
                'id': 'fb7ad479-4c76-4701-9d52-925f96d2f315',
                'leftValue': '={{ Boolean(String($json.number || "").trim()) && (($json.sendMode === "media" && Boolean(String($json.media || "").trim())) || Boolean(String($json.replyText || "").trim())) }}',
                'rightValue': '',
                'operator': {
                    'type': 'boolean',
                    'operation': 'true',
                    'singleValue': True,
                },
            }],
            'combinator': 'and',
        },
        'options': {},
    },
    'id': 'ce1d0eb4-1adf-4109-b304-6e1626ab8a84',
    'name': 'Can Send?',
    'type': 'n8n-nodes-base.if',
    'typeVersion': 2.2,
}

ROUTER_LEARN_NODE = {
    'parameters': {
        'method': 'POST',
        'url': f'{ROUTER_BASE}/learn-response',
        'sendHeaders': True,
        'headerParameters': {
            'parameters': [
                {'name': 'Content-Type', 'value': 'application/json'},
            ]
        },
        'sendBody': True,
        'specifyBody': 'json',
        'jsonBody': '={{ $json }}',
        'options': {'timeout': 30000},
    },
    'id': '84ee7744-d52c-4162-9d32-e2dc5ae72fea',
    'name': 'Router Learn',
    'type': 'n8n-nodes-base.httpRequest',
    'typeVersion': 4.2,
    'continueOnFail': True,
}

MANUAL_WEBHOOK_NODE = {
    'parameters': {
        'httpMethod': 'POST',
        'path': 'manual-outbound-send',
        'responseMode': 'onReceived',
        'options': {},
    },
    'id': '9c75cc2e-7fe4-45bb-b4b7-6e9f0184afab',
    'name': 'Webhook Manual Send',
    'type': 'n8n-nodes-base.webhook',
    'typeVersion': 2.1,
    'webhookId': 'manual-outbound-send',
}

MANUAL_NORMALIZE_NODE = {
    'parameters': {
        'language': 'javaScript',
        'jsCode': manual_code,
    },
    'id': 'f5ed974c-d8f8-468b-b2b0-8c26cf85d822',
    'name': 'Normalize Manual Send',
    'type': 'n8n-nodes-base.code',
    'typeVersion': 2,
}

ENSURE = {
    'Can Send?': CAN_SEND_NODE,
    'Router Learn': ROUTER_LEARN_NODE,
    'Webhook Manual Send': MANUAL_WEBHOOK_NODE,
    'Normalize Manual Send': MANUAL_NORMALIZE_NODE,
}

DESIRED_CONNECTIONS = {
    'Webhook Evolution': {'main': [[{'node': 'Normalize Payload', 'type': 'main', 'index': 0}]]},
    'Normalize Payload': {'main': [[{'node': 'Guardrails', 'type': 'main', 'index': 0}]]},
    'Guardrails': {'main': [[{'node': 'AI Allowed?', 'type': 'main', 'index': 0}]]},
    'AI Allowed?': {
        'main': [
            [{'node': 'OpenAI Responses', 'type': 'main', 'index': 0}],
            [{'node': 'Build Fallback Reply', 'type': 'main', 'index': 0}],
        ]
    },
    'OpenAI Responses': {'main': [[{'node': 'Extract Reply', 'type': 'main', 'index': 0}]]},
    'Extract Reply': {'main': [[{'node': 'Can Send?', 'type': 'main', 'index': 0}]]},
    'Build Fallback Reply': {'main': [[{'node': 'Can Send?', 'type': 'main', 'index': 0}]]},
    'Can Send?': {'main': [[{'node': 'Router Learn', 'type': 'main', 'index': 0}], []]},
    'Router Learn': {'main': [[{'node': 'Evolution Send Text', 'type': 'main', 'index': 0}]]},
    'Webhook Manual Send': {'main': [[{'node': 'Normalize Manual Send', 'type': 'main', 'index': 0}]]},
    'Normalize Manual Send': {'main': [[{'node': 'Can Send?', 'type': 'main', 'index': 0}]]},
}

REMOVE_CONNECTION_KEYS = [
    'Evolution Find Contacts', 'Resolve Recipient', 'Resolve Recipient API', 'Router Decision'
]


def patch(nodes_text, connections_text):
    nodes = json.loads(nodes_text)
    connections = json.loads(connections_text)
    changed = False
    by_name = {n.get('name'): n for n in nodes}

    for name, template in ENSURE.items():
        node = by_name.get(name)
        if node is None:
            node = dict(template)
            node['position'] = LAYOUT[name]
            nodes.append(node)
            by_name[name] = node
            changed = True
        else:
            desired = dict(template)
            desired['position'] = node.get('position') or LAYOUT[name]
            desired['disabled'] = bool(node.get('disabled', False))
            merged = dict(desired)
            if name not in ['Can Send?', 'Router Learn', 'Webhook Manual Send', 'Normalize Manual Send']:
                pass
            if name == 'Router Learn' and node.get('continueOnFail') != True:
                pass
            idx = nodes.index(node)
            # keep any unknown top-level attrs if harmless
            for k in ['credentials', 'notes', 'alwaysOutputData', 'retryOnFail', 'maxTries', 'waitBetweenTries']:
                if k in node and k not in merged:
                    merged[k] = node[k]
            if merged != node:
                nodes[idx] = merged
                by_name[name] = merged
                changed = True

    for node in nodes:
        name = node.get('name')
        desired_pos = LAYOUT.get(name)
        if desired_pos and node.get('position') != desired_pos:
            node['position'] = desired_pos
            changed = True

    for key in REMOVE_CONNECTION_KEYS:
        if key in connections:
            del connections[key]
            changed = True

    for key, value in DESIRED_CONNECTIONS.items():
        if connections.get(key) != value:
            connections[key] = value
            changed = True

    if not changed:
        return None, None
    return json.dumps(nodes, ensure_ascii=False, separators=(',', ':')), json.dumps(connections, ensure_ascii=False, separators=(',', ':'))

conn = sqlite3.connect(DB)
cur = conn.cursor()
entity_changes = 0
history_changes = 0
cur.execute('select nodes, connections from workflow_entity where id = ?', (WORKFLOW_ID,))
row = cur.fetchone()
if row:
    n, c = patch(row[0], row[1])
    if n is not None:
        cur.execute('update workflow_entity set nodes = ?, connections = ?, versionId = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW"), versionCounter = versionCounter + 1 where id = ?', (n, c, str(uuid.uuid4()), WORKFLOW_ID))
        entity_changes = cur.rowcount
cur.execute('select versionId, nodes, connections from workflow_history where workflowId = ?', (WORKFLOW_ID,))
for version_id, nodes_text, connections_text in cur.fetchall():
    n, c = patch(nodes_text, connections_text)
    if n is not None:
        cur.execute('update workflow_history set nodes = ?, connections = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") where versionId = ?', (n, c, version_id))
        history_changes += cur.rowcount
conn.commit()
print(f'entity_changes={entity_changes}')
print(f'history_changes={history_changes}')
conn.close()
