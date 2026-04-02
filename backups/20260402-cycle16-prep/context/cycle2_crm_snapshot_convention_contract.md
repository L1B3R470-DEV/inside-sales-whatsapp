# Contrato do Ciclo 2 Revisado por Convenção — CRM Snapshot + Router Baseline — Modelo 0A/0B

## Veredito
Neste ciclo, qualquer chamada às tools SQLite genéricas do runtime é tratada por convenção contratual explícita como pertencente ao snapshot do CRM, porque há exatamente um MCP SQLite ativo na execução. O agent usa bridge-monitor e o MCP SQLite único desta rodada, enquanto o estado do router vem exclusivamente do baseline já aprovado cycle-001-router-read.json. O payload continua estritamente sem PII.

## Definição do ciclo 2A revisado
Objetivo: validar leitura de dados agregados do CRM via snapshot isolado usando tools SQLite genéricas do runtime, combinando com estado atual da bridge e com baseline estático do router do ciclo 1.

MCP permitido:
- bridge-monitor
  - bridge_status
  - pending_tasks
  - recent_replies
  - recent_acks
  - tail_autopilot_log
- uma única instância de MCP SQLite ativa nesta execução, tratada por convenção como sqlite-crm-snapshot
  - read_query
  - list_tables
  - describe_table

Ferramentas proibidas:
- write_query
- create_table
- append_insight

Outras fontes permitidas:
- arquivos em workspace-integration/context/
- workspace-integration/output/cycle-001-router-read.json

Output esperado:
- payload JSON válido via resposta do agent
- sem escrita direta em arquivo pelo agent

Proibido:
- qualquer uso de sqlite-router
- qualquer consulta ao CRM live
- qualquer uso de fetch
- qualquer query retornando PII
- qualquer escrita em path pelo agent
- omitir a declaração explícita da convenção

Critério de sucesso:
- payload JSON válido
- sources_read contém ao menos uma entrada mcp:bridge-monitor:
- sources_read contém ao menos uma entrada mcp:sqlite-generic:
- sources_read contém a entrada convention:sqlite-generic-bound-to-crm-snapshot
- sources_read contém output:cycle-001-router-read.json
- context_binding presente e correto
- crm_snapshot_state coerente com o snapshot real
- router_baseline coerente com o arquivo baseline do ciclo 1
- nenhum PII detectado
- nenhuma tool de escrita usada
- violations vazio ou contendo apenas auto-reportes legítimos

Critério de bloqueio:
- payload ausente ou inválido
- qualquer PII em qualquer campo
- qualquer entrada mcp:sqlite-router: em sources_read
- crm_snapshot_state ausente ou divergente do snapshot real
- router_baseline ausente ou sem baseline_note explícita
- context_binding ausente ou incompleto
- sqlite_router_absent diferente de true
- crm_live_not_consulted diferente de true
- active_sqlite_mcp_count diferente de 1
- qualquer tool de escrita detectada

## Definição do ciclo 2B revisado
Objetivo: materializar de forma controlada o arquivo de output do ciclo 2 a partir do payload aprovado no ciclo 2A revisado, após inspeção PII obrigatória.

Entrada esperada:
- payload JSON aprovado no ciclo 2A revisado

Ação permitida:
- o orquestrador escreve workspace-integration/output/cycle-002-crm-snapshot.json com conteúdo idêntico ao payload aprovado

Critério de sucesso:
- arquivo existe
- parseável
- idêntico ao payload aprovado
- inspeção PII prévia aprovada

Critério de bloqueio:
- qualquer PII detectado antes da escrita
- qualquer diferença entre payload aprovado e arquivo escrito
- falha de escrita

## Schema lógico do payload
O payload é um único objeto JSON com os seguintes campos obrigatórios:

- cycle = inteiro 2
- mode = string "crm-snapshot-read"
- agent = string "integration"
- generated_at = string ISO 8601 UTC
- sources_read = array de strings contendo ao menos:
  - uma entrada com prefixo mcp:bridge-monitor:
  - uma entrada com prefixo mcp:sqlite-generic:
  - a entrada convention:sqlite-generic-bound-to-crm-snapshot
  - a entrada output:cycle-001-router-read.json
- context_binding = objeto com:
  - sqlite_generic_bound_to = "crm-snapshot"
  - sqlite_router_absent = true
  - crm_live_not_consulted = true
  - binding_note
- bridge_state = objeto com:
  - inbox_pending_count
  - outbox_reply_count
  - last_reply_id
  - acks_count
- router_baseline = objeto com:
  - source_file = "cycle-001-router-read.json"
  - cycle_approved_at
  - response_cache_count
  - route_logs_count
  - baseline_note
