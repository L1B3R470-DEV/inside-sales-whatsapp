# FLOW_AUDIT_2026-04-28

Auditoria inicial gerada apos migracao para CODEX_PROJECTS.

## Fluxo alvo

WhatsApp lead -> Evolution API -> webhook n8n /webhook/evolution-inbound -> Normalize Payload -> Resolve Recipient API -> Router Decision -> Guardrails -> OpenAI/Anthropic/fallback -> Extract Reply -> Can Send? -> Evolution Send Text -> WhatsApp -> dashboard SDR.

## Gargalos e riscos encontrados

1. Caminhos antigos ainda existiam em documentos de contexto.
Impacto: novas sessoes poderiam abrir a pasta errada.
Acao: AGENTS.md, CLAUDE.md, AGENT_CONTEXT.md, COLLAB_HANDOFF.md e NEXT_ACTIONS.md foram normalizados para CODEX_PROJECTS.

2. Marca antiga ainda aparecia em docs e dashboard.
Impacto: risco de reintroduzir a forma antiga da marca em respostas ou UI.
Acao: docs e header do dashboard foram atualizados para Classe. No codigo, referencias proibitivas ou keywords de entendimento podem continuar existindo apenas para sanitizacao/intencao.

3. ROUTER_BASE_URL divergente.
Achado: n8n estava correto em http://router:8091, mas o servico router ainda trazia ROUTER_BASE_URL=http://host.docker.internal:8091.
Risco: confusao de runtime e chamadas acidentais ao processo host legado.
Acao: docker-compose.yml alinhado para http://router:8091 tambem no servico router.

4. Worktree sujo e artefatos nao rastreados.
Impacto: commits sem triagem podem misturar features, diagnosticos e lixo operacional.
Acao necessaria: antes de commit, separar arquivos de contexto/collab, mudancas funcionais e artefatos temporarios.

5. Possivel processo host legado em 8091.
Historico: houve PID host antigo competindo com container router.
Acao necessaria: verificar com netstat/Get-NetTCPConnection e eliminar duplicidade em janela segura.

6. LID/number.
Historico: messages @lid podem chegar sem number; o fluxo deve usar senderPhoneCandidate, participantJidCandidate, senderJidCandidate e mapeamentos Evolution Contact.
Acao necessaria: testar com inbound real recente e confirmar route_logs.number preenchido e outbound enviado.

7. n8n backlog.
Historico: houve execucoes new/running/crashed e logs 'Execution is already being resumed by another process'.
Acao necessaria: auditar execution_entity, aplicar autoheal apenas em running velho e nao declarar 100% sem execucao success recente.

8. Dashboard.
Historico: o painel confundia sem outbound com atendimento humano pendente.
Acao ja aplicada: display_status/display_label devem reger a UI. Validar /sdr-dashboard-data antes de confiar na tela.

9. Segredos e chaves LLM.
Historico: ja houve divergencia de OPENAI_API_KEY entre host/n8n/router.
Acao necessaria apos qualquer rotacao: recriar n8n/router e testar consumo real da API sem expor chave.

## Checklist de validacao para declarar atendente 100%

1. docker compose config -q sem erro.
2. docker ps com evolution, n8n, router, postgres, redis, minio e n8n-autoheal ativos.
3. router /health ok e routerTestGateEnforced=false.
4. n8n /healthz ok.
5. Evolution instance/connectionState/ATENDIMENTO_VENDAS_CLEAN = open.
6. Webhook Evolution configurado para http://n8n:5678/webhook/evolution-inbound.
7. Inbound real de numero nao bloqueado gera execution success no n8n.
8. route_logs registra number preenchido.
9. Evolution registra outbound DELIVERY_ACK/READ.
10. Dashboard mostra status coerente, sem 'Aguardando Eduardo' falso.

## Prioridade de saneamento

P0: eliminar runtime duplicado em 8091 e validar n8n -> router interno.
P0: validar inbound real de numero nao bloqueado com outbound no Evolution.
P1: limpar backlog n8n antigo com regra auditavel.
P1: revisar untracked/fuse_hidden e artefatos temporarios.
P1: versionar docs de contexto aprovados.
P2: endurecer testes automatizados E2E com numero homologado e evidencia no dashboard.\n\n
## Validacao runtime em 2026-04-28 10:20 -03:00

Resultado:
- docker compose config -q: sem erro.
- docker ps: bloqueado porque Docker API nao esta acessivel.
- com.docker.service: Stopped.
- Processos Docker Desktop/com.docker.backend: nao encontrados.
- Pipes Docker: \\.\pipe\dockerDesktopLinuxEngine = False; \\.\pipe\docker_engine = False.
- http://localhost:8091/health: conexao recusada.
- http://localhost:5678/healthz: conexao recusada.

Conclusao:
O projeto foi migrado e documentado, mas o atendente nao pode ser declarado 100% em runtime enquanto Docker Desktop estiver parado. A proxima validacao deve iniciar Docker Desktop/engine e executar o checklist de ponta a ponta.\n\n
