# CHANGELOG_COLLAB

## 2026-04-28 09:24:42 -03:00 - Criacao de contexto persistente apos renomeacao da pasta

### Problema

A pasta do projeto foi renomeada e o chat antigo ficou vinculado ao caminho inexistente:
C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES.

### Acao

Criados arquivos persistentes de contexto na pasta nova:
- AGENT_CONTEXT.md
- PROJECT_RULES.md
- COLLAB_HANDOFF.md
- NEXT_ACTIONS.md

### Evidencia

A pasta nova foi validada como existente:
C:\Users\User\Desktop\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES

git status --short --branch indicou branch main com worktree sujo preexistente.

### Resultado

O contexto operacional basico foi materializado em arquivos para ser lido por novas conversas/agentes.

### Pendencia

Abrir nova conversa/workspace apontando para a pasta nova e instruir o agente a ler os arquivos de contexto antes de agir.
## 2026-04-30 - Stress criativo rodada 2 e saneamento comercial

### Acao
- Inseridas regras comerciais criticas no RAG ativo em C:\AUTOMACAO\rag\knowledge.
- Rebuild/restart do router e reindexacao RAG.
- Executado stress test comercial nao-triagem com 40 perguntas pelo endpoint /route.
- Saneadas falhas de PV/PVL, ranking de kits, B2B, estoque inicial, seguranca comercial e valores do book.

### Evidencia
- Relatorio: $report
- Resultado final: 40/40 respostas SATISFATORIA apos retestes.

### Observacao
- Validacao desta rodada ocorreu pelo router /route, nao por inbound real Evolution/n8n.
## 2026-05-04 - Regra intransponivel etiqueta ENCERRADO

- Implementado bloqueio operacional para etiqueta WhatsApp `ENCERRADO` antes de contato com lead/cliente.
- Label Evolution validada: `ENCERRADO` com id `21` na instancia `ATENDIMENTO_VENDAS_CLEAN`.
- Camadas alteradas: `normalize-payload.js`, `guardrails.js`, `workflow-send-gate.js`, `router_service.py`, `sdr_prompt.txt`, `patch_workflow_intelligence_v1.py`.
- Workflow n8n ativo `zN3heKJVLO8w4dG6` republicado via patch SQLite: `entity_changes=1`, `history_changes=2`.
- Router reconstruido/reiniciado e n8n reiniciado para evitar cache de runtime.
- Validacao: payload com `labels=[{id:"21", name:"ENCERRADO"}]` retorna `routeDecision=closed_label_encerrado`, `sendEligible=false`, `llmReplyText=""`; guardrails zera `number` e send gate retorna `skip_closed_label_encerrado`.

## 2026-05-04 - Saneamento do Git sujo

- Removido lock obsoleto `.git/index.lock` depois de limpar processos Git presos.
- Atualizado `.gitignore` para impedir staging recorrente de runtime local, QR, bancos, `node_modules`, dumps brutos e backups de relatorio.
- Recuperados arquivos textuais corrompidos por escrita com `\n` literal usando blobs bons do object database Git.
- Stage consolidado em commit rastreavel, com validacao de whitespace, sintaxe Python/JS/PowerShell, JSON e `docker compose config`.
