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
