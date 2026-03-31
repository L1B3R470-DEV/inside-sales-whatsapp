import sqlite3, json
conn = sqlite3.connect('/data/database.sqlite')
conn.row_factory = sqlite3.Row
row = conn.execute("select staticData from workflow_entity where id = ?", ('zN3heKJVLO8w4dG6',)).fetchone()
obj = json.loads(row['staticData'] or '{}')
g = obj.get('global', {})
profiles = g.setdefault('customerProfiles', {})
key = '558796686768'
p = profiles.get(key, {})
p['customerName'] = 'Edileuza'
p['customerNameSource'] = 'whatsapp_profile'
p['customerNameUpdatedAt'] = '2026-03-19T20:35:00.000Z'
p['pushName'] = p.get('pushName') or 'Edileuza Cruz'
rev = p.get('revendaScript') or {}
rev['active'] = True
rev['stage'] = 5
rev['completed'] = False
rev['disqualified'] = False
rev['disqualifiedReason'] = ''
data = rev.get('data') or {}
data['cnpjAtivo'] = 'sim'
data['lojaFisica'] = 'sim'
data['cidade'] = 'Cedro PE'
data['nome'] = 'Edileuza'
data['telefone'] = ''
data['instagram'] = ''
data['cnpj'] = ''
rev['data'] = data
p['revendaScript'] = rev
profiles[key] = p
obj['global'] = g
conn.execute("update workflow_entity set staticData = ?, updatedAt = STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW') where id = ?", (json.dumps(obj, ensure_ascii=False, separators=(',', ':')), 'zN3heKJVLO8w4dG6'))
conn.commit()
print('updated')
print(json.dumps(profiles[key], ensure_ascii=False, indent=2))
conn.close()
