# COLLAB STATE

Atualizado em: 2026-05-04 12:12:00 -03:00

## Estado atual

Projeto migrado para:
C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES

## Responsabilidades

Codex:
- executar alteracoes no projeto
- validar stack e runtime
- integrar respostas de sidecars
- manter rastreabilidade final

Claude Code:
- revisar fluxo e payloads
- procurar lacunas em guardrails/router/n8n
- propor correcao minima quando solicitado
- nao executar mudanca em producao sem task explicita

## Proxima tarefa recomendada

Executar validacao operacional completa do checklist em FLOW_AUDIT_2026-04-28.md e atacar P0:
- garantir um unico router em 8091
- validar inbound real de numero nao bloqueado ate outbound Evolution
- confirmar dashboard coerente

## Ultima decisao conhecida

Reset completo do numero homologado 557588340000 nao era necessario para liberar atendimento global. So limpar se houver evidencia nova de contaminacao.
## Bloqueio runtime registrado em 2026-04-28

Docker Desktop/engine estava parado durante a migracao:
- com.docker.service = Stopped
- pipes Docker ausentes
- n8n/router recusando conexao

Proxima sessao deve tratar isso como P0 antes de qualquer afirmacao de runtime 100%.

## Radar IA Codex em 2026-05-01 03:03 -03

Execucao inicial da automacao `radar-ia-auditor-evolutivo-do-stack-whatsapp-inside-sales` concluida sem alterar producao.

Artefatos:
- `ANALISES/RADAR_IA_CODEX.md`
- `NOTIFICACAO_RADAR_IA.md`

Achados principais:
- stack Docker operacional em PC CLS `100.113.13.27`;
- Git ja estava sujo antes da execucao;
- `/metrics` do router apresentou falha intermitente SQLite antes de voltar a responder;
- `.mcp.json` ainda aponta para paths antigos fora do workspace atual;
- recomendacao pratica: branch/backup antes de corrigir MCP, observabilidade e testes do n8n MCP oficial.

## Monitor de memorias Codex em 2026-05-01 03:08 -03

Execucao recorrente `monitor-de-memorias-e-correcoes-codex`:
- criou `.collab/README.md` apenas como ponteiro de compatibilidade para o fluxo ativo `collab/`;
- manteve `collab/` como fonte operacional de protocolo/estado, sem migracao ou renomeacao;
- corrigiu `.mcp.json` para executaveis MCP instalados no Python 3.14 e bancos runtime em `C:\AUTOMACAO\dados`;
- confirmou PC CLS `100.113.13.27`;
- validou `/health` e `/metrics` do router repetidamente apos erro SQLite transitorio;
- manteve pendencias humanas: teste inbound WhatsApp real e decisao sobre `learning_backlog`.

## Correcao CRM / backlog / SQLite em 2026-05-01 04:40 -03

Execucao operacional solicitada por Rodrigo:
- causa raiz do CRM estagnado: tarefa `CRM_CYCLE_N8N` apontava para `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES`, e o ciclo CRM gravava em `/work/crm_operacional.sqlite` em vez do runtime `C:\AUTOMACAO\dados\crm_operacional.sqlite`;
- corrigidos `run-crm-cycle*.ps1`, `crm_cycle_engine.py` e `crm_sheet_sync.py` para usar o projeto vigente e o CRM runtime;
- criados wrappers no caminho antigo para compatibilidade com a tarefa `SISTEMA` existente;
- criada tarefa redundante `CRM_CYCLE_N8N_USER` como usuario `User`, validada com `LastTaskResult=0`;
- ciclo CRM importou 59 interacoes, depois teste controlado importou mais 1; CRM agora tem 756 interacoes e ultima interaction em `2026-05-01T07:39:24.018Z`;
- backlog aberto caiu de 121 para 47; fechamentos preservaram historico com status `auto_closed_empty`, `auto_closed_test_artifact` e `auto_closed_duplicate`;
- leads elegiveis do dashboard ficaram em 5; numeros internos/teste/bloqueados foram excluidos de relatorio B2B via `b2b_reporting_exclusions`;
- router recebeu retry/timeout para conexao SQLite e dashboard passou a ler `b2b_eligible_leads`;
- `docker-compose.yml` conectou o router tambem a rede legada `projetoatendimentowhatsappinsidesales_default`, restaurando `n8n -> router` e `router -> postgres/evolution/redis`;
- teste controlado no webhook n8n com `557588340000` gerou execution `7943`, route_log `635` e outbound Evolution `DELIVERY_ACK`;
- logs do router apos correcao sem novos matches de erro/warning/sqlite/postgres.

