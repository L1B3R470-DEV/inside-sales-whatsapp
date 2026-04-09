import sqlite3
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
row=cur.execute("select staticData from workflow_entity where id=?", ('zN3heKJVLO8w4dG6',)).fetchone()
open('/host/_staticData_live.json','w',encoding='utf-8').write(row[0])
conn.close()
print('dumped_live')
