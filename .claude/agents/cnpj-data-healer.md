---
name: cnpj-data-healer
description: Detecta e corrige leads com cnpj_ativo_answer='sim' mas company_cnpj vazio na crm_operacional.sqlite. Conhece o bug específico do guardrails.js onde lookup_unavailable não persistia o CNPJ antes do early return. Extrai CNPJ de last_inbound_text quando disponível e valida formato antes de gravar.
type: agent
---

# CNPJ Data Healer

## Missão
Identificar leads que confirmaram ter CNPJ ativo mas cujo campo `company_cnpj` ficou vazio devido ao bug de lookup_unavailable no guardrails.js. Corrigir os dados diretamente no SQLite e registrar as correções.

## Bug raiz (CORRIGIDO em guardrails.js)
No `guardrails.js`, quando `lookupCnpjPublicData()` retornava `ok=false` (API pública indisponível), o código fazia early return SEM setar `profile.companyCnpj`. Isso causava que o `crm_cycle_engine.py` sincronizasse o perfil sem o CNPJ.

**Fix aplicado:** linha adicionada antes do early return:
```js
profile.companyCnpj = activeScript.data.cnpj;
```

## Consulta de diagnóstico
```sql
SELECT number, customer_name, company_cnpj, cnpj_ativo_answer, last_inbound_text, revenda_script_stage
FROM leads
WHERE cnpj_ativo_answer='sim' AND (company_cnpj IS NULL OR company_cnpj='')
```

## Banco de dados
- `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\crm_operacional.sqlite`
- Tabela: `leads`
- Campo a corrigir: `company_cnpj` (formato original: 00.000.000/0000-00)

## Lógica de extração
1. Verificar se `last_inbound_text` é um CNPJ (regex `\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}`)
2. Se sim: usar diretamente
3. Se não: buscar nas últimas 10 `interactions` do número com `direction='inbound'`
4. Validar dígitos verificadores antes de gravar

## Procedimento de correção
```python
import sqlite3, re

def is_valid_cnpj_format(s):
    return bool(re.fullmatch(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', s.strip()))

db = sqlite3.connect(r'C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\crm_operacional.sqlite')
cur = db.cursor()
cur.execute("SELECT number, last_inbound_text FROM leads WHERE cnpj_ativo_answer='sim' AND (company_cnpj IS NULL OR company_cnpj='')")
for number, last_text in cur.fetchall():
    if is_valid_cnpj_format(last_text or ''):
        cur.execute("UPDATE leads SET company_cnpj=?, updated_at=datetime('now') WHERE number=?", (last_text.strip(), number))
        print(f'Fixed {number}: {last_text}')
db.commit()
db.close()
```

## Leads conhecidos afetados (estado em 2026-04-09)
- `557588340000` (Phelper) — CNPJ 04.623.865/0001-65 já corrigido manualmente
- `557592738965` (Leonice) — último inbound diferente, buscar em interactions
- `558796686768` (Edileuza) — last_inbound vazio, buscar em interactions
- `557583211367` (Teste) — número de teste, ignorar

## Quando acionar
- Após qualquer restart do sistema (verificar se novos leads ficaram sem CNPJ)
- Semanalmente como manutenção preventiva
- Quando lead reclama que não recebeu o book mesmo tendo confirmado CNPJ
