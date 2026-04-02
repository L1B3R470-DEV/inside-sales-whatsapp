# BOOTSTRAP — CODEX LOCAL (Esta Máquina)

## Seu papel
Executar ciclos. Produzir payloads JSON. Não analisa, não decide — executa o que o CODEX REMOTO ordena.

## Antes de qualquer sessão — 3 comandos obrigatórios

```powershell
cd C:\Users\User\.openclaw\workspace-integration
git checkout master
git pull origin master
```

## Após CADA ciclo concluído — obrigatório

```powershell
.\sync-after-cycle.ps1 -CycleId "18B" -Message "descrição do que foi feito"
```

Isso faz automaticamente: `git add -A` → `commit` → `push master` → `push context`

## Estado atual

Leia `STATE.md` (branch `context`) para o estado mais recente.

Resumo agora:
- Último ciclo: **18A** produzido
- Próxima tarefa: produzir **18B** quando receber contrato do CODEX REMOTO
- Payload 18A: `cycle18-input/cycle-018A-r2-iteration-closure-or-reopen-conditions.json`

## Restrições (nunca violar)

- session_write_policy = RESSALVA_OPERACIONAL
- live_crm_authorized = false
- sandbox_authorized = false  
- write_authorized = false
- Nunca tocar em produção, .mcp.json, bridge local, projeto real
- Nunca usar runner stateful

## Workspace

```
C:\Users\User\.openclaw\workspace-integration\
├── output\          → payloads homologados (ciclos B)
├── cycle12-input\   → payloads A do ciclo 12
├── cycle13-input\   → ...
├── cycle18-input\   → ciclo atual
└── context\         → contratos e contexto
```
