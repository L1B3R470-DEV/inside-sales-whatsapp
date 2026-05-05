# Radar IA Codex - WhatsApp Inside Sales

Execucao: 2026-05-04T19:05:25-03:00
Workspace: `C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES`
Maquina atual: PC CLS (`100.113.13.27`)
Outra ponta conhecida: PC LBN (`100.101.106.95`)
Modo: pesquisa, auditoria, recomendacao e pequena configuracao de fonte Codex. Nenhuma alteracao de producao aplicada.
Classificacao: `novas melhorias relevantes encontradas`

## Resumo executivo

Foram encontradas 9 novidades relevantes e 11 melhorias aplicaveis ao stack. A leitura pratica mudou desde a rodada anterior: o `.mcp.json` do projeto ja esta corrigido, o bug SQLite do router ja foi mitigado, e o bloqueio de `number` vazio parece efetivo apos a correcao mais recente. Os riscos atuais mais concretos sao: n8n local ainda em `2.11.3`, banco n8n com 48.3 GB, Evolution em `2.2.3` com ruido recente de sessao/decriptacao, e RAG com baixa superficie ativa para o volume de conhecimento do CRM.

Acao executada fora da producao: o OpenAI Docs MCP foi adicionado ao Codex CLI global (`openaiDeveloperDocs`, URL `https://developers.openai.com/mcp`). A sessao atual nao recebeu as tools dinamicamente, entao esta rodada ainda usou fallback web oficial da OpenAI; a proxima execucao deve conseguir partir do MCP.

## Fontes consultadas

- OpenAI Models / latest model catalog: https://developers.openai.com/api/docs/models
- OpenAI GPT-5.5 model card: https://developers.openai.com/api/docs/models/gpt-5.5
- OpenAI Responses API migration: https://developers.openai.com/api/docs/guides/migrate-to-responses
- OpenAI Responses tools / remote MCP: https://openai.com/index/new-tools-and-features-in-the-responses-api/
- OpenAI Agents SDK update: https://openai.com/index/the-next-evolution-of-the-agents-sdk/
- n8n instance-level MCP server: https://docs.n8n.io/advanced-ai/mcp/accessing-n8n-mcp-server/
- n8n MCP Server Trigger: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger/
- n8n releases: https://github.com/n8n-io/n8n/releases
- n8n SSRF protection: https://docs.n8n.io/hosting/securing/ssrf-protection/
- Evolution API releases: https://github.com/EvolutionAPI/evolution-api/releases
- Qdrant hybrid queries: https://qdrant.tech/documentation/search/hybrid-queries/
- Qdrant hybrid search with reranking: https://qdrant.tech/documentation/advanced-tutorials/reranking-hybrid-search/
- MCP production-readiness paper: https://arxiv.org/abs/2603.13417

## Evidencia local do stack

