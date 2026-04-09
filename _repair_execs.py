import sqlite3
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
print('integrity_before', cur.execute('pragma integrity_check').fetchone())
try:
    rows=cur.execute("select id,status,finished from execution_entity order by id desc limit 10").fetchall()
    print('recent_before', rows)
except Exception as e:
    print('recent_before_error', e)
try:
    cur.execute("update execution_entity set status='error', finished=1, stoppedAt=COALESCE(stoppedAt,CURRENT_TIMESTAMP) where (status in ('new','running','crashed','unknown') or finished=0)")
    print('updated_rows', cur.rowcount)
except Exception as e:
    print('update_error', e)
try:
    cur.execute('pragma wal_checkpoint(full)')
    print('checkpoint', cur.fetchall())
except Exception as e:
    print('checkpoint_error', e)
conn.commit()
print('integrity_after', cur.execute('pragma integrity_check').fetchone())
print('recent_after', cur.execute("select id,status,finished from execution_entity order by id desc limit 10").fetchall())
conn.close()
