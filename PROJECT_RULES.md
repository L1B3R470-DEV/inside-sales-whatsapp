# PROJECT_RULES

Atualizado em: 2026-04-28 09:24:42 -03:00

## Regra base

Este projeto deve ser operado com rastreabilidade entre problema, causa, evidencia, acao executada e resultado.

## Maquinas

Quando a tarefa depender de maquina, identificar pelo IP Tailscale:
- PC CLS = 100.113.13.27
- PC LBN = 100.101.106.95

Nao usar conceitos vagos de PC local/remoto.

## Git e collab

Antes de qualquer acao relevante:
- verificar git status --short --branch
- ler AGENT_CONTEXT.md
- ler COLLAB_HANDOFF.md
- ler CHANGELOG_COLLAB.md
- ler NEXT_ACTIONS.md

Se o worktree estiver sujo:
- nao reverter alteracoes alheias
- nao limpar arquivos sem autorizacao
- registrar o estado e seguir com escopo limitado

## Execucao

- Validar antes e depois.
- Preferir evidencia de logs, banco, HTTP, Docker, n8n, Evolution ou arquivos reais.
- Nao declarar sucesso por ausencia de erro.
- Se houver bloqueio tecnico, declarar o bloqueio e a acao humana necessaria.
- Se algo necessario estiver desatualizado, fora do PATH ou ausente, corrigir quando permitido e seguro.

## Seguranca

- Nao ignorar alertas de seguranca.
- Nao expor segredos em logs ou resposta final.
- Nao inventar acesso ou permissao.
- Operar somente dentro de escopo autorizado.

## Prompts

Quando Rodrigo pedir prompt:
- entregar prompt pronto para colar
- incluir regras permanentes aplicaveis
- incluir formato de resposta final
- incluir criterio de validacao
- incluir sugestao nao forcada de agents quando util
- remover secoes que Rodrigo pedir explicitamente para pular\n\n