- `CWD` confirmado: `C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES`.
- Git antes da atualizacao documental: `main...origin/main`, sem alteracoes reportadas por `git status --short`.
- `docker compose config -q`: OK.
- Containers ativos: `router`, `n8n`, `evolution`, `evolution-postgres`, `evolution-redis`, `evolution-minio`, `n8n-autoheal`.
- Endpoints: `router /health` 200, `router /metrics` 200, `n8n /healthz` 200, Evolution `/` 200.
- Evolution reporta versao `2.2.3`; release upstream mais recente observado: `v2.3.7`.
- n8n local: `n8n-runnerless:2.11.3`; release upstream observado no GitHub em 2026-05-04: `2.18.7`.
- Node dentro do n8n: `v24.13.1`.
- Router: Python `3.11.15`, OpenAI SDK `2.33.0`, Flask `3.1.3`, qdrant-client `1.17.1`, psycopg `3.3.4`, rank-bm25 `0.2.2`.
- `C:\AUTOMACAO\dados\router_runtime.sqlite`: 525 `route_logs`, 32 `response_cache`, 23 `rag_chunks`, 82 `rag_documents`, 274 `lead_memory`, 420 `conversation_history`.
- `route_logs` com `number` vazio: 175 historicos; depois da correcao `no_recipient` de 2026-05-04 14:10 -03, foram 7 rotas novas e 0 com `number` vazio.
- `C:\AUTOMACAO\dados\crm_operacional.sqlite`: 836 `interactions`, 7 `leads`, 37 itens abertos acionaveis em `learning_backlog`, 43 `knowledge_rules`, 91 `knowledge_documents`.
- Historico preservado no CRM: 600 interacoes antigas com `number` vazio e 363 com `text` vazio seguem marcadas/filtradas, nao apagadas.
- Banco do n8n: `/home/node/.n8n/database.sqlite` com 48.3 GB.
- Disco C: 10.23 GB livres no momento da execucao.
- Logs das ultimas 2h: router/n8n sem novo erro SQLite relevante observado; Evolution registrou `SessionError`, `Bad MAC`, falha de decriptacao e timeouts Baileys.
- `.mcp.json` do projeto ja aponta para bancos reais em `C:\AUTOMACAO\dados` e executaveis MCP do Python 3.14.
- `codex mcp list` inicialmente nao tinha servidores; apos a acao, `openaiDeveloperDocs` aparece como `enabled`.

## Novidades relevantes

### P1 - n8n 2.18.x + MCP/AI Builder mais maduro

Nome: n8n 2.18.x e instance-level MCP.
Fonte: n8n releases e docs MCP.
Resumo tecnico: a linha atual do n8n expande MCP para gerenciamento/construcao de workflows e traz correcoes recentes, incluindo redacao em caminho de teste de webhook.
Maturidade: oficial, em evolucao rapida.
Compatibilidade: alta, mas exige ensaio porque o projeto usa imagem custom `n8n-runnerless:2.11.3`.
Onde encaixa: workflow principal `zN3heKJVLO8w4dG6`, auditorias de node, validacao de patches n8n e reducao de copy-paste de JSON.
Problema que resolve: drift entre workflow ativo e scripts, falta de automacao segura para inspecionar/editar n8n.
Ganho esperado: menos erro manual e melhor ciclo de auditoria.
Esforco estimado: medio.
Risco: medio/alto se escrito direto em producao.
Prioridade: P1.
Recomendacao: testar em branch/laboratorio, primeiro leitura/inventario; liberar escrita somente com export, backup e rollback.

### P1 - n8n SSRF protection

Nome: protecao SSRF n8n, disponivel desde `2.12.0`.
Fonte: docs n8n SSRF protection.
Resumo tecnico: n8n passa a validar requisicoes HTTP controlaveis por workflows contra faixas bloqueadas/permitidas, incluindo redirects e DNS.
Maturidade: oficial.
Compatibilidade: media, porque o stack precisa acessar nomes internos Docker como `router`, `evolution`, `postgres` e endpoints locais.
Onde encaixa: `docker-compose.yml`, ambiente n8n e workflows com HTTP Request/Webhook.
Problema que resolve: reducao de risco de chamadas indevidas para recursos internos por node controlavel.
Ganho esperado: defesa adicional contra abuso do n8n em self-hosted.
Esforco estimado: medio.
Risco: medio, por poder bloquear chamadas legitimas se allowlist for mal definida.
Prioridade: P1.
Recomendacao: aplicar somente apos upgrade testado, com allowlist explicita dos servicos internos necessarios.

### P1 - Evolution API v2.3.7

