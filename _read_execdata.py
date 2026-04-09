import sqlite3, json
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
for row in cur.execute("select executionId, substr(data,1,2500) from execution_data order by executionId desc limit 3").fetchall():
    print('EXEC', row[0])
    print(row[1])
    print('---')
conn.close()
