# Radar IA Codex - WhatsApp Inside Sales

Execucao: 2026-05-01T03:03:33-03:00
Workspace: `C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES`
Maquina atual: PC CLS (`100.113.13.27`)
Outra ponta conhecida: PC LBN (`100.101.106.95`)
Modo: pesquisa, auditoria e recomendacao. Nenhuma alteracao de producao aplicada.

## Resumo executivo

Foram encontradas 6 novidades relevantes e 8 melhorias aplicaveis ao stack. A prioridade pratica nao e trocar a arquitetura; e corrigir pontos de observabilidade/MCP, testar evolucao controlada do n8n MCP, reduzir custo/latencia em chamadas OpenAI e melhorar RAG sem reescrever o fluxo.

Classificacao: `acao humana necessaria`

Motivo: o Git ja estava sujo antes desta execucao e o projeto opera em producao. Foram criados apenas relatorio, notificacao persistente e memoria da automacao.

## Fontes consultadas

- OpenAI tools / Remote MCP / Skills / tool search: https://developers.openai.com/api/docs/guides/tools
- OpenAI Docs MCP: https://developers.openai.com/learn/docs-mcp
- OpenAI Responses API migration: https://developers.openai.com/api/docs/guides/migrate-to-responses
- OpenAI Agents SDK: https://developers.openai.com/api/docs/guides/agents
- OpenAI model guide/catalog: https://developers.openai.com/api/docs/models
- Codex plan/features: https://help.openai.com/en/articles/11369540-codex-in-chatgpt
- n8n MCP workflow creation/update: https://blog.n8n.io/n8n-mcp-server/
- n8n node versions: https://docs.n8n.io/integrations/builtin/deprecated-and-versioned-nodes/
- n8n security bulletin 2026-02-25: https://community.n8n.io/t/security-bulletin-february-25-2026/270324
- n8n release notes: https://docs.n8n.io/release-notes/
- Evolution API releases: https://github.com/EvolutionAPI/evolution-api/releases
- Qdrant hybrid search: https://qdrant.tech/articles/hybrid-search/
- Qdrant current feature overview: https://qdrant.tech/
- OpenTelemetry Flask instrumentation: https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/flask/flask.html
- OpenTelemetry Python zero-code instrumentation: https://opentelemetry.io/docs/zero-code/python/

## Evidencia local do stack

- Docker ativo: `router`, `n8n`, `evolution`, `postgres`, `redis`, `minio`, `n8n-autoheal`.
- `router`: `attendant-router:latest`, Python 3.11.15, Flask 3.1.3, OpenAI SDK 2.31.0, health `healthy`.
- `n8n`: imagem `n8n-runnerless:2.11.3`, health `healthy`.
- `evolution`: imagem `atendai/evolution-api:latest`, HTTP 200 no endpoint raiz.
- `http://localhost:8091/health`: OK, com `routerTestGateEnforced=false`.
- `http://localhost:8091/metrics`: falhou inicialmente com HTTP 500 e depois respondeu OK; logs do container registraram `sqlite3.OperationalError: disk I/O error` e `unable to open database file` em `/metrics` e `/health`.
- Runtime DB real em `C:\AUTOMACAO\dados\router_runtime.sqlite`: 470 `route_logs`, 32 `response_cache`, 82 `rag_documents`, 23 `rag_chunks`, 267 `lead_memory`, 364 `conversation_history`, 14 `learning_events`.
- CRM real em `C:\AUTOMACAO\dados\crm_operacional.sqlite`: 12 leads, 696 interacoes, 109 itens em `learning_backlog`, 34 regras, 89 documentos.
- Decisoes de rota no runtime: `rag_claude=177`, `claude_direct=131`, `gpt_direct=87`, `audio_untranscribed=65`, `cache=10`; cache hit total aproximado de 2,1%.
- `router_service.py` tem `/metrics` em `router_service.py:3282` e `db()` aplica `PRAGMA journal_mode=WAL` a cada conexao em `router_service.py:956`.
- `multi_llm.py` ainda usa `chat.completions.create` em `multi_llm.py:313`, `:387`, `:510`, `:595`, com defaults `gpt-4o-mini` para caminhos OpenAI.
- `guardrails.js` ja aponta `gpt-5.4` para decisao do fluxo n8n.
- `.mcp.json` ainda referencia o caminho antigo `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\...`, nao o workspace atual em `CODEX_PROJECTS`.
- `router-decision.js` usa `ROUTER_BASE_URL || http://router:8091`; `router-learn.js` ainda contem `http://host.docker.internal:8091/learn-response`.
- `codex mcp list` nao executou: `codex.exe` existe via WindowsApps, mas retornou `Acesso negado`. A consulta OpenAI usou fallback web oficial.

## Novidades relevantes

### P1 - n8n MCP oficial para criar/atualizar workflows