Pendencia residual:
- disco C ainda critico em 98.5% usado; prune Docker seguro removeu cache/imagens nao usadas sem tocar volumes, mas o volume `ai_n8n_data` segue grande e exige manutencao planejada se o espaco voltar a causar risco.

## Saneamento Git em 2026-05-04

Execucao operacional solicitada para resolver worktree sujo:
- confirmado PC CLS `100.113.13.27`, branch `main` e origem `https://github.com/L1B3R470-DEV/inside-sales-whatsapp.git`;
- removido `.git/index.lock` obsoleto apos encerrar processos Git travados da sessao;
- segregados artefatos locais/volateis em `.gitignore` (`qr_reconectar.html`, `.fuse_hidden*`, bancos locais, `sms-receive-module/`, `node_modules/`, dumps/raws de relatorio e `stress-test-runs/`);
- restaurados arquivos textuais corrompidos por normalizacao defeituosa a partir de blobs bons do object database Git;
- mantido backup temporario da versao corrompida em `%LOCALAPPDATA%\Temp\inside_sales_git_repair_20260504_111103`.

Proxima regra operacional:
- antes de novo commit grande, executar `git diff --cached --check`, validadores de sintaxe e revisar se algum artefato de runtime/sessao entrou no stage.

## Correcao Guardrails no_recipient em 2026-05-04

Execucao recorrente `monitor-de-memorias-e-correcoes-codex`:
- causa raiz confirmada para novas interacoes CRM com `number` vazio: o Code node `Guardrails` persistia `customerProfiles[recipientNumber]` e `customerHistory[recipientNumber]` mesmo quando `recipientNumber` era vazio apos `blockReason='no_recipient'`;
- corrigido `guardrails.js` para gravar perfil/historico apenas quando houver `recipientNumber`;
- workflow n8n ativo `zN3heKJVLO8w4dG6` atualizado no node `Guardrails` com backup local em `C:\AUTOMACAO\backups\n8n_guardrails_node_fix_20260504_120818`;
- n8n reiniciado e validado com `/healthz 200`.

Pendencia residual:
- nao foi feita limpeza historica das 363 interacoes CRM antigas com texto vazio nem das entradas antigas com numero vazio; qualquer saneamento retroativo precisa de politica aprovada e backup especifico.

## Correcao SQLite router em 2026-05-04

Execucao recorrente `monitor-de-memorias-e-correcoes-codex`:
- causa raiz de falha intermitente em `/health` e `/metrics`: `db()` reexecutava `PRAGMA journal_mode=WAL` em toda conexao SQLite; em janela de carga isso gerou `sqlite3.OperationalError: unable to open database file` e HTTP 500 temporario;
- corrigido `router_service.py` para configurar WAL uma unica vez por processo com lock, aplicar `busy_timeout` antes e fechar conexao aberta quando uma tentativa falhar;
- router reconstruido e recriado com `docker compose up -d --build router`;
- validacao pos-deploy: `/health` 10/10 HTTP 200, `/metrics` 10/10 HTTP 200, container `router` healthy e sem novos `sqlite_db_open_retry`/`OperationalError` nos logs apos o restart.

Pendencia residual:
- disco C e banco SQLite do n8n continuam criticos; nao executar manutencao/compactacao sem janela e backup especifico.

## Saneamento Evolution/Compose em 2026-05-04 13:50 -03

