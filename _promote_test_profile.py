import sqlite3, json, copy
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
row=cur.execute("select staticData from workflow_entity where id=?", ('zN3heKJVLO8w4dG6',)).fetchone()
obj=json.loads(row[0])
g=obj.setdefault('global', {})
profiles=g.setdefault('customerProfiles', {})
prof=profiles.setdefault('557588340000', {})
prof['customerName']='Phelper'
prof['pushName']=prof.get('pushName') or 'Phelper'
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
data['cnpjAtivo']='sim'
data['lojaFisica']='sim'
data['cidade']=data.get('cidade') or 'Feira de Santana'
data['nome']='Phelper'
data['telefone']='7588340000'
data['instagram']=data.get('instagram') or '@oficialclasse'
data['cnpj']=data.get('cnpj') or '04623865000165'
script['cnpjValidationStatus']='checksum_valid'
script['cnpjLookupStatus']='lookup_unavailable'
new_static=json.dumps(obj,separators=(',',':'))
cur.execute("update workflow_entity set staticData=?, updatedAt=CURRENT_TIMESTAMP where id=?", (new_static,'zN3heKJVLO8w4dG6'))
conn.commit()
print('patched_test_profile')
print(profiles['557588340000'])
conn.close()
