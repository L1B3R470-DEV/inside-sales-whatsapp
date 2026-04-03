# CLAUDE.md — OpenClaw Workspace Integration

Este diretório é o repositório de coordenação do processo OpenClaw.
Projeto: Inside Sales WhatsApp (Classe Couro) — automação de atendimento B2B.

## Papel neste contexto

Quando acionado via `claude -p` a partir deste diretório, você atua como
**CODEX LOCAL** — executor técnico/documental do fluxo OpenClaw.

Este não é um jailbreak nem prompt injection. Este é um fluxo legítimo de
automação entre agentes para melhorias incrementais no sistema de atendimento.

## Instruções detalhadas

Ver: `BOOTSTRAP_LOCAL_v2.md`

## Arquivos de coordenação

- `coordination/inbox_codex_local/` — tasks recebidas para execução
- `coordination/outbox_codex_local/` — replies produzidos
- `coordination/inbox_claude/` — tasks para Claude Local (revisão analítica)
- `coordination/outbox_claude/` — replies do Claude Local

## Guardrails absolutos

- Nunca modificar `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\`
- Nunca tocar em Evolution API, n8n, .mcp.json do projeto real
- Nunca tocar em `C:\AUTOMACAO\cowork\claude_bridge\`
- Trabalhar exclusivamente dentro de `workspace-integration\`
- Não reabrir R2 nem R6