Fonte: n8n blog, 2026-04-29.
Resumo: o MCP oficial do n8n agora cria e atualiza workflows diretamente na instancia, com validacao e execucao assistida.
Maturidade: primeira parte, preview/publicamente disponivel e mantido pelo n8n.
Compatibilidade: alta com n8n self-hosted, mas exige controle forte de credenciais e permissao.
Onde encaixa: workflow principal `zN3heKJVLO8w4dG6`, patches de `Router Decision`, `Repair Router Payload`, `Guardrails`, `Extract Reply`.
Problema que resolve: drift entre scripts versionados e workflow ativo, copy-paste de JSON, erro de typeVersion/node version.
Ganho esperado: acelerar correcao e auditoria do fluxo n8n, com menos erro manual.
Esforco: medio.
Risco: medio/alto se habilitado com escrita em producao sem backup.
Recomendacao: testar em branch/ambiente controlado; iniciar em modo leitura/inventario e so depois liberar escrita.

### P1 - Responses API + tools/MCP/skills para caminhos OpenAI

Fonte: OpenAI docs.
Resumo: Responses API e a superficie recomendada para agentes, tools, MCP, file search, skills e prompt templates; migracao pode ser incremental.
Maturidade: oficial e recomendada.
Compatibilidade: alta; OpenAI SDK local ja esta em 2.31.0.
Onde encaixa: `multi_llm.py` em extracao estruturada, resumo, lead score e fallback OpenAI.
Problema que resolve: uso legado de `chat.completions.create`, menos rastreabilidade de tool calls e prompts, menor controle de cache/prompt.
Ganho esperado: melhor versionamento de prompts, structured outputs mais robustos, possibilidade de `prompt_cache_key`, MCP/tools futuros.
Esforco: medio.
Risco: medio por impacto em respostas; deve ser feito por fluxo e com testes.
Recomendacao: testar em branch, com fixtures de mensagens sinteticas e comparacao de custo/qualidade.

### P1 - Qdrant hybrid search server-side / Query API

Fonte: Qdrant docs/artigo.
Resumo: Qdrant suporta busca hibrida densa + esparsa e Query API para combinar busca no servidor.
Maturidade: madura em Qdrant.
Compatibilidade: media/alta; projeto ja usa Qdrant local + `rank_bm25`.
Onde encaixa: camada RAG em `router_service.py`, ingestao de `rag_documents`/`rag_chunks`.
Problema que resolve: dependencia de BM25 local separado e possivel baixa cobertura: 82 documentos no runtime contra 23 chunks ativos.
Ganho esperado: melhor precisao de recuperacao e menor complexidade no roteador.
Esforco: medio.
Risco: medio; exige reindexacao controlada e teste de perguntas comerciais.
Recomendacao: testar em branch com colecao paralela e benchmark contra perguntas do stress test.

### P1 - Observabilidade Flask com OpenTelemetry/metricas robustas

Fonte: OpenTelemetry docs.
Resumo: instrumentacao Flask pode rastrear requisicoes, rotas, headers controlados, traces e metricas com pouco codigo ou zero-code.
Maturidade: madura.
Compatibilidade: alta com Flask.
Onde encaixa: `router_service.py`, `/route`, `/learn-response`, `/health`, `/metrics`, chamadas OpenAI/Anthropic/Qdrant/SQLite.
Problema que resolve: `/metrics` teve falha intermitente por SQLite; logs locais estao espalhados e dashboard depende do mesmo DB.
Ganho esperado: latencia por etapa, erro por dependencia, tempo de LLM/RAG/cache e alerta antes de queda operacional.
Esforco: baixo/medio.
Risco: baixo se iniciado com export console/file e sem PII.
Recomendacao: implementar agora em branch curta, com redacao de PII e fallback caso collector nao exista.

### P1 - Alertas de seguranca n8n e auditoria de versao

Fonte: n8n security bulletin e release notes.
Resumo: n8n publicou correcoes de severidade alta/critica; ramo stable patched em `>=2.9.3` para o boletim de 2026-02-25.
Maturidade: oficial.
Compatibilidade: alta.
Onde encaixa: imagem custom `n8n-runnerless:2.11.3`, workflow principal, Code nodes, Form/Webhook/AI nodes.
Problema que resolve: risco de RCE/sandbox escape em self-hosted se ficar defasado.
Ganho esperado: reducao de risco operacional e de vazamento de credenciais.
Esforco: baixo/medio.
Risco: medio por atualizar n8n em producao; precisa backup e teste.
Recomendacao: backlog prioritario para rotina segura de update: backup, export workflow, subir imagem em teste, validar inbound/outbound.

### P2 - OpenAI Docs MCP no Codex