Execucao operacional:
- ordem aplicada: auditar PC/Git/collab -> diagnosticar logs e schema -> corrigir `Media.fileName` -> consolidar Compose -> saneamento seguro de disco -> validar endpoints/logs/Git;
- PC atual confirmado como PC CLS `100.113.13.27`; Git iniciou limpo em `main`/`origin/main`;
- `Media_fileName_key` era um indice unico indevido para `public."Media"."fileName"`; WhatsApp permite repeticao de nome de arquivo por contato e `messageId` ja e unico;
- backup PostgreSQL antes da alteracao: `C:\AUTOMACAO\backups\evolution_media_filename_fix_20260504_134815\evolution_pre_media_filename_fix_20260504_134815.sql`;
- removido o indice unico `Media_fileName_key` e criado `Media_fileName_idx` nao unico; validado com insert duplicado em transacao e rollback;
- `docker-compose.yml` passou a apontar Postgres, Redis, Evolution, MinIO e n8n para os volumes reais de producao como volumes externos;
- containers legados foram apenas parados e renomeados com sufixo `legacy-20260504_134957`, sem apagar dados;
- novos containers `postgres`, `redis`, `minio`, `evolution`, `n8n` e `n8n-autoheal` subiram pelo compose atual e agora todos apontam para `C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES\docker-compose.yml`;
- removidos apenas 4 volumes vazios do compose atual antigo, todos com 4 KB e 0 arquivos; cache Docker de build ficou sem reclaimable;
- Evolution API validada com instancia `ATENDIMENTO_VENDAS_CLEAN` em estado `open`.

Validacao:
- `router /health`, `router /metrics`, `n8n /healthz` e Evolution `/` retornaram 200;
- `Message` tem 20522 linhas e `Media` 758 linhas apos a transicao;
- logs apos a correcao/consolidacao sem novo `Media_fileName_key`, sem Bad MAC/SessionError/decrypt e sem erro Postgres novo;
- `docker compose ps` mostra todos os servicos principais no compose atual.

Pendencia residual:
- disco C segue critico (~9.54 GB livres) porque o gargalo real e o `ai_n8n_data` com cerca de 49 GB, especialmente `database.sqlite` de 48.3 GB; compactacao/VACUUM exige janela, backup e mais espaco livre.
- os containers `*-legacy-20260504_134957` ficaram parados como rollback operacional; remover depois de uma janela estavel e decisao explicita.
- os erros de query mal cotada desta rodada ficaram registrados no log do Postgres, sem alteracao de dados.

## Bloqueio precoce no_recipient no router em 2026-05-04 14:10 -03

Execucao recorrente `monitor-de-memorias-e-correcoes-codex`:
- causa raiz residual: mensagens `@lid` sem mapeamento numerico ainda entravam em `route_message`, gerando `route_logs.number=''` antes do Guardrails bloquear o envio;
- corrigido `router_service.py` para retornar `routeDecision='no_recipient'` antes de LLM/RAG/cache quando o numero nao for resolvido;
- a resposta bloqueada preserva campos esperados pelo n8n/Guardrails e evita gravacao de `route_logs` sem numero.

Pendencia residual:
- as entradas historicas com `number` vazio nao foram alteradas; saneamento retroativo continua dependendo de politica aprovada e backup especifico.

## Bloqueio de history vazio no ciclo CRM em 2026-05-04 16:05 -03

Execucao recorrente `monitor-de-memorias-e-correcoes-codex`:
- causa raiz residual: o `crm_cycle_engine.py` ja ignorava `customerProfiles` com chave vazia, mas ainda importava `customerHistory['']` para `interactions`;
- corrigido o loop de importacao de historico para normalizar `number` e ignorar chave vazia antes do `INSERT OR IGNORE`;
- a correcao evita novas `interactions.number=''` geradas por historico n8n antigo sem apagar dados historicos.

Pendencia residual:
- as 600 interacoes historicas com `number` vazio e as 363 com `text` vazio nao foram alteradas; saneamento retroativo continua dependendo de politica aprovada e backup especifico.

## Politica aplicada para backlog/KPIs e STRESS_CLIENT_SETOR em 2026-05-04 17:59 -03

Execucao operacional apos decisao do usuario:
- politica aprovada: fechar no `learning_backlog` apenas teste, duplicado, vazio, sem pergunta real, dado solto ou artefato sem valor comercial; manter aberto o que for pergunta real de lead, melhoria de resposta ou contexto comercial acionavel;
- backup pontual antes da alteracao: `C:\AUTOMACAO\backups\crm_saneamento_politica_20260504_175900`;
- `learning_backlog`: 64 abertos antes, 27 fechados por status auditaveis e 37 abertos restantes;
- criadas tabelas de auditoria `learning_backlog_triage_audit` e `interaction_quality_flags` no CRM runtime;
- historico preservado: nenhuma linha de `interactions` foi apagada ou sobrescrita;
- 605 interacoes historicas com `number`/`text` vazio foram marcadas com `flag='exclude_from_kpi'`;
- criada view `v_interactions_kpi_clean` para KPIs sem dados historicos vazios e view `v_learning_backlog_open_actionable` para backlog acionavel;
- relatorio local gerado em `C:\AUTOMACAO\logs\crm_saneamento_politica_20260504_175941.json`;
- `STRESS_CLIENT_SETOR` foi apenas desconectada por logout da Evolution API, sem remover a instancia; validado `STRESS_CLIENT_SETOR=close` e `ATENDIMENTO_VENDAS_CLEAN=open`.

