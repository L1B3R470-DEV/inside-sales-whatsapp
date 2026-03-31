import json
import sqlite3

DB = '/data/database.sqlite'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'

with open('/work/resolve-recipient.js', 'r', encoding='ascii') as f:
    new_code = f.read()

conn = sqlite3.connect(DB)
cur = conn.cursor()

def patch_nodes_json(nodes_text):
    nodes = json.loads(nodes_text)
    changed = False
    for node in nodes:
        if node.get('name') == 'Resolve Recipient' and node.get('type') == 'n8n-nodes-base.code':
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

# workflow_entity
cur.execute('SELECT id, nodes FROM workflow_entity WHERE id = ?', (WORKFLOW_ID,))
row = cur.fetchone()
entity_changes = 0
if row and row[1]:
    patched = patch_nodes_json(row[1])
    if patched is not None:
        cur.execute('UPDATE workflow_entity SET nodes = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE id = ?', (patched, WORKFLOW_ID))
        entity_changes = cur.rowcount

# workflow_history (all versions for same workflow)
cur.execute('SELECT versionId, nodes FROM workflow_history WHERE workflowId = ?', (WORKFLOW_ID,))
history_rows = cur.fetchall()
history_changes = 0
for version_id, nodes_text in history_rows:
    if not nodes_text:
        continue
    patched = patch_nodes_json(nodes_text)
    if patched is not None:
        cur.execute('UPDATE workflow_history SET nodes = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE versionId = ?', (patched, version_id))
        history_changes += cur.rowcount

conn.commit()
print(f'entity_changes={entity_changes}')
print(f'history_changes={history_changes}')

# quick verify current active workflow node
cur.execute('SELECT nodes FROM workflow_entity WHERE id = ?', (WORKFLOW_ID,))
nodes = json.loads(cur.fetchone()[0])
for n in nodes:
    if n.get('name') == 'Resolve Recipient':
        print('language=' + str(n.get('parameters', {}).get('language')))
        print('jsCode_prefix=' + n.get('parameters', {}).get('jsCode', '')[:60].replace('\n',' '))
        break

conn.close()