Fonte: OpenAI Docs MCP.
Resumo: OpenAI fornece MCP read-only para consultar docs atuais dentro do agente.
Maturidade: oficial.
Compatibilidade: alta com Codex, mas `codex.exe` falhou com `Acesso negado` neste host.
Onde encaixa: esta propria automacao de radar, prompts de migracao OpenAI, validacao de modelos/tools.
Problema que resolve: reduz dependencia de web search comum e melhora rastreabilidade de docs OpenAI.
Ganho esperado: radar mais confiavel e repetivel.
Esforco: baixo se resolver permissao/execucao do Codex CLI.
Risco: baixo; docs MCP e somente leitura.
Recomendacao: colocar no backlog e corrigir acesso ao Codex CLI antes da proxima execucao profunda.

## Novidades descartadas

- Substituir o stack por workflow simples `AI Agent + Simple Memory + SerpAPI`: `DESCARTADO`. A memoria do projeto ja registrava que isso e prototipo/MVP e remove controles operacionais, CRM, guardrails e fallback.
- Evolution API Lite como substituicao imediata: `DESCARTADO`. Pode simplificar microservico, mas trocar Evolution em producao aumenta risco sem resolver gargalo atual comprovado.
- MCPs n8n terceiros nao oficiais: `DESCARTADO` para producao. O n8n agora tem caminho oficial; terceiros so fariam sentido para laboratorio isolado.
- GraphRAG pesado/frameworks agenticos gerais: `P3`. Pode ser util no futuro, mas hoje o gargalo e cobertura/qualidade do RAG e observabilidade, nao falta de framework.
- Atualizacao direta de n8n/Evolution em producao nesta execucao: `DESCARTADO` como acao automatica. Git sujo + producao ativa + necessidade de backup/teste.

## Melhorias recomendadas

| Prioridade | Recomendacao | Beneficio esperado | Esforco | Risco | Modulos impactados |
|---|---|---:|---:|---:|---|
| P0 | Corrigir `.mcp.json` para os bancos reais em `C:\AUTOMACAO\dados` ou workspace atual | MCP sqlite volta a auditar dados reais | Baixo | Baixo | `.mcp.json` |
| P1 | Estabilizar `db()` e endpoints read-only para evitar `PRAGMA journal_mode=WAL` por request | reduz falhas intermitentes em `/health` e `/metrics` | Baixo/medio | Baixo | `router_service.py` |
| P1 | Instrumentar router com OTel/metricas sem PII | rastreabilidade por dependencia e latencia | Medio | Baixo | `router_service.py`, `requirements-router.txt`, compose |
| P1 | Testar n8n MCP oficial em modo leitura e laboratorio | reduz drift e copy-paste de workflows | Medio | Medio | n8n, workflow principal |
| P1 | Criar benchmark RAG com Qdrant hybrid em colecao paralela | melhora precisao comercial e simplifica BM25 | Medio | Medio | `router_service.py`, ingestao RAG |
| P1 | Planejar migracao incremental de OpenAI paths para Responses API | prompts/versionamento/tooling melhores | Medio | Medio | `multi_llm.py` |
| P2 | Remover hardcode restante `host.docker.internal` em `router-learn.js` | elimina ambiguidade PC CLS/host legado | Baixo | Baixo | `router-learn.js` |
| P2 | Criar rotina de update seguro n8n/Evolution | reduz risco CVE e drift de node versions | Medio | Medio | `docker-compose.yml`, backups, workflow exports |

## Plano de implementacao recomendado

1. Preparar branch dedicada quando o Git estiver limpo ou com escopo separado: `radar/2026-05-01-observability-mcp`.
2. Fazer backup de `C:\AUTOMACAO\dados\*.sqlite`, export do workflow n8n e snapshot do `docker-compose.yml`.
3. Patch 1: corrigir `.mcp.json` para paths reais e validar MCP sqlite sem expor dados.
4. Patch 2: alterar `db()` para nao executar `PRAGMA journal_mode=WAL` em toda conexao de leitura; adicionar tratamento de erro em `/health` e `/metrics`.
5. Patch 3: adicionar metricas/traces sem PII para `/route`, LLM, Qdrant e SQLite.
6. Patch 4: laboratorio do n8n MCP oficial em modo controlado, sem permissao de escrita em producao inicialmente.
7. Patch 5: benchmark RAG Qdrant hybrid com conjunto de perguntas do stress test, comparando resposta, latencia e fonte recuperada.
8. Patch 6: prova de conceito Responses API em extracao estruturada ou lead score, nao no texto SDR principal.

## Acao humana necessaria

- Decidir se a proxima execucao deve abrir branch e aplicar os patches P0/P1.
- Resolver/autorizar o problema `codex.exe` via WindowsApps com `Acesso negado` para permitir `codex mcp list` e registro do OpenAI Docs MCP.
- Manter a restricao: nenhuma alteracao de fluxo WhatsApp/n8n em producao sem backup, Git controlado e validacao inbound/outbound.

\n