Pendencia residual:
- os containers `*-legacy-20260504_134957` ainda nao devem ser removidos antes de 24-48h de estabilidade;
- disco C e `n8n database.sqlite` seguem exigindo janela propria de manutencao.

## Saneamento de risco comercial em 2026-05-05 08:40 -03

Execucao operacional:
- PC atual confirmado como PC CLS `100.113.13.27`; CWD validado em `C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES`;
- Git iniciou limpo em `main...origin/main`; backup antes de alteracoes em `C:\AUTOMACAO\backups\risk_commercial_fix_20260505_082016`;
- `docker-compose.yml` reduziu pressao do n8n/Evolution: `DATABASE_SAVE_DATA_HISTORIC=false`, `DB_SQLITE_POOL_SIZE=1`, `EXECUTIONS_DATA_SAVE_ON_SUCCESS=none` e `EXECUTIONS_DATA_PRUNE_MAX_COUNT=1000`;
- `auto_heal_n8n.py` passou a curar execucoes presas em `running`, `new` e `crashed`, com `busy_timeout=300000` e auditoria sob demanda;
- execucoes n8n `8246` (`crashed`) e `8247` (`new`) foram marcadas como `failed`, `finished=1`, com auditoria `status_timeout:*`;
- `crm_cycle_engine.py` colocou 37 itens `learning_backlog` em `queued_human_review`, marcou 4 leads antigos em `follow_up_humano_pendente` e passou a preservar esse estado contra sobrescrita por `staticData`;
- criada reconciliacao `evolution_crm_reconcile.py` para importar eventos reais da Evolution PostgreSQL ao CRM apos o ciclo n8n, cobrindo restart/queda sem depender apenas de `workflow.staticData`;
- corrigido encoding UTF-8 da reconciliacao e removidos, com auditoria, 74 registros malformados e 8 leads internos criados na primeira rodada de ajuste;
- lead `556974009750` recebeu resposta de recuperacao pelo Evolution apos inbound `Oi` perdido na janela de restart; envio validado no PostgreSQL com status `DELIVERY_ACK`;
- tarefa agendada duplicada `CRM_CYCLE_N8N_USER` foi parada e desativada para reduzir concorrencia/`SQLITE_BUSY`; `CRM_CYCLE_N8N` continua ativa e aponta para wrapper da pasta antiga que chama o script vigente neste projeto.

Validacao:
- `python -m py_compile` OK para `auto_heal_n8n.py`, `crm_cycle_engine.py` e `evolution_crm_reconcile.py`;
- `docker compose config -q` OK;
- endpoints `router /health`, `router /metrics`, `n8n /healthz` e Evolution `/` retornaram 200;
- containers principais em execucao; `router` e `n8n` healthy;
- n8n sem execucoes `running/new/crashed`; auditoria confirmou 2 heals para `8246/8247`;
- router sem `recipient_unresolved` novo desde o restart; ultimo `route_log` valido com `number=556974009750`;
- CRM final: `learning_backlog.open=0`, `queued_human_review=37`, `follow_up_humano_pendente=4`, `leads=8`;
- Evolution apos restart: 0 `failed_to_decrypt`, 0 `Bad MAC`, 0 `SessionError/No matching sessions`, 0 `stream 503`; restou apenas timeout Baileys isolado de keepalive em log.

Pendencia residual:
- nao executar `VACUUM`/compactacao do `ai_n8n_data` em producao com cerca de 10 GB livres para banco SQLite de ~48.3 GB; exige janela de manutencao, backup novo e espaco livre externo/suficiente;
- mensagens historicas antigas com status `PENDING`/`ERROR` na Evolution foram preservadas; nao houve edicao manual de status de mensagem;
- nao foi possivel alterar a tarefa `CRM_CYCLE_N8N` de nivel `SISTEMA` por acesso negado, mas ela ja executa o wrapper que chama o script vigente.

