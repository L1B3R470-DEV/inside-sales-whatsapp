import json
import sqlite3


DB = '/data/database.sqlite'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
SEND_GATE_EXPR = '={{ Boolean($json.sendEligible === true && String($json.number || "").trim()) }}'


def patch_nodes_json(nodes_text: str):
    nodes = json.loads(nodes_text)
    changed = False

    for node in nodes:
        if node.get('name') != 'Can Send?' or node.get('type') != 'n8n-nodes-base.if':
            continue

        params = node.setdefault('parameters', {})
        conditions = params.setdefault('conditions', {})
        options = conditions.setdefault('options', {})

        if options.get('caseSensitive') is not True:
            options['caseSensitive'] = True
            changed = True
        if options.get('leftValue') != '':
            options['leftValue'] = ''
            changed = True
        if options.get('typeValidation') != 'strict':
            options['typeValidation'] = 'strict'
            changed = True
        if int(options.get('version', 0) or 0) != 2:
            options['version'] = 2
            changed = True

        current_conditions = conditions.get('conditions')
        desired_conditions = [{
            'id': '8a10a0a9-0d49-41ab-b442-0be9b1d5e022',
            'leftValue': SEND_GATE_EXPR,
            'rightValue': '',
            'operator': {
                'type': 'boolean',
                'operation': 'true',
                'singleValue': True,
            },
        }]
        if current_conditions != desired_conditions:
            conditions['conditions'] = desired_conditions
            changed = True

        if conditions.get('combinator') != 'and':
            conditions['combinator'] = 'and'
            changed = True

        node_options = params.get('options')
        if node_options != {}:
            params['options'] = {}
            changed = True

    if not changed:
        return None

    return json.dumps(nodes, ensure_ascii=False, separators=(',', ':'))


conn = sqlite3.connect(DB)
cur = conn.cursor()

entity_changes = 0
history_changes = 0
gate_confirmed = False

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

cur.execute('SELECT nodes FROM workflow_entity WHERE id = ?', (WORKFLOW_ID,))
row = cur.fetchone()
if row and row[0]:
    nodes = json.loads(row[0])
    for node in nodes:
        if node.get('name') == 'Can Send?':
            node_conditions = (((node.get('parameters') or {}).get('conditions') or {}).get('conditions') or [])
            if node_conditions:
                gate_confirmed = node_conditions[0].get('leftValue') == SEND_GATE_EXPR
            break

print(f'entity_changes={entity_changes}')
print(f'history_changes={history_changes}')
print(f'send_gate_confirmed={gate_confirmed}')

conn.close()
