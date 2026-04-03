# CLAUDE.md — Inside Sales OpenClaw Workspace

Sistema de coordenação de melhorias incrementais para o projeto Inside Sales WhatsApp (Classe Couro).
Repositório: workspace-integration (branch master)
Responsável técnico: Inside Sales Dev

## Contexto

Este diretório contém artefatos de ciclos de melhoria do sistema de atendimento B2B.
Cada ciclo produz arquivos JSON em `output/` e `cycle*-input/`.
Tarefas comuns: verificar existência de arquivos JSON, criar ou reconstituir artefatos a partir de sources documentais, gerar relatórios de status.

## Regras de trabalho

- Trabalhar exclusivamente dentro deste diretório (workspace-integration)
- Nunca modificar o diretório: C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES
- Nunca tocar em: C:\AUTOMACAO\cowork\claude_bridge
- Commits no branch master após cada mudança

## Identidade Git

```
git config user.name "Inside Sales Dev"
git config user.email "dev@insidesales.local"
```

## Estrutura relevante

- `output/` — artefatos produzidos por ciclos anteriores (somente leitura como fonte)
- `cycle19-input/` — artefatos esperados do ciclo 19 (podem precisar ser criados)
- `coordination/` — arquivos de coordenação (inbox/outbox)
- `STATE.md` — estado atual do processo