Nome: Evolution API v2.3.7.
Fonte: releases oficiais GitHub EvolutionAPI.
Resumo tecnico: release upstream cita ajustes de `normalizeJid`, compatibilidade Node 18+ native fetch, fixes de media/base64/filename/caption e conversoes LID/phoneNumber em certos fluxos.
Maturidade: oficial, mas precisa validar com dados reais da instancia.
Compatibilidade: media/alta; local roda `atendai/evolution-api:latest` expondo versao `2.2.3`.
Onde encaixa: container `evolution`, instancia `ATENDIMENTO_VENDAS_CLEAN`, rotas de media, LID e mensagens WhatsApp.
Problema que resolve: pode reduzir risco em pontos que ja deram incidentes: LID, media, filename e compatibilidade Baileys.
Ganho esperado: menos falha operacional e melhor suporte a mensagens recentes.
Esforco estimado: medio.
Risco: medio/alto por envolver WhatsApp em producao e banco Postgres.
Prioridade: P1.
Recomendacao: testar em staging/backup primeiro; nao atualizar producao automaticamente.

### P1 - Qdrant hybrid queries e reranking

Nome: Qdrant hybrid search / Query API / reranking.
Fonte: docs Qdrant.
Resumo tecnico: Qdrant permite combinar vetores densos e esparsos com `prefetch`, fusao e re-ranking, reduzindo dependencia de BM25 local separado.
Maturidade: madura em Qdrant.
Compatibilidade: alta; router ja usa Qdrant local e `rank_bm25`.
Onde encaixa: `router_service.py`, ingestao `rag_documents`/`rag_chunks`, perguntas comerciais do stress test.
Problema que resolve: RAG atual tem apenas 23 chunks ativos e mistura busca vetorial com BM25 local, aumentando complexidade e possivel perda de recall.
Ganho esperado: melhor recuperacao de produto/regra comercial e menor codigo custom.
Esforco estimado: medio.
Risco: medio por exigir reindexacao paralela e benchmark.
Prioridade: P1.
Recomendacao: testar em colecao paralela, sem substituir a colecao atual ate comparar latencia, fonte recuperada e resposta final.

### P1 - Responses API para extracao/lead score antes do texto SDR

Nome: OpenAI Responses API.
Fonte: OpenAI migration guide e docs de tools.
Resumo tecnico: Responses e a superficie recomendada para apps agenticos, com tools, MCP, estado, structured outputs e migracao incremental a partir de Chat Completions.
Maturidade: oficial.
Compatibilidade: alta; OpenAI SDK do router esta em `2.33.0`.
Onde encaixa: `multi_llm.py` nos caminhos de extracao estruturada, lead score e sumarizacao, antes de mexer no texto SDR principal.
Problema que resolve: `multi_llm.py` ainda chama `chat.completions.create`; isso limita uso de estado, tools e padroes atuais.
Ganho esperado: saidas estruturadas mais previsiveis, melhor rastreabilidade e base futura para tools/MCP.
Esforco estimado: medio.
Risco: medio se mexer no texto ao lead; baixo/medio se limitar a lead score/extracao.
Prioridade: P1.
Recomendacao: testar em branch com fixtures de mensagens e comparacao de custo/qualidade.

### P2 - GPT-5.5 e politica de modelos

Nome: GPT-5.5 / GPT-5.4 / GPT-5.4-mini.
Fonte: OpenAI model catalog.
Resumo tecnico: GPT-5.5 e indicado como frontier para trabalho profissional complexo; GPT-5.4 e GPT-5.4-mini ficam mais baratos para cargas de menor latencia/custo.
Maturidade: oficial.
Compatibilidade: media; `guardrails.js` usa `gpt-5.4`, enquanto `multi_llm.py` ainda usa `gpt-4o-mini` por default.
Onde encaixa: avaliacao offline, nao troca direta do atendimento principal.
Problema que resolve: pode melhorar classificacao/analise dificil, mas aumenta custo se usado em toda mensagem.
Ganho esperado: melhor qualidade em casos complexos se roteado seletivamente.
Esforco estimado: baixo/medio para benchmark.
Risco: medio por custo e drift de tom.
Prioridade: P2.
Recomendacao: colocar no backlog de benchmark; nao substituir o SDR principal por GPT-5.5 sem A/B local e limite de custo.