## Bloqueio definitivo de etiqueta ENCERRADO via PostgreSQL Evolution em 2026-05-05 08:54 -03

Incidente:
- cliente com etiqueta WhatsApp `ENCERRADO` continuava entrando no fluxo automatico, gerando `routeDecision=claude_direct` e risco comercial de interferencia na negociacao.

Causa raiz:
- o bloqueio anterior dependia da etiqueta chegar no payload ou de `staticData.closedByWhatsappLabel`;
- a instancia principal opera com webhook focado em `MESSAGES_UPSERT`, entao a associacao de etiqueta nao chega junto no payload da mensagem;
- no caso reproduzido, a fonte real estava em `public."Chat"."labels"` no PostgreSQL da Evolution: JID `49723356479543@lid` com `labels=["21"]`, label `ENCERRADO`, enquanto as mensagens eram resolvidas para o numero `556974009750`.

Correcao aplicada:
- `router_service.py` passou a consultar diretamente o PostgreSQL da Evolution antes de RAG/LLM/log de rota;
- a consulta cruza `remoteJid`, `resolvedJid`, candidatos `@s.whatsapp.net` e LIDs conhecidos em `lid_mappings` para o numero resolvido;
- quando encontra label id `21` ou nome `ENCERRADO`, retorna `routeDecision=closed_label_encerrado`, `sendEligible=false`, `llmReplyText=""`, `blockReason=closed_label_encerrado`;
- backup antes da alteracao: `C:\AUTOMACAO\backups\closed_label_guard_fix_20260505_085055`.

Validacao:
- `python -m py_compile router_service.py` OK;
- router reconstruido com `docker compose up -d --build router`;
- router healthy e endpoints `router /health`, `router /metrics`, `n8n /healthz`, Evolution `/` retornaram 200;
- teste controlado com `remoteJid=49723356479543@lid` retornou `closed_label_encerrado`, `sendEligible=false`, `llmReplyText=""`, origem `evolution_chat_labels`;
- teste controlado com `remoteJid=556974009750@s.whatsapp.net` tambem bloqueou usando o LID mapeado `49723356479543@lid`;
- os testes controlados nao criaram novo `route_log`; ultimo route_log comercial permaneceu `id=696`;
- log do router registrou `closed_label_route_suppressed` com label `ENCERRADO`.

Pendencia residual:
- nenhuma pendencia tecnica para o bloqueio `ENCERRADO`; ele agora independe de evento de label no webhook.

## Contencao emergencial apos desconexao da instancia em 2026-05-05 08:59 -03

Incidente:
- o usuario precisou desconectar a instancia principal para impedir novos eventos nocivos enquanto o risco comercial era contido.

Estado confirmado:
- PC atual: PC CLS `100.113.13.27`, host `INTELIGENCIA-G1`;
- `ATENDIMENTO_VENDAS_CLEAN` ficou com `connectionStatus=close` desde `2026-05-05 11:46:31.326`;
- `STRESS_CLIENT_SETOR` ficou em `connecting`, mas nao e a instancia principal de atendimento;
- o workflow principal `zN3heKJVLO8w4dG6` ainda estava ativo logo apos a desconexao da instancia.

Correcao de contencao aplicada:
- workflow n8n `zN3heKJVLO8w4dG6` desativado com `n8n update:workflow --id=zN3heKJVLO8w4dG6 --active=false`;
- container `n8n` reiniciado para garantir descarregamento do webhook ativo;
- n8n voltou `healthy`.

Validacao:
- `n8n list:workflow --active=true` nao lista o workflow principal;
- `n8n list:workflow --active=false` lista `zN3heKJVLO8w4dG6|WhatsApp AI Auto Reply (Evolution + OpenAI + Claude + Openclaw)`;
- POST controlado para `http://localhost:5678/webhook/evolution-inbound` retorna 404, confirmando webhook principal indisponivel;
- Evolution PostgreSQL mostra 0 mensagens com status de envio desde `2026-05-05 11:46:31`;
- `router_runtime.sqlite` mostra 0 `route_logs` desde `2026-05-05T11:56:24`;
- containers `n8n` e `router` estao `healthy`, `evolution` esta `running`.

Status operacional:
- atendimento automatico esta em trava de seguranca: instancia principal desconectada e workflow principal inativo;
- nao reativar a instancia/workflow sem uma acao deliberada de retomada e conferencia da etiqueta `ENCERRADO`.
