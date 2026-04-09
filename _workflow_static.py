import sqlite3, json
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
print(cur.execute("pragma table_info('workflow_entity')").fetchall())
row=cur.execute("select staticData from workflow_entity where id=?", ('zN3heKJVLO8w4dG6',)).fetchone()
print('has_staticData', row is not None and row[0] is not None)
if row and row[0]:
    txt=row[0]
    print('len', len(txt), 'contains_profile', '557588340000' in txt, 'contains_book' , 'salesBookAsset' in txt, 'contains_vitrine', 'vitrineAssets' in txt)
    print(txt[:2500])
conn.close()