### P2 - Agents SDK com sandbox, skills e AGENTS.md

Nome: OpenAI Agents SDK atualizado.
Fonte: OpenAI Agents SDK update.
Resumo tecnico: o SDK ganhou primitives para workspace controlado, tools, MCP, skills, AGENTS.md, shell e apply patch em ambiente sandbox.
Maturidade: oficial, util para automacoes de engenharia.
Compatibilidade: alta com automacoes Codex; baixa para substituir o runtime WhatsApp.
Onde encaixa: automacao de radar, validadores, sidecars de auditoria e geracao de patches sugeridos.
Problema que resolve: padroniza auditorias recorrentes e reduz improviso de ferramentas.
Ganho esperado: automacoes mais reprodutiveis.
Esforco estimado: medio.
Risco: baixo se limitado a laboratorio/relatorios; medio se ganhar escrita em producao.
Prioridade: P2.
Recomendacao: backlog; usar como arquitetura de automacao, nao como substituto do router/n8n.

### P0 - OpenAI Docs MCP para Codex

Nome: OpenAI Docs MCP.
Fonte: OpenAI docs/Codex CLI.
Resumo tecnico: servidor MCP read-only para consultar docs oficiais da OpenAI a partir do Codex.
Maturidade: oficial.
Compatibilidade: alta; `codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp` executou com sucesso.
Onde encaixa: esta automacao e futuras migracoes OpenAI.
Problema que resolve: reduz dependencia de web search comum para docs OpenAI.
Ganho esperado: pesquisa mais confiavel e repetivel.
Esforco estimado: baixo.
Risco: baixo; read-only.
Prioridade: P0.
Recomendacao: implementado agora no CLI global; validar na proxima sessao se as tools MCP aparecem no ambiente.

### P2 - Checklist de producao para MCPs

Nome: padroes de producao para MCP - identidade, timeout, erros estruturados e observabilidade.
Fonte: paper arXiv `2603.13417`.
Resumo tecnico: o paper aponta lacunas praticas em MCPs de producao: propagacao de identidade, orcamento adaptativo de timeout, erros estruturados e observabilidade.
Maturidade: pesquisa recente; aplicavel como checklist, nao como dependencia.
Compatibilidade: alta como criterio de desenho para MCP interno.
Onde encaixa: `mcp_bridge_monitor.py`, possivel n8n MCP, MCP sqlite e automacoes Codex.
Problema que resolve: evita MCP virar caixa-preta sem timeout, sem escopo e sem erro legivel.
Ganho esperado: menos falhas silenciosas em automacoes recorrentes.
Esforco estimado: baixo/medio.
Risco: baixo se usado como checklist.
Prioridade: P2.
Recomendacao: backlog; incorporar nos proximos MCPs/tools internos.

## Novidades descartadas

- Substituir o stack por framework agentico generico: `DESCARTADO`. Aumenta complexidade e ignora guardrails, CRM, Evolution e n8n existentes.
- GPT-5.5 para todas as mensagens do SDR: `DESCARTADO` por enquanto. Custo alto e risco de drift; melhor roteamento seletivo.
- MCPs n8n terceiros como caminho principal: `DESCARTADO` para producao. O caminho oficial do n8n e mais coerente.
- Atualizacao direta de n8n/Evolution nesta execucao: `DESCARTADO` como acao automatica. Exige backup, staging e janela.
- Evolution API Lite/substituicao de WhatsApp engine: `DESCARTADO` por enquanto. Nao resolve os gargalos provados de forma mais segura do que atualizar/testar Evolution atual.
- Hype de GitHub trending sem manutencao ou sem Windows/self-host claro: `DESCARTADO`.

## Melhorias recomendadas

