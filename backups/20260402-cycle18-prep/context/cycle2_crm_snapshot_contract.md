# Contrato do Ciclo 2 — CRM Snapshot Read — Modelo 0A/0B

## Veredito
O ciclo 2 introduz a primeira leitura de dados do CRM pelo agent, com uma proteção estrutural central: o agent nunca toca no crm_operacional.sqlite live — apenas em um snapshot isolado criado antes do ciclo pelo orquestrador/Codex. O escopo do payload é restrito a agregados e contagens. Nenhum dado pessoal identificável pode aparecer em nenhum campo do output.

## Definição do ciclo 2A
Objetivo: validar que o agent consegue ler dados agregados do CRM via snapshot isolado, combiná-los com o estado do router e da bridge, e produzir diagnóstico de alto nível sobre o sistema sem expor nenhum dado pessoal identificável.

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
- sqlite-crm-snapshot
  - read_query
  - list_tables
  - describe_table

Ferramentas proibidas em qualquer MCP, mesmo que tecnicamente disponíveis:
- write_query
- create_table
- append_insight

Outras fontes permitidas:
- arquivos em workspace-integration/context/
- workspace-integration/output/cycle-001-router-read.json

Output esperado:
- payload JSON válido entregue via resposta do agent
- sem exigência de escrita direta em arquivo no ciclo 2A

Proibido:
- qualquer chamada ao crm_operacional.sqlite live
- qualquer chamada a fetch
- qualquer query que retorne números de telefone, nomes, texto de mensagens ou qualquer dado pessoal identificável
- qualquer uso de write_query, create_table ou append_insight
- qualquer escrita em path pelo agent

Critério de sucesso:
- payload JSON válido
- sources_read contém bridge-monitor
- sources_read contém sqlite-router
- sources_read contém sqlite-crm-snapshot
- crm_snapshot_state coerente com o snapshot real
- previous_cycle aponta para cycle-001-router-read.json com status passed
- nenhum campo contém PII
- violations vazio ou contendo apenas auto-reportes legítimos

Critério de bloqueio:
- payload ausente ou inválido
- ausência de entrada mcp:sqlite-crm-snapshot: em sources_read
- qualquer PII detectado em qualquer campo do payload
- crm_snapshot_state divergente do snapshot real em mais de 10%
- previous_cycle ausente ou diferente de passed
- qualquer ferramenta de escrita detectada

## Definição do ciclo 2B
Objetivo: materializar de forma controlada o arquivo de output do ciclo 2 a partir do payload aprovado no ciclo 2A, após inspeção PII obrigatória.

Entrada esperada:
- payload JSON aprovado no ciclo 2A

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

## Schema lógico do payload do ciclo 2A
O payload é um único objeto JSON com os seguintes campos obrigatórios:

- cycle = inteiro 2
- mode = string "crm-snapshot-read"
- agent = string "integration"
- generated_at = string ISO 8601 UTC
- sources_read = array de strings contendo ao menos uma entrada com prefixo mcp:sqlite-crm-snapshot:, uma com mcp:sqlite-router: e uma com mcp:bridge-monitor:
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

INSTRUÇÃO OPERACIONAL DO CICLO 2A
Você é o agent integration operando no ciclo 2A em modo crm-snapshot-read.

Tarefa:
- Ler apenas os arquivos de contexto autorizados
- Ler o baseline anterior em output/cycle-001-router-read.json
- Usar apenas os MCPs bridge-monitor, sqlite-router e sqlite-crm-snapshot
- No sqlite-router e sqlite-crm-snapshot, usar somente:
  - read_query
  - list_tables
  - describe_table
- Não usar write_query, create_table ou append_insight
- Não usar sqlite live
- Não usar fetch
- Não escrever nenhum arquivo
- Produzir exatamente um payload JSON válido conforme este contrato
- O payload deve conter apenas agregados, contagens, distribuições e diagnósticos de alto nível
- Se houver ambiguidade, limitação ou bloqueio legítimo, registrar em violations com precisão
- Se uma query tender a retornar PII, não a utilize; reporte a limitação em violations ou anomalies

PRÉ-CHECAGEM OBRIGATÓRIA
Antes da execução, confirme:
- produção continua isolada
- bridge-monitor está presente
- sqlite-router está presente
- sqlite-crm-snapshot está presente
- sqlite live continua fora do escopo operacional do ciclo
- fetch continua ausente
- cycle-001-router-read.json existe
- cycle2_crm_snapshot_contract.md existe
- o snapshot usado é exatamente:
  C:\Users\User\.openclaw\snapshots\20260329-021916-cycle2-prep\crm_operacional.snapshot.sqlite
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
- cycle = 2
- mode = crm-snapshot-read
- previous_cycle.file = cycle-001-router-read.json
- previous_cycle.status = passed
- sources_read contém bridge-monitor
- sources_read contém sqlite-router
- sources_read contém sqlite-crm-snapshot
- bridge_state comparado com o estado real da bridge
- router_state comparado com o estado real do router_runtime.sqlite
- crm_snapshot_state comparado com o snapshot real do CRM
- nenhuma ferramenta de escrita usada
- inspeção explícita de PII em:
  - crm_snapshot_state
  - findings
  - anomalies
  - next_steps
  - meta
- .mcp.json segue intacto
- bridge segue intacta
- produção segue isolada

PROIBIDO
- Não executar o ciclo 2B
- Não materializar output/cycle-002-crm-snapshot.json nesta rodada
- Não usar o CRM live
- Não reativar fetch
- Não tocar em C:\AUTOMACAO\cowork\
- Não tocar em produção
- Não alterar gateway
- Não criar bindings ao workspace real
- Não fazer segunda tentativa nesta mesma rodada
