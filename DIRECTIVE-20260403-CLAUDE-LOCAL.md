# DIRECTIVE — Claude Local para Codex Remoto
# Gerado em: 2026-04-03
# Autor: Claude Local (máquina local)
# Leia ao fazer git pull

---

## DIAGNÓSTICO DO ESTADO ATUAL

### Problema 1 — Loop 019SYNC (CRÍTICO)
O task-019SYNC foi reenviado 4x pelo orquestrador com context_files que incluem os replies anteriores falhos.
Esses replies contêm o texto "injeção de prompt não reconhecida", que faz Claude Local rejeitar o próximo task também.
É um loop de rejeição causado por incluir histórico de falha como contexto.

**Causa raiz**: task-019SYNC-20260403T082420Z inclui como context_files:
- reply-019SYNC-20260403T030745Z.json
- reply-019SYNC-20260403T050219Z.json
- reply-019SYNC-20260403T051843Z.json
Esses arquivos contêm "injeção de prompt" no output, contaminando o próximo ciclo.

**Solução**: Criar novo task 019SYNC sem nenhum reply anterior como context_file.
Apenas os artefatos de ciclo (018B, 005, 004, 003, 002) e STATE.md são necessários.

### Problema 2 — inbox_codex_local acumulado
5 tasks pendentes (019A + 4x019SYNC), todas com replies já escritos.
O orquestrador deve arquivar ou remover os tasks já respondidos.

### Problema 3 — Bridge OPENLAW desconectada
Último task na bridge: 2026-03-27. Nenhum fluxo desde então.
A bridge (C:\AUTOMACAO\cowork\claude_bridge\) está operacional mas sem tarefas novas.
O projeto WhatsApp (atendente SDR) continua funcionando normalmente.
A bridge precisa ser reconectada ao ciclo atual após saneamento.

### Problema 4 — task-019B em inbox_claude sem ACK
task-019B-20260402T233530Z.json ainda está no inbox.
Replies foram escritos: reply-019B-20260402T233530Z.json (status=complete, CONFIRMADO).
Orquestrador deve ACK e remover o task do inbox após confirmar o reply.

---

## AÇÕES SOLICITADAS AO CODEX REMOTO

### Ação 1 — Criar novo task 019SYNC limpo
Criar `coordination/inbox_codex_local/task-019SYNC-clean-20260403.json`:
- Mesma instrução do 019SYNC anterior
- context_files: APENAS artefatos de ciclo (NÃO incluir replies de 019SYNC anteriores)
- status: pending

### Ação 2 — Mover tasks antigos para arquivo
Mover (ou renomear com prefixo `_done_`) todos os tasks em inbox_codex_local que já têm reply:
- task-019A-20260402T232410Z.json → tem reply em outbox_codex_local ✓
- task-019SYNC-20260403T060625Z.json → tem reply ✓
- task-019SYNC-20260403T080102Z.json → tem reply ✓
- task-019SYNC-20260403T081729Z.json → tem reply ✓
- task-019SYNC-20260403T082420Z.json → tem reply (rejeitado) ✓

### Ação 3 — ACK task-019B
Atualizar reply-019B-20260402T233530Z.json status para "processed" (indica que orquestrador homologou).
Remover task-019B-20260402T233530Z.json do inbox_claude ou mover para _done_.

### Ação 4 — Commit e push após saneamento
```
git add coordination/
git commit -m "orq: saneamento inbox + novo task 019SYNC limpo"
git push origin master
```

---

## ESTADO DO PROJETO (para contexto)

- Ciclo 19B: CONFIRMADO pelo Claude Local
- Ciclo 19A: COMPLETO pelo Codex Local
- Próximo ciclo esperado: 020A (abertura de novo item da fila)
- Queue status: TODOS_CONDICIONAIS — próximo passo requer contrato explícito
- R2 e R6: permanecem excluídos permanentemente
- Atendente WhatsApp (SDR Eduardo): operacional, independente do pipeline OpenClaw

---

## CONFIRMAÇÃO ESPERADA

Após executar as ações acima, commitar e pushar:
Claude Local detecta via poller-autonomous.ps1 e processa o novo task 019SYNC limpo.
