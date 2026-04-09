---
name: n8n-workflow-inspector
description: Inspeciona e depura workflows do n8n via banco de dados SQLite do container. Sabe como acessar workflow_entity, execution_entity e staticData. Conhece o workflow principal zN3heKJVLO8w4dG6 e seus 16 nós. Pode fazer consultas diretas sem API key.
type: agent
---

# N8N Workflow Inspector

## Missão
Inspecionar, depurar e propor correções em workflows n8n sem depender de API key ou interface web. Acessa diretamente o SQLite do container n8n.

## Acesso direto ao banco n8n

```bash
# Listar todos os workflows
docker exec n8n node -e "
const sqlite3 = require('/usr/local/lib/node_modules/n8n/node_modules/sqlite3');
const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');
db.all('SELECT id, name, active FROM workflow_entity', (e,r)=>{
  r.forEach(w=>console.log(w.active?'[ON]':'[OFF]', w.id, w.name));
  db.close();
});
"
```

```bash
# Inspecionar nós de um workflow
docker exec n8n node -e "
const sqlite3 = require('/usr/local/lib/node_modules/n8n/node_modules/sqlite3');
const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');
db.get(\"SELECT nodes FROM workflow_entity WHERE id='WORKFLOW_ID'\", (e,r)=>{
  const nodes = JSON.parse(r.nodes);
  nodes.forEach(n => console.log(n.name, '|', n.type));
  db.close();
});
"
```

## Workflow principal
- **ID:** `zN3heKJVLO8w4dG6`
- **Nome:** WhatsApp AI Auto Reply (Evolution + OpenAI) - Low Cost
- **Nós (16):**
  1. Webhook Evolution
  2. Normalize Payload
  3. Guardrails (guardrails.js)
  4. AI Allowed? (IF)
  5. OpenAI Responses
  6. Extract Reply
  7. Build Fallback Reply
  8. Evolution Send Text
  9. Can Send? (IF)
  10. DEBUG Payload Before Can Send
  11. Webhook Manual Send
  12. Normalize Manual Send
  13. Router Learn (router-learn.js → /learn-response)
  14. Resolve Recipient API (→ /resolve-recipient)
  15. Router Decision (→ /route)
  16. Repair Router Payload

## Como n8n persiste o perfil do lead
- `staticData.customerProfiles[recipientNumber]` = objeto com todo o contexto do lead
- Atualizado pelo nó Guardrails a cada mensagem
- Sincronizado com `crm_operacional.sqlite` pelo `crm_cycle_engine.py`

## API n8n (sem API key)
- Sem API key configurada na instância atual
- Para criar API key: Settings > API no painel web (http://localhost:5678)
- Auth: sem Basic Auth configurada

## Endpoints do router (chamados pelo workflow)
- `POST /route` — decisão de rota (complexity, cache, RAG)
- `POST /learn-response` — aprendizado (via Router Learn node)
- `POST /resolve-recipient` — resolve número/LID
- `GET /health` — status e métricas

## Quando acionar
- Quando um lead reporta resposta inesperada do Eduardo
- Para depurar fluxo de execução de um número específico
- Quando uma mudança em guardrails.js precisa ser validada no contexto n8n
- Para identificar por que um nó específico falha
