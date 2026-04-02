# Contrato do Ciclo 2 Revisado — CRM Snapshot + Router Baseline — Modelo 0A/0B

## Veredito
O ciclo 2 revisado elimina a colisão MCP removendo sqlite-router do escopo operacional. O agent usa bridge-monitor e sqlite-crm-snapshot, e herda o estado do router a partir do arquivo já aprovado cycle-001-router-read.json. O payload continua estritamente sem PII e segue o modelo 0A/0B.

## Definição do ciclo 2A revisado
Objetivo: validar leitura de dados agregados do CRM via snapshot isolado, combinando com estado atual da bridge e com baseline estático do router já aprovado, produzindo diagnóstico de alto nível sem PII e sem colisão MCP.

MCP permitido:
- bridge-monitor
  - bridge_status
  - pending_tasks
  - recent_replies
  - recent_acks
  - tail_autopilot_log
- sqlite-crm-snapshot
  - read_query
  - list_tables
  - describe_table

Ferramentas proibidas em qualquer MCP:
- write_query
- create_table
- append_insight

Outras fontes permitidas:
- arquivos em workspace-integration/context/
- workspace-integration/output/cycle-001-router-read.json

Output esperado:
- payload JSON válido entregue via resposta do agent
- sem escrita direta em arquivo pelo agent

Proibido:
- qualquer chamada ao sqlite-router via MCP
- qualquer chamada ao crm_operacional.sqlite live
- qualquer chamada a fetch
- qualquer query retornando PII
- qualquer uso de write_query, create_table ou append_insight
- qualquer escrita em path pelo agent
- tratar cycle-001-router-read.json como dado live; ele é baseline estático

Critério de sucesso:
- payload JSON válido
- sources_read contém ao menos uma entrada mcp:bridge-monitor:
- sources_read contém ao menos uma entrada mcp:sqlite-crm-snapshot:
- sources_read contém ao menos uma entrada output:cycle-001-router-read.json
- crm_snapshot_state coerente com o snapshot real
- router_baseline coerente com o arquivo baseline do ciclo 1
- nenhum PII detectado em nenhum campo
- violations vazio ou contendo apenas auto-reportes legítimos

Critério de bloqueio:
- payload ausente ou inválido
- qualquer PII em qualquer campo
- qualquer entrada mcp:sqlite-router: em sources_read
- crm_snapshot_state ausente ou divergente do snapshot real
- router_baseline ausente ou sem baseline_note explícita
- qualquer ferramenta de escrita detectada

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

## Schema lógico do payload do ciclo 2A revisado
O payload é um único objeto JSON com os seguintes campos obrigatórios:

- cycle = inteiro 2
- mode = string "crm-snapshot-read"
- agent = string "integration"
- generated_at = string ISO 8601 UTC
- sources_read = array de strings contendo ao menos:
  - uma entrada com prefixo mcp:bridge-monitor:
  - uma entrada com prefixo mcp:sqlite-crm-snapshot:
  - uma entrada com prefixo output:cycle-001-router-read.json
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
