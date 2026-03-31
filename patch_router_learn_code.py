import json, sqlite3
from pathlib import Path

DB = '/data/database.sqlite'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
WORK_DIR = Path('/work')
router_learn_code = (WORK_DIR / 'router-learn.js').read_text(encoding='utf-8')

ROUTER_LEARN_NODE = {
    'parameters': {
        'language': 'javaScript',
        'jsCode': router_learn_code,
    },
    'id': '84ee7744-d52c-4162-9d32-e2dc5ae72fea',
    'name': 'Router Learn',
    'type': 'n8n-nodes-base.code',
    'typeVersion': 2,
}

DESIRED_CONNECTIONS = {
    'Extract Reply': {'main': [[{'node': 'Router Learn', 'type': 'main', 'index': 0}]]},
    'Build Fallback Reply': {'main': [[{'node': 'Router Learn', 'type': 'main', 'index': 0}]]},
    'Router Learn': {'main': [[{'node': 'Can Send?', 'type': 'main', 'index': 0}]]},
}


def patch(nodes_text, connections_text):
    nodes = json.loads(nodes_text)
    connections = json.loads(connections_text)
    changed = False
    node = next((n for n in nodes if n.get('name') == 'Router Learn'), None)
    if node is None:
        return None, None
    desired = dict(ROUTER_LEARN_NODE)
    desired['position'] = node.get('position', [530, -40])
    if node.get('disabled'):
        desired['disabled'] = True
    for k in ['notes', 'alwaysOutputData', 'retryOnFail', 'maxTries', 'waitBetweenTries']:
        if k in node:
            desired[k] = node[k]
    if node != desired:
        nodes[nodes.index(node)] = desired
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
cur.execute('SELECT nodes, connections FROM workflow_entity WHERE id = ?', (WORKFLOW_ID,))
row = cur.fetchone()
if row:
    patched_nodes, patched_connections = patch(row[0], row[1])
    if patched_nodes is not None:
        cur.execute(
            'UPDATE workflow_entity SET nodes = ?, connections = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE id = ?',
            (patched_nodes, patched_connections, WORKFLOW_ID),
        )
        entity_changes = cur.rowcount
cur.execute('SELECT versionId, nodes, connections FROM workflow_history WHERE workflowId = ?', (WORKFLOW_ID,))
for version_id, nodes_text, connections_text in cur.fetchall():
    patched_nodes, patched_connections = patch(nodes_text, connections_text)
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
