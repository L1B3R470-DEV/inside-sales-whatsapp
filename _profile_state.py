import sqlite3, json
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
row=cur.execute("select staticData from workflow_entity where id=?", ('zN3heKJVLO8w4dG6',)).fetchone()
obj=json.loads(row[0])
g=obj.get('global',{})
profiles=g.get('customerProfiles',{})
for key in ['557588340000','557592738965','557583211367']:
    prof=profiles.get(key)
    print('PROFILE', key, bool(prof))
    if prof:
        for k in ['customerName','pushName','leadStage','bookSalesAccess','salesBookLastSentAt','awaitingVitrineConsent','vitrineShownAt','b2bLinkSentAt']:
            print(k, prof.get(k))
        print('revendaScript', prof.get('revendaScript'))
        print('---')
print('lidMap', g.get('lidToSJid',{}).get('114062134407423@lid'))
conn.close()
