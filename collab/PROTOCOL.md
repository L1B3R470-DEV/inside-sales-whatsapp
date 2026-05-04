# COLLAB PROTOCOL - Codex + Claude Code

Este diretorio define o protocolo persistente de colaboracao entre Codex e Claude Code.

## Pastas

- inbox_codex: tarefas destinadas ao Codex.
- inbox_claude: tarefas destinadas ao Claude Code.
- outbox_codex: respostas/relatorios gerados pelo Codex.
- outbox_claude: respostas/relatorios gerados pelo Claude Code.
- tasks: tarefas ativas compartilhadas.
- archive: tarefas encerradas.

## Formato de task

Use JSON ou Markdown curto com:
- id
- criado_em
- autor
- destinatario
- objetivo
- contexto_minimo
- arquivos_relevantes
- comandos_validacao
- criterio_de_sucesso
- bloqueios

## Regras

1. Sempre ler CURRENT_STATE.md e FLOW_AUDIT_2026-04-28.md antes de executar tarefa operacional.
2. Antes de editar, rodar git status --short --branch.
3. Nunca reverter alteracoes do outro agente sem pedido explicito.
4. Codex assume execucao operacional e integracao final.
5. Claude Code atua como sidecar de revisao, diagnostico, hipotese tecnica e auditoria de payload quando recrutado.
6. Toda resposta deve indicar evidencias, comandos usados e arquivos alterados.
7. Ao finalizar, atualizar collab/STATE.md e, se necessario, NEXT_ACTIONS.md.\n\n
