# NEXT_ACTIONS

Atualizado em: 2026-05-05 08:40:25 -03:00

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
