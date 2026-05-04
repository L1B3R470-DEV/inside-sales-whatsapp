# AGENTS.md — Atendente WhatsApp B2B Inside Sales (Classe)

Este arquivo é lido automaticamente pelo Codex a cada nova sessão neste projeto.

---

## Identidade Git
```
git config user.name "Inside Sales Dev"
git config user.email "dev@insidesales.local"
```

---

## O Projeto

Sistema de atendimento inteligente via WhatsApp B2B para captação e qualificação de leads revendedores da **Classe**. Opera em produção.

### Stack
| Componente | Localização | Porta |
|---|---|---|
| Evolution API (WhatsApp) | Docker container | 8080 |
| n8n (automação de fluxo) | Docker container | 5678 |
| router_service.py (Python/Flask) | Docker `router` | 8091 |
| Redis (cache Evolution) | Docker container | 6379 |
| PostgreSQL (banco Evolution) | Docker container | 5432 |
| Qdrant (vetorial RAG) | Local | — |

### Fluxo principal
```
WhatsApp → Evolution (8080) → n8n webhook → router-decision.js
→ router_service.py (8091):
    ├── Cache hit      → resposta SQLite instantânea
    ├── RAG match      → contexto Qdrant + GPT
    └── GPT fallback   → gpt-4o direto (último recurso)
→ extract-reply.js → Evolution send → WhatsApp
```

### Arquivos CORE (ler estes ao retomar trabalho)
- `router_service.py` — roteador Flask principal (cache, RAG, GPT, LID, rate-limit)
- `guardrails.js` — regras de negócio, bloqueios, horário, intents do SDR
- `extract-reply.js` — pós-processamento da resposta GPT
- `build-fallback-reply.js` — fallback + saudação + mídia
- `normalize-payload.js` — normalização de payload inbound
- `docker-compose.yml` — infraestrutura Docker
- `README.md` — arquitetura geral

### Arquivos SECUNDÁRIOS (ler sob demanda)
- `router-decision.js` / `router-learn.js` — bridge n8n→router
- `crm_cycle_engine.py` / `crm_sheet_sync.py` — CRM e Google Sheets
- `human-alert-monitor.ps1` — alertas humanos

### NÃO LER (ignorar sempre)
- `_archive/` — backups antigos
- `*.json` com hash no nome — exports n8n (grandes)
- `instagram_*.py`, `launch_*.vbs` — projeto paralelo de scraping
- `evolution-main.js`, `evolution-openapi.json` — código fonte Evolution (não modifica)

---

## Bancos de Dados

### `crm_operacional.sqlite`
Tabelas: `leads`, `interactions`, `learning_backlog`, `knowledge_rules`, `knowledge_cycles`, `knowledge_documents`, `ignored_contacts_registry`

### `router_runtime.sqlite`
Tabelas: `response_cache`, `route_logs`, `rag_documents`, `rag_chunks`

---

## Persona SDR
- **Nome:** Eduardo Vinhas
- **Cargo:** Consultor de Vendas Internas, Classe
- **Tom:** humano, simpático, consultivo, comercial
- **Horário:** Seg-Sex 08:00-12:00 e 13:30-18:00 (America/Bahia)

---

## Workflow n8n Principal
- **ID:** `zN3heKJVLO8w4dG6`

---

## MCPs Ativos (`.mcp.json`)
- `sqlite` → `crm_operacional.sqlite`
- `sqlite-router` → `router_runtime.sqlite`
- `fetch` → HTTP fetch genérico
- `bridge-monitor` → `mcp_bridge_monitor.py` (monitora bridge n8n↔router)

---

## Agents Disponíveis (`.Codex/agents/`)
Invoque com `/nome-do-agente`:
- `status` — health check completo da stack
- `restart` — reinicia componentes
- `logs` — analisa logs recentes
- `router` — analisa/melhora router_service.py
- `guardrails` — analisa/melhora regras guardrails.js
- `crm` — consulta e opera o CRM
- `debug-lead` — investiga estado de um lead específico
- `metrics` — métricas e estatísticas de atendimento
- `flow` — analisa/ajusta fluxo de atendimento
- `deploy` — aplica mudanças e reinicia serviços com segurança
- `backup` — faz backup dos dados críticos
- `test-msg` — simula envio de mensagem para testar o fluxo

---

## Hooks Ativos (`settings.json`)
- **PostToolUse (Edit/Write)**:
  - Valida sintaxe JS (via `node -e` no container n8n)
  - Valida sintaxe Python (`python -m py_compile`)
  - Valida `docker-compose.yml` (`docker compose config -q`)
- **PreToolUse (Bash)**:
  - Bloqueia/pede confirmação para comandos Docker destrutivos (`rm`, `rmi`, `compose down`, `system prune`)
- **Stop**:
  - Health check automático do router (`http://localhost:8091/health`)

---

## Comportamento Esperado do Codex

1. **Não pedir confirmação** para ações operacionais (reiniciar serviços, executar comandos, etc.) — executar direto e reportar o que foi feito
2. **Respostas curtas e objetivas** — sem explicações desnecessárias ou preambles
3. **Ler apenas arquivos necessários** — não explorar o projeto inteiro a cada conversa
4. **Não usar extended thinking** para tarefas simples
5. **Não usar web search** a menos que explicitamente pedido
6. **Commits frequentes** com mensagem descritiva — identidade: `Inside Sales Dev <dev@insidesales.local>`

---

## Caminhos Importantes
- Projeto: `C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES\`
- Venv router: `.venv-router\Scripts\activate`
- docker-compose: `C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES\docker-compose.yml`
- Logs: `C:\AUTOMACAO\logs\`
- Backups: `C:\AUTOMACAO\backups\`

---

## Estado em 2026-03-31
- 9 leads no CRM (3 novos, 6 qualificando)
- 138 interações registradas
- 895 ciclos de conhecimento executados
- 61 documentos indexados no CRM
- 22 regras de conhecimento ativas
- 27 contatos ignorados
\n\n\n
