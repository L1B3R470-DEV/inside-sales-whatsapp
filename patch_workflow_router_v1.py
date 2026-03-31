import json
import sqlite3


DB = '/data/database.sqlite'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
ROUTER_BASE = 'http://host.docker.internal:8091'


def http_node(name, node_id, position, path):
    return {
        'parameters': {
            'method': 'POST',
            'url': f'{ROUTER_BASE}{path}',
            'sendHeaders': True,
            'headerParameters': {
                'parameters': [
                    {
                        'name': 'Content-Type',
                        'value': 'application/json',
                    }
                ]
            },
            'sendBody': True,
            'specifyBody': 'json',
            'jsonBody': '={{ $json }}',
            'options': {
                'timeout': 30000,
            },
        },
        'id': node_id,
        'name': name,
        'type': 'n8n-nodes-base.httpRequest',
        'typeVersion': 4.2,
        'position': position,
        'continueOnFail': True,
    }


def ensure_http_node(nodes, name, node_id, position, path):
    target = http_node(name, node_id, position, path)
    node = next((n for n in nodes if n.get('name') == name), None)
    changed = False

    if node is None:
        nodes.append(target)
        return True

    preserved_position = node.get('position') or position
    preserved_disabled = bool(node.get('disabled', False))
    if node != {**target, 'position': preserved_position, 'disabled': preserved_disabled}:
        target['position'] = preserved_position
        if preserved_disabled:
            target['disabled'] = True
        idx = nodes.index(node)
        nodes[idx] = target
        changed = True
    return changed


def ensure_router(nodes_text: str, connections_text: str):
    nodes = json.loads(nodes_text)
    connections = json.loads(connections_text)
    changed = False

    changed |= ensure_http_node(
        nodes,
        'Resolve Recipient API',
        'a707ce43-a0b2-4ca3-815f-4a94638751f1',
        [-540, 40],
        '/resolve-recipient',
    )
    changed |= ensure_http_node(
        nodes,
        'Router Decision',
        '8dbcf96b-8dae-4b64-8e64-18cfeb9c8d4d',
        [-390, 40],
        '/route',
    )
    changed |= ensure_http_node(
        nodes,
        'Router Learn',
        '84ee7744-d52c-4162-9d32-e2dc5ae72fea',
        [530, -40],
        '/learn-response',
    )

    desired_normalize_connection = {'main': [[{'node': 'Resolve Recipient API', 'type': 'main', 'index': 0}]]}
    if connections.get('Normalize Payload') != desired_normalize_connection:
        connections['Normalize Payload'] = desired_normalize_connection
        changed = True

    # Legacy recipient-resolution nodes are kept in the workflow, but disconnected
    # from the active path now that the router service resolves @lid directly.
    desired_find_contacts_connection = {'main': [[]]}
    if connections.get('Evolution Find Contacts') != desired_find_contacts_connection:
        connections['Evolution Find Contacts'] = desired_find_contacts_connection
        changed = True

    desired_resolve_connection = {'main': [[]]}
    if connections.get('Resolve Recipient') != desired_resolve_connection:
        connections['Resolve Recipient'] = desired_resolve_connection
        changed = True

    desired_resolve_api_connection = {'main': [[{'node': 'Router Decision', 'type': 'main', 'index': 0}]]}
    if connections.get('Resolve Recipient API') != desired_resolve_api_connection:
        connections['Resolve Recipient API'] = desired_resolve_api_connection
        changed = True

    desired_router_connection = {'main': [[{'node': 'Guardrails', 'type': 'main', 'index': 0}]]}
    if connections.get('Router Decision') != desired_router_connection:
        connections['Router Decision'] = desired_router_connection
        changed = True

    desired_extract_connection = {'main': [[{'node': 'Router Learn', 'type': 'main', 'index': 0}]]}
    if connections.get('Extract Reply') != desired_extract_connection:
        connections['Extract Reply'] = desired_extract_connection
        changed = True

    desired_fallback_connection = {'main': [[{'node': 'Router Learn', 'type': 'main', 'index': 0}]]}
    if connections.get('Build Fallback Reply') != desired_fallback_connection:
        connections['Build Fallback Reply'] = desired_fallback_connection
        changed = True

    desired_learn_connection = {'main': [[{'node': 'Can Send?', 'type': 'main', 'index': 0}]]}
    if connections.get('Router Learn') != desired_learn_connection:
        connections['Router Learn'] = desired_learn_connection
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
    patched_nodes, patched_connections = ensure_router(row[0], row[1])
    if patched_nodes is not None:
        cur.execute(
            'UPDATE workflow_entity SET nodes = ?, connections = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE id = ?',
            (patched_nodes, patched_connections, WORKFLOW_ID),
        )
        entity_changes = cur.rowcount

cur.execute('SELECT versionId, nodes, connections FROM workflow_history WHERE workflowId = ?', (WORKFLOW_ID,))
for version_id, nodes_text, connections_text in cur.fetchall():
    patched_nodes, patched_connections = ensure_router(nodes_text, connections_text)
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
