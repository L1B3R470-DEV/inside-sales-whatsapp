import sqlite3, json
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
row=cur.execute("select staticData from workflow_entity where id=?", ('zN3heKJVLO8w4dG6',)).fetchone()
obj=json.loads(row[0])
g=obj.setdefault('global', {})
profiles=g.setdefault('customerProfiles', {})
prof=profiles.setdefault('557588340000', {})
prof['number']='557588340000'
prof['customerName']='Phelper'
prof['pushName']='Phelper'
prof['leadStage']='qualificando'
prof['bookSalesAccess']='eligible'
prof['salesBookLastSentAt']=''
prof['awaitingVitrineConsent']=False
prof['vitrineShownAt']=''
prof['b2bLinkSentAt']=''
script=prof.setdefault('revendaScript', {})
script['active']=False
script['stage']=8
script['completed']=True
script['disqualified']=False
script['disqualifiedReason']=''
data=script.setdefault('data', {})
for k,v in {'cnpjAtivo':'sim','lojaFisica':'sim','cidade':'Feira de Santana','nome':'Phelper','telefone':'7588340000','instagram':'@oficialclasse','cnpj':'04623865000165'}.items():
    data[k]=v
script['cnpjValidationStatus']='checksum_valid'
script['cnpjLookupStatus']='lookup_unavailable'
cur.execute("update workflow_entity set staticData=?, updatedAt=CURRENT_TIMESTAMP where id=?", (json.dumps(obj,separators=(',',':')),'zN3heKJVLO8w4dG6'))
conn.commit()
row2=cur.execute("select staticData from workflow_entity where id=?", ('zN3heKJVLO8w4dG6',)).fetchone()
obj2=json.loads(row2[0])
print(obj2['global']['customerProfiles']['557588340000'])
conn.close()
