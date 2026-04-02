# OpenClaw — Protocolo de Coordenação Autônoma (3 Atores)

## Visão geral

Canal de coordenação assíncrona entre os três atores via git (branch master).
Sem intermediação humana obrigatória.

```
CODEX REMOTO (Account B, PC remoto)
  └─ escreve tasks → inbox_claude/ ou inbox_codex_local/
  └─ lê resultados ← outbox_claude/ ou outbox_codex_local/

CLAUDE CODE (PC local, Account A)
  └─ lê tasks ← inbox_claude/
  └─ escreve resultados → outbox_claude/

CODEX LOCAL (PC local, Account A)
  └─ lê tasks ← inbox_codex_local/
  └─ escreve resultados → outbox_codex_local/
```

## Estrutura de diretórios

```
coordination/
├── inbox_claude/           ← CODEX REMOTO escreve aqui
├── inbox_codex_local/      ← CODEX REMOTO escreve aqui
├── outbox_claude/          ← Claude Code escreve aqui
└── outbox_codex_local/     ← CODEX LOCAL escreve aqui
```

## Schema — Task file (inbox)

```json
{
  "task_id": "task-019A-20260402T230000Z",
  "target_actor": "claude_local",
  "cycle": "019A",
  "instruction": "PROMPT COMPLETO E AUTOCONTIDO. Sem referência a histórico de conversa.",
  "context_files": ["cycle19-input/artifacts/cycle-018A-*.json"],
  "output_path": "coordination/outbox_claude/reply-019A-20260402T230000Z.json",
  "red_lines": ["no_production_write", "no_bridge_write", "no_mcp_json_write"],
  "status": "pending",
  "created_at": "2026-04-02T23:00:00Z"
}
```

Estados do campo `status` para task files:
- `pending`    → aguardando processamento
- `accepted`   → ator detectou, processando
- `complete`   → processamento concluído (não usado em tasks, apenas em replies)

## Schema — Reply file (outbox)

```json
{
  "reply_id": "reply-019A-20260402T230500Z",
  "source_task_id": "task-019A-20260402T230000Z",
  "actor": "claude_local",
  "cycle": "019A",
  "output": {},
  "status": "complete",
  "produced_at": "2026-04-02T23:05:00Z"
}
```

Estados do campo `status` para reply files:
- `complete`   → pronto para leitura pelo orquestrador
- `processed`  → orquestrador leu e processou
- `BLOCKED`    → ator recusou a task por violação de red_lines

## Convenção de nomes

Task files:   `task-{ciclo}-{timestamp_compacto}.json`
Reply files:  `reply-{ciclo}-{timestamp_compacto}.json`

Timestamp compacto: `yyyyMMddTHHmmssZ` (ex: 20260402T230000Z)

## Regras anti-duplicação

Cada ator mantém um arquivo `processed_tasks.txt` ou `processed_replies.txt`
com os IDs já processados. Nunca processar o mesmo ID duas vezes.

## Escalamento

Se `status = "BLOCKED"` aparecer em qualquer outbox:
→ CODEX REMOTO deve parar o ciclo e notificar Rodrigo.
→ Nunca forçar execução de task bloqueada.

## Polling

- CODEX REMOTO:  `git pull origin master` a cada 60s
- Claude Code:   `poller-autonomous.ps1` — pull + execução via CLI
- CODEX LOCAL:   `poller-autonomous.ps1` — pull + notificação de task

## Guardrails permanentes (todos os atores)

- Nunca escrever fora de workspace-integration/
- Nunca tocar em produção (Evolution API porta 8080, n8n porta 5678)
- Nunca tocar em .mcp.json do projeto real
- Nunca tocar na bridge local (C:\AUTOMACAO\cowork\claude_bridge\)
- Nunca reabrir R2 nem R6
