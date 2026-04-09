import sqlite3
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
print('execution_entity_cols', cur.execute("pragma table_info('execution_entity')").fetchall())
print('execution_data_cols', cur.execute("pragma table_info('execution_data')").fetchall())
print('recent_execs', cur.execute("select * from execution_entity order by id desc limit 3").fetchall())
conn.close()
