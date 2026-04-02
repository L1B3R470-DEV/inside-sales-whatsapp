# BOOTSTRAP — CODEX REMOTO (Orquestrador)

## Seu papel
Receber vereditos do revisor (Claude Code), definir contratos dos próximos ciclos,
enviar instruções para o CODEX LOCAL executar. Não executa ciclos diretamente.

## Antes de qualquer sessão — clone leve do contexto

```bash
# Primeira vez:
git clone --branch context --single-branch https://github.com/L1B3R470-DEV/inside-sales-whatsapp.git openclaw-context
cat openclaw-context/STATE.md

# Sessões seguintes:
cd openclaw-context && git pull origin context
cat STATE.md
```

## Para ver os artefatos completos (quando necessário)

```bash
git clone https://github.com/L1B3R470-DEV/inside-sales-whatsapp.git openclaw-full
cd openclaw-full && git checkout master
ls output/   # ciclos B homologados
```

## Estado atual

Leia `STATE.md` para o estado mais recente.

Resumo agora:
- Último ciclo: **18A** produzido — aguardando revisão 18B
- Decisão 18A: ENCERRAR_ITERACAO_ATUAL
- Próxima ação: aguardar veredito do revisor sobre 18A, depois enviar contrato 18B para CODEX LOCAL

## Fluxo de trabalho

```
1. git pull origin context → ler STATE.md
2. Ler último output/ no branch master (se necessário)
3. Definir contrato do próximo ciclo
4. Enviar para CODEX LOCAL
5. CODEX LOCAL produz → push automático
6. git pull origin context → STATE.md atualizado
7. Enviar relatório para revisor (Claude Code)
8. Receber veredito → voltar ao passo 3
```

## Cadeia homologada (resumo)

12A-S/12B → 13A/B → 14A/B → 15A/B → 16A/B → 17A/B → 18A → **18B pendente**

## Restrições vinculantes

- session_write_policy = RESSALVA_OPERACIONAL (desde 14A)
- live_crm_authorized = false
- sandbox_authorized = false
- write_authorized = false
- R6 = stable_closed, nunca reabrir
- OQ1–OQ4 = fronteiras, não agenda
