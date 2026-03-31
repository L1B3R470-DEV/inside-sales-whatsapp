import json, sqlite3

DB = '/data/database.sqlite'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'

DESIRED_CONNECTIONS = {
    'Extract Reply': {'main': [[{'node': 'Can Send?', 'type': 'main', 'index': 0}]]},
    'Build Fallback Reply': {'main': [[{'node': 'Can Send?', 'type': 'main', 'index': 0}]]},
    'Normalize Manual Send': {'main': [[{'node': 'Can Send?', 'type': 'main', 'index': 0}]]},
    'Can Send?': {'main': [[{'node': 'Router Learn', 'type': 'main', 'index': 0}], []]},
    'Router Learn': {'main': [[{'node': 'Evolution Send Text', 'type': 'main', 'index': 0}]]},
}


def patch(nodes_text, connections_text):
    nodes = json.loads(nodes_text)
    connections = json.loads(connections_text)
    changed = False
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
