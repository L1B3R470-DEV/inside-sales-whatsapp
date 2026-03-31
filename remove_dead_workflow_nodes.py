import json, sqlite3, uuid
DB = '/data/database.sqlite'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
REMOVE_NODES = {'Evolution Find Contacts','Resolve Recipient','Router Decision','Resolve Recipient API'}

def patch(nodes_text, connections_text):
    nodes = json.loads(nodes_text)
    connections = json.loads(connections_text)
    changed = False
    filtered = [n for n in nodes if n.get('name') not in REMOVE_NODES]
    if len(filtered) != len(nodes):
        nodes = filtered
        changed = True
    for key in list(connections.keys()):
        if key in REMOVE_NODES:
            del connections[key]
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
