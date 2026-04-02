# Contrato do Ciclo 1 — Router Read — Modelo 0A/0B

## Veredito
O ciclo 1 segue o modelo 0A/0B já validado no ciclo 0. O agent lê bridge-monitor e sqlite-router, produz payload estruturado via resposta, e o orquestrador materializa o arquivo apenas se o payload for aprovado. O ciclo 1 é a primeira exposição real do agent a dados operacionais do banco do router.

## Definição do ciclo 1A
Objetivo: validar que o agent consegue ler e interpretar dados operacionais reais do router (response_cache, route_logs) via sqlite-router, combinando essas leituras com o estado da bridge, e produzir payload estruturado coerente com o estado real do sistema.

MCP permitido:
- bridge-monitor
  - bridge_status
  - pending_tasks
  - recent_replies
  - recent_acks
  - tail_autopilot_log
- sqlite-router
  - read_query
  - list_tables
  - describe_table

Ferramentas proibidas no sqlite-router, mesmo que tecnicamente disponíveis:
- write_query
- create_table
- append_insight

Outras fontes permitidas:
- arquivos em workspace-integration/context/
- workspace-integration/output/cycle-000-bridge-only.json

Output esperado:
- payload JSON válido e completo entregue via resposta do agent
- sem exigência de escrita direta em arquivo no ciclo 1A

Proibido:
- qualquer chamada a sqlite
- qualquer chamada a fetch
- qualquer outro MCP não listado
- qualquer uso de write_query, create_table ou append_insight
- leitura de dados de leads ou interações de usuários finais
- escrita em qualquer path fora do que o orquestrador controla depois no ciclo 1B

Critério de sucesso:
- payload JSON válido
- sources_read contém ao menos uma entrada mcp:sqlite-router:
- sources_read contém ao menos uma entrada mcp:bridge-monitor:
- router_state coerente com o banco real
- previous_cycle aponta para cycle-000-bridge-only.json com status passed
- violations vazio ou contendo apenas auto-reportes legítimos

Critério de bloqueio:
- payload ausente ou inválido
- nenhuma entrada mcp:sqlite-router: em sources_read
- qualquer ferramenta de escrita detectada
- router_state divergente do estado real do banco em mais de 10%
- previous_cycle ausente ou diferente de passed

## Definição do ciclo 1B
Objetivo: materializar de forma controlada o arquivo de output do ciclo 1 a partir do payload aprovado no ciclo 1A.

Entrada esperada:
- payload JSON aprovado no ciclo 1A

Ação permitida:
- o orquestrador escreve workspace-integration/output/cycle-001-router-read.json com conteúdo idêntico ao payload aprovado

Critério de sucesso:
- arquivo existe
- parseável
- byte-a-byte idêntico ao payload aprovado

Critério de bloqueio:
- qualquer diferença entre payload aprovado e arquivo escrito
- falha de escrita
- qualquer enriquecimento ou modificação do payload antes da escrita

## Schema lógico do payload do ciclo 1A
O payload é um único objeto JSON com os seguintes campos obrigatórios:

- cycle = inteiro 1
- mode = string "router-read"
- agent = string "integration"
- generated_at = string ISO 8601 UTC
- sources_read = array de strings contendo ao menos uma entrada com prefixo mcp:sqlite-router: e ao menos uma com prefixo mcp:bridge-monitor:
- bridge_state = objeto com:
  - inbox_pending_count
  - outbox_reply_count
  - last_reply_id
  - acks_count
- router_state = objeto com:
  - tables_found
  - response_cache_count
  - route_logs_count
  - cache_note
- findings = array de objetos com:
  - source
  - key
  - value
  - note
- anomalies = array de objetos com:
  - source
  - description
  - severity
  - suggested_action
- violations = array de strings
- previous_cycle = objeto com:
  - file = "cycle-000-bridge-only.json"
  - status = "passed"
- next_steps = array de strings com no máximo 5 itens
- meta = objeto com:
  - workspace
  - context_files_read
  - output_file = "output/cycle-001-router-read.json"

INSTRUÇÃO OPERACIONAL DO CICLO 1A
Você é o agent integration operando no ciclo 1A em modo router-read.

Tarefa:
- Ler apenas os arquivos de contexto autorizados
- Ler o baseline anterior em output/cycle-000-bridge-only.json
- Usar apenas os MCPs bridge-monitor e sqlite-router
- No sqlite-router, usar somente:
  - read_query
  - list_tables
  - describe_table
- Não usar write_query, create_table ou append_insight
- Não usar sqlite
- Não usar fetch
- Não escrever nenhum arquivo
- Produzir exatamente um payload JSON válido conforme este contrato
- Se houver ambiguidade, limitação ou bloqueio legítimo, registrar em violations com precisão

PRÉ-CHECAGEM OBRIGATÓRIA
Antes da execução, confirme:
- produção continua isolada
- bridge-monitor está presente
- sqlite-router está presente
- sqlite continua ausente
- fetch continua ausente
- cycle-000-bridge-only.json existe
- cycle1_router_read_contract.md existe
- caminho embedded/local está pronto
- gateway não será usado

EXECUÇÃO
- usar embedded/local
- usar agent integration
- não usar gateway
- não usar deliver
- não usar bindings
- timeout máximo de 5 minutos
- uma única tentativa apenas

VALIDAÇÃO OBRIGATÓRIA APÓS EXECUÇÃO
- payload foi retornado
- JSON parseável
- cycle = 1
- mode = router-read
- sources_read contém bridge-monitor
- sources_read contém sqlite-router
- previous_cycle.file = cycle-000-bridge-only.json
- previous_cycle.status = passed
- router_state comparado com o estado real do router_runtime.sqlite
- nenhuma ferramenta de escrita usada
- .mcp.json segue intacto
- bridge segue intacta
- produção segue isolada

PROIBIDO
- Não executar o ciclo 1B
- Não materializar output/cycle-001-router-read.json nesta rodada
- Não reativar sqlite
- Não reativar fetch
- Não tocar em C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES
- Não tocar em C:\AUTOMACAO\cowork\
- Não tocar em produção
- Não alterar gateway
- Não criar bindings ao workspace real
- Não fazer segunda tentativa nesta mesma rodada
