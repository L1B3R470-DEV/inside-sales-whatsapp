# CURRENT_STATE

Atualizado em: 2026-04-28 10:10:00 -03:00
Diretorio vigente: C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES

## Identificacao operacional

- PC CLS = 100.113.13.27
- PC LBN = 100.101.106.95
- Antes de qualquer acao dependente de maquina, detectar IP Tailscale e mapear PC atual / PC da outra ponta.

## Stack esperada

- Evolution API: Docker, porta 8080, instancia ATENDIMENTO_VENDAS_CLEAN.
- n8n: Docker, porta 5678, workflow principal zN3heKJVLO8w4dG6.
- router: Docker, porta 8091, imagem attendant-router:latest.
- PostgreSQL Evolution: Docker, evolution-postgres.
- Redis Evolution: Docker, evolution-redis.
- MinIO: Docker, evolution-minio.
- n8n-autoheal: Docker, limpa execucoes antigas em running.

## Regras comerciais permanentes

- Marca em mensagem ao lead: usar somente Classe.
- Nunca usar a forma antiga da marca com sufixo proibido em outbound ao lead.
- Nunca usar premium como qualificativo comercial.
- Nao genderizar produtos; a Classe atende produtos femininos e masculinos.
- Nao citar cidade do lead em resposta comercial.
- Consultor: Eduardo Vinhas.
- Mensagens curtas, objetivas, sem assinatura longa.
- Para B2B/CNPJ: login = CNPJ completo; senha inicial = 8 primeiros digitos do CNPJ.

## Estado tecnico consolidado ate a migracao

- Gates de homologacao foram desligados: guardrails testModeOnlyAllowedNumbers=false e routerTestGateEnforced=false.
- always_allowed_numbers deve permanecer vazia salvo necessidade explicita.
- blocked_numbers legitimos conhecidos: 557382474263, 557591932073, 557599163917, 557599193581.
- n8n deve chamar o router por http://router:8091 dentro do Docker.
- O dashboard deve distinguir response_sent, human_pending, number_unresolved, no_outbound_associated e processing.
- Resolucao de LID deve preservar candidatos: senderPhoneCandidate, participantJidCandidate, senderJidCandidate.

## Evidencias historicas importantes

- Workflow principal: zN3heKJVLO8w4dG6.
- Instancia Evolution: ATENDIMENTO_VENDAS_CLEAN.
- Numero homologado historico: 557588340000.
- Validacao anterior mostrou route_log com number preenchido quando o payload trazia senderPhone rastreavel.
- O problema antigo do dashboard era visual: ausencia de outbound era rotulada como aguardando Eduardo.
- Problema operacional antigo: n8n chamava host.docker.internal:8091 e podia atingir processo host legado.

## Antes de retomar

1. Rodar git status --short --branch.
2. Verificar docker ps.
3. Verificar /health do n8n, router e Evolution.
4. Confirmar ROUTER_BASE_URL no n8n como http://router:8091.
5. Verificar se existe processo host legado em 8091 competindo com o container.\n\n\n