| Prioridade | Recomendacao | Beneficio esperado | Esforco | Risco | Modulos impactados |
|---|---|---:|---:|---:|---|
| P1 | Criar plano de upgrade n8n `2.11.3` -> release atual em laboratorio | seguranca, MCP mais maduro, redacao e correcoes recentes | Medio | Medio | `docker-compose.yml`, `docker/n8n-runnerless`, volume `ai_n8n_data` |
| P1 | Preparar SSRF protection com allowlist interna apos upgrade n8n | reduz risco de uso indevido de HTTP Request nodes | Medio | Medio | n8n env, workflows HTTP |
| P1 | Testar Evolution v2.3.7 em staging com dump Postgres e rollback | pode reduzir riscos de LID/media/JID e acompanhar upstream | Medio | Medio/alto | Evolution, Postgres, Redis, MinIO |
| P1 | Criar alerta para `SessionError`, `Bad MAC`, decrypt e timeout Baileys | detecta degradacao WhatsApp antes de impacto comercial | Baixo/medio | Baixo | logs Evolution, `human-alert-monitor.ps1` ou monitor novo |
| P1 | Benchmark Qdrant hybrid em colecao paralela | melhora RAG e reduz BM25 custom no router | Medio | Medio | `router_service.py`, ingestao RAG |
| P1 | POC Responses API em lead score/extracao estruturada | moderniza OpenAI sem mexer primeiro na resposta ao lead | Medio | Medio | `multi_llm.py`, fixtures de teste |
| P1 | Planejar manutencao do banco n8n de 48.3 GB | reduz risco de disco e instabilidade SQLite n8n | Medio | Medio/alto | volume `ai_n8n_data`, backups |
| P2 | Instrumentar router com traces/metricas sem PII | latencia e erro por etapa: LLM, RAG, SQLite, Evolution | Medio | Baixo | `router_service.py`, `requirements-router.txt` |
| P2 | Validar OpenAI Docs MCP na proxima sessao | fontes oficiais OpenAI via MCP em vez de web fallback | Baixo | Baixo | Codex CLI config |
| P2 | Limpar hardcodes antigos de caminho/pastas em scripts auxiliares | evita regressao para pasta antiga | Baixo/medio | Baixo | scripts PS/JS auxiliares |
| P2 | Criar teste E2E para `no_recipient` nao gerar `route_logs.number=''` | impede regressao ja historicamente recorrente | Baixo | Baixo | `router_service.py`, fixtures |

## Plano de implementacao recomendado

1. Abrir branch dedicada somente quando o escopo estiver limpo: `radar/2026-05-04-n8n-evolution-rag`.
2. Antes de qualquer deploy: exportar workflow n8n, backup de `C:\AUTOMACAO\dados`, dump Postgres Evolution e snapshot do compose.
3. Criar copia de laboratorio do n8n, testar imagem atual contra workflow principal e validar inbound/outbound controlado.
4. Depois do upgrade n8n em laboratorio, testar MCP em modo limitado e SSRF protection com allowlist dos servicos internos reais.
5. Criar alerta de logs Evolution sem reiniciar instancia: procurar `SessionError`, `Bad MAC`, `failed to decrypt` e `Timed Out`.
6. Subir Evolution v2.3.7 em staging com dados copiados, validar QR/conexao, LID, media e envio controlado; so depois planejar producao.
7. Criar colecao Qdrant paralela com dense+sparse e comparar contra perguntas do stress test.
8. Implementar POC Responses API apenas em extracao/lead score e comparar JSON, latencia e custo contra `chat.completions.create`.
9. Planejar manutencao do banco n8n de 48.3 GB em janela propria; nao executar VACUUM/compactacao sem espaco, backup e rollback.

## Acao humana necessaria

- Aprovar uma janela para laboratorio/backup de n8n e Evolution antes de qualquer atualizacao.
- Decidir se a proxima execucao recorrente deve abrir branch e implementar apenas itens de baixo risco: alerta Evolution, teste `no_recipient` e POC Responses em fixtures.
- Manter a restricao operacional: nenhuma mudanca no fluxo WhatsApp/n8n em producao sem backup, Git controlado e validacao inbound/outbound.
