import sqlite3
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
print(cur.execute("select id,status,finished,mode,startedAt,stoppedAt,createdAt from execution_entity order by id desc limit 10").fetchall())
conn.close()
