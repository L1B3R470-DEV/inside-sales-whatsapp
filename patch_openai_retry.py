import json
import sqlite3

DB = '/data/database.sqlite'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
TARGET_NODE_NAME = 'OpenAI Responses'
TARGET_NODE_TYPE = 'n8n-nodes-base.httpRequest'


def patch_nodes_json(nodes_text: str):
    nodes = json.loads(nodes_text)
    changed = False

    for node in nodes:
        if node.get('name') == TARGET_NODE_NAME and node.get('type') == TARGET_NODE_TYPE:
            if node.get('retryOnFail') is not True:
                node['retryOnFail'] = True
                changed = True

            if int(node.get('maxTries', 0) or 0) != 5:
                node['maxTries'] = 5
                changed = True

            if int(node.get('waitBetweenTries', 0) or 0) != 5000:
                node['waitBetweenTries'] = 5000
                changed = True

            params = node.setdefault('parameters', {})
            options = params.setdefault('options', {})

            # Defensive throttling in case multiple items arrive together.
            batching = options.setdefault('batching', {'batch': {}})
            batch = batching.setdefault('batch', {})

            if int(batch.get('batchSize', 0) or 0) != 1:
                batch['batchSize'] = 1
                changed = True

            if int(batch.get('batchInterval', 0) or 0) != 1200:
                batch['batchInterval'] = 1200
                changed = True

    if not changed:
        return None

    return json.dumps(nodes, ensure_ascii=False, separators=(',', ':'))


conn = sqlite3.connect(DB)
cur = conn.cursor()

entity_changes = 0
history_changes = 0

# Patch active workflow entity
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

# Patch all versions in history for same workflow
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

# Verify from workflow_entity
cur.execute('SELECT nodes FROM workflow_entity WHERE id = ?', (WORKFLOW_ID,))
nodes = json.loads(cur.fetchone()[0])
for n in nodes:
    if n.get('name') == TARGET_NODE_NAME:
        print('retryOnFail=' + str(n.get('retryOnFail')))
        print('maxTries=' + str(n.get('maxTries')))
        print('waitBetweenTries=' + str(n.get('waitBetweenTries')))
        opts = n.get('parameters', {}).get('options', {})
        print('batching=' + json.dumps(opts.get('batching', {}), ensure_ascii=False))
        break

conn.close()