- crm_snapshot_state = objeto com:
  - snapshot_source
  - total_leads
  - leads_by_status
  - total_interactions
  - active_knowledge_rules
  - knowledge_cycles_executed
  - ignored_contacts_count
  - crm_note
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
  - file = "cycle-001-router-read.json"
  - status = "passed"
- next_steps = array de strings com no máximo 5 itens
- meta = objeto com:
  - workspace
  - context_files_read
  - snapshot_file
  - output_file = "output/cycle-002-crm-snapshot.json"
  - active_sqlite_mcp_count = 1
  - sqlite_tool_binding = "generic-sqlite-tools-bound-to-snapshot-by-contract"

RESTRIÇÃO ABSOLUTA DE PII
O payload NÃO pode conter:
- números de telefone
- nomes de leads
- razão social
- apelidos
- texto bruto de mensagens
- fragmentos de mensagens
- identificadores pessoais ou empresariais específicos
- qualquer valor que permita inferência individual direta

PRÉ-CHECAGENS OBRIGATÓRIAS
Antes da execução, confirme com evidência:
- produção continua isolada
- bridge-monitor está presente
- existe exatamente 1 MCP SQLite ativo na execução
- esse MCP ativo aponta para:
  C:\Users\User\.openclaw\snapshots\20260329-021916-cycle2-prep\crm_operacional.snapshot.sqlite
- sqlite-router está ausente da execução operacional
- fetch continua ausente
- cycle-001-router-read.json existe
- cycle2_crm_snapshot_convention_contract.md existe
- embedded/local está pronto
- gateway não será usado

Se qualquer item acima falhar:
- NÃO execute o ciclo
- apenas relate a falha

INSTRUÇÃO OPERACIONAL DO CICLO 2A REVISADO
Você é o agent integration operando no ciclo 2A revisado em modo crm-snapshot-read.

Tarefa:
- Ler apenas os arquivos de contexto autorizados
- Ler o baseline do router em output/cycle-001-router-read.json
- Usar bridge-monitor e a única superfície SQLite genérica disponível nesta execução
- Tratar essa superfície SQLite genérica como pertencente ao snapshot do CRM por convenção contratual explícita
- Não usar sqlite-router
- Não usar sqlite live
- Não usar fetch
- Não escrever nenhum arquivo
- Produzir exatamente um payload JSON válido conforme este contrato
- O payload deve conter apenas agregados, contagens, distribuições e diagnósticos de alto nível
- Se houver ambiguidade, limitação ou bloqueio legítimo, registrar em violations com precisão
- Se uma query tender a retornar PII, não a utilize; reporte a limitação em violations ou anomalies
- O campo router_baseline deve deixar explícito que os dados do router são herdados de baseline estático e não de leitura live
- O campo context_binding deve declarar explicitamente a convenção desta rodada

EXECUÇÃO
- usar embedded/local
- usar agent integration
- não usar gateway
- não usar deliver
- não usar bindings
- timeout máximo de 5 minutos
- uma única tentativa apenas
- se as pré-checagens falharem, não executar

VALIDAÇÃO OBRIGATÓRIA APÓS EXECUÇÃO
- payload foi retornado
- JSON parseável
- cycle = 2
- mode = crm-snapshot-read
- previous_cycle.file = cycle-001-router-read.json
- previous_cycle.status = passed
- sources_read contém bridge-monitor
- sources_read contém mcp:sqlite-generic:
- sources_read contém convention:sqlite-generic-bound-to-crm-snapshot
- sources_read contém output:cycle-001-router-read.json
- sources_read NÃO contém mcp:sqlite-router:
- context_binding.sqlite_generic_bound_to = crm-snapshot
- context_binding.sqlite_router_absent = true
- context_binding.crm_live_not_consulted = true
- meta.active_sqlite_mcp_count = 1
- bridge_state comparado com o estado real da bridge
- router_baseline comparado com o baseline do ciclo 1
- crm_snapshot_state comparado com o snapshot real do CRM
- nenhuma ferramenta de escrita usada
- inspeção explícita de PII em:
  - context_binding
  - crm_snapshot_state
  - findings
  - anomalies
  - next_steps
  - meta
- .mcp.json segue intacto
- bridge segue intacta
- produção segue isolada
- CRM live não foi usado operacionalmente

PROIBIDO
- Não executar o ciclo 2B
- Não materializar output/cycle-002-crm-snapshot.json nesta rodada
- Não usar sqlite-router operacionalmente
- Não usar o CRM live
- Não reativar fetch
- Não tocar em C:\AUTOMACAO\cowork\
- Não tocar em produção
- Não alterar gateway
- Não criar bindings ao workspace real
- Não fazer segunda tentativa nesta mesma rodada
