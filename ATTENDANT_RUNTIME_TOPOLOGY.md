# Topologia Operacional do Atendente

## Regra estrutural
- `PC CLS` (`100.113.13.27`) é a origem unica das IAs operacionais do atendente.
- `PC CLS` (`100.113.13.27`) hospeda o Docker operacional do projeto do atendente.
- `PC LBN` (`100.101.106.95`) e somente interface interativa, coordenacao humana e distribuicao manual de prompts.
- O Docker do `PC LBN` nao faz parte do runtime real do atendente e deve ser tratado como invalido para este projeto.

## Consequencias obrigatorias
- Todo recrutamento operacional de IA deve apontar para `PC CLS`.
- Toda consulta de container, compose, runtime, webhook, banco ou servico do atendente deve apontar para o Docker do `PC CLS`.
- `PC LBN` nao pode ser tratado como origem de `n8n`, `Evolution`, `Router`, `watchdogs`, `sidecars` ou bridges operacionais do atendente.
- Qualquer fallback, reinicio, recovery ou watchdog deve preservar essa topologia.

## Onde esta regra deve existir

### 1. Configuracao de ambiente
- `.env`
- `.env.example`
- `docker-compose.yml`

Campos obrigatorios:
- `ATTENDANT_OPERATIONAL_HOST_ROLE=PC_CLS`
- `ATTENDANT_OPERATIONAL_HOST_IP=100.113.13.27`
- `ATTENDANT_OPERATIONAL_DOCKER_HOST_ROLE=PC_CLS`
- `ATTENDANT_OPERATIONAL_DOCKER_HOST_IP=100.113.13.27`
- `ATTENDANT_INTERACTIVE_HOST_ROLE=PC_LBN`
- `ATTENDANT_INTERACTIVE_HOST_IP=100.101.106.95`
- `ATTENDANT_INTERACTIVE_MODE_ONLY=true`
- `ATTENDANT_REJECT_LBN_AS_RUNTIME=true`
- `ATTENDANT_REJECT_LBN_DOCKER=true`

### 2. Decisao de IA
- `multi_llm.py`
- `router_service.py`
- `router-decision.js`
- `router-learn.js`
- `guardrails.js`
- `extract-reply.js`
- `build-fallback-reply.js`

Regras:
- todo provider LLM e todo fallback devem carregar metadado de topologia
- o runtime deve falhar cedo se a topologia operacional estiver configurada fora de `PC CLS`

### 3. Recrutamento de agentes auxiliares
- `claude_codex_autopilot.py`
- `claude_cowork_worker.py`
- `mcp_bridge_monitor.py`

Regras:
- os bridges devem expor a topologia em log/status
- a existencia desses agentes no `PC LBN` nao os torna parte do runtime real do atendente
- qualquer recrutamento operacional continua vinculado a `PC CLS`

### 4. Observabilidade
- logs do router
- logs de bootstrap dos clients LLM
- status da ponte Codex/Claude
- payloads do `n8n` quando houver roteamento/learn/send

## Pontos de decisao do ecossistema

### Decisao de IA
- `multi_llm.py`: escolhe Anthropic vs OpenAI e aplica fallback entre providers
- `router_service.py`: decide quando chamar IA, cache, RAG ou fallback
- `router-decision.js`: encaminha o evento do `n8n` para o router operacional
- `guardrails.js`, `extract-reply.js`, `build-fallback-reply.js`: moldam regras de autoenvio, fallback e texto final
- `claude_codex_autopilot.py` e `claude_cowork_worker.py`: recrutamento auxiliar Codex/Claude fora do pipeline principal

### Decisao de runtime e Docker
- `docker-compose.yml`: define os containers operacionais reais
- `send-message.js`: decide o endpoint do `Evolution`
- `router-decision.js` e `router-learn.js`: chamam `host.docker.internal`, portanto dependem do host do Docker operacional
- `README.md` e scripts de bootstrap: orientam de qual host e Docker o projeto sobe

## Regra de validacao
Uma mudanca so esta valida quando for possivel provar simultaneamente:
1. logs e status marcam `PC CLS` como host operacional
2. logs e status marcam `PC CLS` como host Docker operacional
3. `PC LBN` aparece apenas como host interativo
4. nenhum fluxo ou script tenta tratar o Docker do `PC LBN` como runtime do atendente
