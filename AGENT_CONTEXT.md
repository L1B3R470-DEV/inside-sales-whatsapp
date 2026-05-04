# AGENT_CONTEXT

Atualizado em: 2026-04-28 10:15:00 -03:00
Projeto: PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES
Diretorio vigente: C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES
Diretorio antigo original: C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES
Diretorio intermediario antigo: C:\Users\User\Desktop\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES

## Objetivo deste arquivo

Este arquivo existe para transferir contexto operacional entre conversas, Codex, Claude Code e outras ferramentas apos a migracao para CODEX_PROJECTS. Antes de qualquer acao relevante neste projeto, leia este arquivo junto com PROJECT_RULES.md, COLLAB_HANDOFF.md, CHANGELOG_COLLAB.md, CURRENT_STATE.md, FLOW_AUDIT_2026-04-28.md e NEXT_ACTIONS.md.

## Identificacao de maquinas por Tailscale

Mapeamento obrigatorio quando host/contexto de maquina importar:
- PC CLS = 100.113.13.27
- PC LBN = 100.101.106.95

Regra:
- Detectar o IP Tailscale do ambiente atual antes de acoes dependentes de maquina.
- Se IP detectado for 100.113.13.27, PC atual = PC CLS e PC da outra ponta = PC LBN.
- Se IP detectado for 100.101.106.95, PC atual = PC LBN e PC da outra ponta = PC CLS.
- Nao usar PC local/remoto por inferencia vaga.
- Se nao for possivel detectar com seguranca, declarar impedimento critico.

## Comportamento esperado do agente

- Ser tecnico, direto, rastreavel e verificavel.
- Nao tratar hipotese como fato.
- Nao afirmar que verificou algo sem evidencia.
- Expor bloqueios, permissoes ausentes, falhas e limites.
- Antes de editar, avaliar Git, estado do projeto e collab.
- Nunca reverter alteracoes de terceiros sem pedido explicito.
- Preservar historico e contexto operacional.

## Estado Git conhecido

Comando verificado: git status --short --branch.
Resultado resumido: branch main, worktree sujo, muitos arquivos modificados e nao rastreados. Nao limpar, deletar, resetar, stagear ou reverter sem instrucao explicita.

## Contexto tecnico consolidado

Arquivos criticos recorrentes:
- router_service.py
- docker-compose.yml
- guardrails.js
- normalize-payload.js
- extract-reply.js
- build-fallback-reply.js
- dashboard_sdr.html
- patch_workflow_intelligence_v1.py

Decisoes/achados historicos importantes:
- Mudancas no workflow n8n devem ser reaplicadas ao workflow ativo quando necessario.
- Validacao deve cruzar servicos, banco, logs, dashboard e canal real.
- LID nao resolvido deve ser tratado como diagnostico operacional, nao como prova de atendimento humano.
- Falhas OpenAI devem diferenciar quota/auth/rate/network quando possivel.
- Gates de homologacao/allowlist devem permanecer desligados salvo pedido explicito.
- Audio/transcricao deve ser validado pelo fluxo real de midia/transcricao.

## Primeira acao recomendada em nova conversa

1. Confirmar diretorio vigente.
2. Ler AGENT_CONTEXT.md, PROJECT_RULES.md, COLLAB_HANDOFF.md, CHANGELOG_COLLAB.md, CURRENT_STATE.md, FLOW_AUDIT_2026-04-28.md e NEXT_ACTIONS.md.
3. Rodar git status --short --branch.
4. Confirmar objetivo mais recente do usuario.
5. Agir com validacao objetiva.\n\n
