import sqlite3, json
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
row=cur.execute("select staticData from workflow_entity where id=?", ('zN3heKJVLO8w4dG6',)).fetchone()
obj=json.loads(row[0])
g=obj.get('global',{})
for key in g.keys():
    if 'dup' in key.lower() or 'outbound' in key.lower() or 'finger' in key.lower() or 'sent' in key.lower():
        print('KEY', key)
        txt=json.dumps(g.get(key), ensure_ascii=False)
        if '557588340000' in txt:
            print('contains_test_number', key)
            print(txt[:2000])
            print('---')
conn.close()
