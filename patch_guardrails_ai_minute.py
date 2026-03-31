import json
import sqlite3

DB = '/data/database.sqlite'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
TARGET_NODE_NAME = 'Guardrails'
TARGET_NODE_TYPE = 'n8n-nodes-base.code'

with open('/work/guardrails.js', 'r', encoding='ascii') as f:
    new_code = f.read()


def patch_nodes_json(nodes_text: str):
    nodes = json.loads(nodes_text)
    changed = False

    for node in nodes:
        if node.get('name') == TARGET_NODE_NAME and node.get('type') == TARGET_NODE_TYPE:
            params = node.setdefault('parameters', {})
            if params.get('language') != 'javaScript':
                params['language'] = 'javaScript'
                changed = True
            if params.get('jsCode') != new_code:
                params['jsCode'] = new_code
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
        params = n.get('parameters', {})
        code = params.get('jsCode', '')
        print('language=' + str(params.get('language')))
        print('has_ai_minute=' + str('maxAiCallsPerMinute' in code))
        print('code_prefix=' + code[:80].replace('\n',' '))
        break

conn.close()
