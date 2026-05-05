# NEXT_ACTIONS

Atualizado em: 2026-05-05 10:19:06 -03:00

1. Abrir nova conversa no Codex apontando para C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES.
2. Pedir ao agente para ler AGENT_CONTEXT.md, PROJECT_RULES.md, COLLAB_HANDOFF.md, CHANGELOG_COLLAB.md e NEXT_ACTIONS.md.
3. Verificar git status --short --branch antes de qualquer edicao.
4. Decidir se os novos arquivos de contexto devem ser versionados.
5. Revisar a grande quantidade de artefatos temporarios/untracked antes de qualquer commit.
6. Prosseguir apenas com o objetivo operacional mais recente definido por Rodrigo.
## P0 apos migracao - 2026-04-28

8. Iniciar Docker Desktop/engine no PC CLS e confirmar pipes Docker ativos.
9. Rodar docker compose up -d no diretorio vigente.
10. Validar router, n8n, Evolution e instancia ATENDIMENTO_VENDAS_CLEAN.
11. Reaplicar workflow n8n se houver drift entre arquivos JS e workflow ativo.
12. Executar teste real de inbound ate outbound e dashboard antes de declarar atendente 100%.

## Atualizacao operacional - 2026-05-01

Concluido nesta rodada:
- ciclo CRM corrigido para `C:\AUTOMACAO\dados\crm_operacional.sqlite`;
- tarefa redundante `CRM_CYCLE_N8N_USER` validada com `LastTaskResult=0`;
- router reconectado a rede Docker legada para manter `n8n -> router` e `router -> postgres/evolution`;
- teste controlado pelo webhook n8n validou outbound Evolution com `DELIVERY_ACK`;
- dashboard passou a contar 5 leads elegiveis e 47 itens reais no backlog aberto.

Proxima pendencia real:
1. Manutencao de espaco em disco no PC CLS: C: segue com uso critico mesmo apos prune seguro. Nao apagar volumes Docker sem nova decisao operacional.

## Atualizacao operacional - 2026-05-05

Concluido nesta rodada:
- n8n auto-heal agora fecha execucoes presas em `running`, `new` e `crashed`;
- execucoes `8246` e `8247` foram saneadas e auditadas;
- ciclo CRM zerou `learning_backlog.open`, preservou `queued_human_review=37` e marcou 4 leads em `follow_up_humano_pendente`;
- reconciliacao Evolution -> CRM passou a rodar apos o ciclo para cobrir quedas/restarts sem depender apenas do `staticData` do n8n;
- resposta de recuperacao enviada ao lead `556974009750` e validada como `DELIVERY_ACK`;
- tarefa duplicada `CRM_CYCLE_N8N_USER` parada/desativada para reduzir concorrencia SQLite.

Proxima pendencia real:
1. Planejar janela com backup e espaco suficiente para compactar/migrar `ai_n8n_data`; nao executar `VACUUM` com ~10 GB livres para um SQLite de ~48.3 GB.

## Atualizacao operacional - 2026-05-05 08:54

Concluido nesta rodada:
- bloqueio `ENCERRADO` deixou de depender do payload do webhook e passou a consultar `Chat.labels` diretamente no PostgreSQL da Evolution;
- validado no caso real `49723356479543@lid` / `556974009750`: label `21=ENCERRADO` bloqueia `@lid` e numero normal;
- router retorna `closed_label_encerrado`, `sendEligible=false` e `llmReplyText=""` antes de RAG/LLM.

Proxima pendencia real:
1. Monitorar proximas mensagens de contatos encerrados; qualquer novo route_log `claude_direct` para label `ENCERRADO` deve ser tratado como regressao critica.

## Contencao emergencial - 2026-05-05 08:59

Concluido nesta rodada:
- usuario desconectou `ATENDIMENTO_VENDAS_CLEAN` para impedir novos eventos nocivos;
- confirmado no PostgreSQL da Evolution: `ATENDIMENTO_VENDAS_CLEAN=close` desde `2026-05-05 11:46:31.326`;
- workflow principal `zN3heKJVLO8w4dG6` foi desativado no n8n e o container `n8n` foi reiniciado;
- validado que o webhook `http://localhost:5678/webhook/evolution-inbound` retorna 404;
- validado 0 mensagens Evolution de envio desde a desconexao e 0 `route_logs` desde a desativacao do workflow.

Proxima pendencia real:
1. Manter `ATENDIMENTO_VENDAS_CLEAN` desconectada e `zN3heKJVLO8w4dG6` inativo ate uma retomada operacional deliberada.
2. Na retomada: confirmar bloqueio `ENCERRADO`, reconectar a instancia, ativar o workflow e executar teste controlado antes de liberar trafego real.

## Retomada controlada - 2026-05-05 09:17

Concluido nesta rodada:
- `556974009750` bloqueado no router runtime (`blocked_numbers`), no corte antecipado de `/route`, no `guardrails.js` fonte e no `staticData.ignoredContacts` do workflow ativo;
- workflow principal `zN3heKJVLO8w4dG6` reativado e validado como ativo;
- teste direto no router para `556974009750` retornou `blocked_number`, `sendEligible=false`, `llmReplyText=""`;
- teste via webhook n8n com `556974009750` iniciou o workflow e foi suprimido por `blocked_number_route_suppressed`;
- validado 0 envios Evolution `fromMe=true` desde a desconexao;
- QR gerado para reconectar `ATENDIMENTO_VENDAS_CLEAN`.

Proxima pendencia real:
1. Escanear o QR em `C:\AUTOMACAO\logs\ATENDIMENTO_VENDAS_CLEAN_QR_20260505_091900.png`.
2. Apos o estado virar `open`, monitorar `route_logs`, Evolution `Message fromMe=true` e logs do router por pelo menos os primeiros eventos reais.

## Laboratorio aprovado e implantado - 2026-05-05 10:19

Concluido nesta rodada:
- criado `docker-compose.lab.yml` para laboratorio isolado n8n/Evolution/RAG;
- criado env-file local fora do Git em `C:\AUTOMACAO\secrets\inside_sales_lab.env`;
- n8n lab 2.18.7 subiu em `http://localhost:15678` com PostgreSQL proprio e workflow `zN3heKJVLO8w4dG6` importado/ativo;
- Evolution lab 2.3.7 subiu em `http://localhost:18080` com instancia `ATENDIMENTO_VENDAS_LAB` em `connecting`;
- teste webhook lab com `556974009750` foi suprimido por `blocked_number_route_suppressed` e nao gerou envio produtivo;
- benchmark RAG baseline gerado em `ANALISES/QDRANT_HYBRID_BENCHMARK.md`;
- backup/export de seguranca criado em `C:\AUTOMACAO\backups\lab_upgrade_n8n_evolution_rag_20260505_094826`.

Proxima pendencia real:
1. Decidir janela de promocao produtiva do n8n/Evolution usando a branch `lab/n8n-evolution-rag-20260505` como base.
2. Nao compactar nem copiar o SQLite produtivo do n8n de 48.3 GB enquanto o C: tiver apenas cerca de 10 GB livres.
3. Criar colecao Qdrant paralela dense+sparse e comparar contra o baseline BM25/RRF antes de substituir recuperacao em producao.
