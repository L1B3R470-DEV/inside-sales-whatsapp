import sqlite3, json
conn = sqlite3.connect('/data/database.sqlite')
conn.row_factory = sqlite3.Row
row = conn.execute("select nodes, connections from workflow_entity where id = ?", ('zN3heKJVLO8w4dG6',)).fetchone()
nodes = json.loads(row['nodes'])
conns = json.loads(row['connections'])
print([n.get('name') for n in nodes])
print(json.dumps({k:v for k,v in conns.items() if k in ['Normalize Payload','Resolve Recipient API','Router Decision','Extract Reply','Build Fallback Reply','Router Learn']}, ensure_ascii=False, indent=2))
conn.close()
