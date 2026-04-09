import sqlite3, json
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
row=cur.execute("select nodes,connections from workflow_entity where id=?", ('zN3heKJVLO8w4dG6',)).fetchone()
nodes=json.loads(row[0])
for n in nodes:
    if n.get('name') in ['Can Send?','Evolution Send Text','Build Fallback Reply']:
        print('NODE', n['name'])
        print(json.dumps(n.get('parameters',{}), ensure_ascii=False)[:4000])
        print('---')
conn.close()
