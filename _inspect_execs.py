import sqlite3, json
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
print('recent_execs', cur.execute("select id,status,finished,error from execution_entity order by id desc limit 5").fetchall())
rows=cur.execute("select executionId, workflowData from execution_data order by executionId desc limit 3").fetchall()
for executionId, workflowData in rows:
    txt = workflowData or ''
    print('exec', executionId, 'has_topology', 'operationalHostRole' in txt, 'has_book', 'BOOK_PROSPECCAO_VENDAS_INTERNAS.pdf' in txt, 'len', len(txt))
conn.close()
