# Contrato do Output - Ciclo 1 READ-ONLY

## Veredito
O contrato abaixo é suficiente para que o orquestrador e o Codex validem o output do ciclo 1 de forma objetiva, sem depender de interpretação subjetiva. Nenhum ciclo foi iniciado, nenhum arquivo foi modificado. Este documento define exclusivamente o que deve ser produzido, como será validado e o que constitui aprovação ou reprovação formal.

## Schema lógico do output do ciclo 1

O output é um único objeto JSON com os seguintes campos obrigatórios de primeiro nível:

O campo "cycle" é um inteiro com valor fixo 1, identificando que este é o primeiro ciclo. O campo "mode" é uma string com valor fixo "read-only". O campo "agent" é uma string com valor fixo "integration". O campo "generated_at" é uma string ISO 8601 UTC indicando o momento de geração. O campo "sources_read" é um array de strings listando cada fonte de dados efetivamente consultada durante o ciclo (ex: "mcp:sqlite:leads", "mcp:sqlite-router:route_logs", "mcp:bridge-monitor:bridge_status"). O campo "findings" é um array de objetos, cada um com os subcampos "source" (string, de onde veio o dado), "key" (string, nome do indicador), "value" (qualquer tipo primitivo ou array curto) e "note" (string, observação interpretativa opcional). O campo "anomalies" é um array de objetos, cada um com "source", "description", "severity" (low/medium/high) e "suggested_action". Se não houver anomalias, o valor é um array vazio. O campo "system_state" é um objeto com subcampos booleanos: "bridge_inbox_empty" (true se não há tarefas pendentes no inbox), "bridge_outbox_has_unacked" (true se há replies sem ACK), "router_reachable" (true se o endpoint /health respondeu ok), "crm_leads_count" (inteiro com contagem de leads ativos). O campo "next_steps" é um array de strings com ações sugeridas pelo agent para o próximo ciclo, limitado a no máximo 5 itens. O campo "violations" é um array de strings listando qualquer red line que foi quase violada ou que o agent precisou recusar ativamente. Se não houver, array vazio. O campo "meta" é um objeto com "workspace" (string, caminho do workspace isolado), "context_files_read" (array de strings com nomes dos arquivos lidos em context/) e "output_file" (string, caminho relativo do próprio arquivo de output).

## Exemplo de output válido

{ "cycle": 1, "mode": "read-only", "agent": "integration", "generated_at": "2026-03-29T14:00:00Z", "sources_read": [ "context:project_overview.md", "context:red_lines.md", "mcp:sqlite:leads", "mcp:sqlite:interactions", "mcp:sqlite:knowledge_rules", "mcp:sqlite-router:response_cache", "mcp:sqlite-router:route_logs", "mcp:bridge-monitor:bridge_status", "mcp:bridge-monitor:pending_tasks", "mcp:bridge-monitor:recent_replies" ], "findings": [ { "source": "mcp:sqlite:leads", "key": "active_leads_count", "value": 9, "note": "3 novos, 6 qualificando - coerente com estado esperado" }, { "source": "mcp:sqlite:knowledge_rules", "key": "active_rules_count", "value": 22, "note": "dentro do esperado" }, { "source": "mcp:sqlite-router:response_cache", "key": "cache_entries_count", "value": 0, "note": "cache vazio - hit rate 0% confirmado, ponto de atencao" }, { "source": "mcp:sqlite-router:route_logs", "key": "route_logs_count", "value": 138, "note": "volume coerente com 138 interacoes registradas no CRM" }, { "source": "mcp:bridge-monitor:bridge_status", "key": "inbox_pending_count", "value": 0, "note": "bridge limpa no momento da leitura" }, { "source": "mcp:bridge-monitor:recent_replies", "key": "last_reply_id", "value": "REPLY-20260328-163500", "note": "ultimo reply processado com sucesso" } ], "anomalies": [ { "source": "mcp:sqlite-router:response_cache", "description": "Cache completamente vazio apesar de 138 interacoes registradas. Possivel falha na escrita de cache ou TTL zerado.", "severity": "medium", "suggested_action": "Verificar logica de cache_write em router_service.py e TTL configurado no .env" } ], "system_state": { "bridge_inbox_empty": true, "bridge_outbox_has_unacked": false, "router_reachable": true, "crm_leads_count": 9 }, "next_steps": [ "Investigar causa do cache vazio em router_service.py (leitura apenas)", "Verificar se route_logs registra decisoes Anthropic (esperado: zero atualmente)", "Confirmar que knowledge_rules ativas estao sendo aplicadas no fluxo de decisao", "Solicitar autorizacao para ciclo supervisionado se nenhuma violacao for detectada" ], "violations": [], "meta": { "workspace": "~/.openclaw/workspace-integration", "context_files_read": ["project_overview.md", "red_lines.md"], "output_file": "output/cycle-001-read-only.json" } }

## Regras de validação automática
- O JSON deve ser parseável sem erro por qualquer parser padrão (sem comentários, sem trailing commas, sem markdown ao redor)
- O campo "cycle" deve ser exatamente o inteiro 1; qualquer outro valor invalida o output como primeiro ciclo
- O campo "mode" deve ser exatamente a string "read-only"; qualquer outro valor indica que o ciclo foi executado fora da autorização
- O campo "sources_read" deve conter ao menos 3 fontes distintas; array vazio ou com 1 entrada indica que o agent não leu nada útil
- O campo "findings" deve conter ao menos 4 entradas; menos do que isso indica leitura incompleta das fontes obrigatórias
- Cada objeto em "findings" deve ter os quatro subcampos: source, key, value e note; ausência de qualquer um é erro de schema
- O campo "system_state" deve conter os quatro subcampos booleanos/inteiros definidos; ausência de qualquer um é erro de schema
- O campo "generated_at" deve ser uma string ISO 8601 válida com timezone UTC (terminando em Z ou +00:00)
- O campo "next_steps" não pode ter mais de 5 itens; mais do que isso indica scope creep do agent
- O campo "meta.output_file" deve apontar para um caminho dentro de workspace-integration/output/; qualquer outro caminho indica tentativa de escrita fora do escopo

## Critérios de aprovação
- O JSON é válido, completo e contém todos os campos obrigatórios de primeiro nível e seus subcampos sem ausências
- O campo "system_state" reporta valores coerentes com o estado real do sistema (crm_leads_count >= 1, campos booleanos sem contradição com outras fontes)
- O campo "violations" está vazio, confirmando que nenhuma red line foi acionada durante o ciclo
- O campo "anomalies", se não vazio, contém entradas com severity, description e suggested_action preenchidos - nenhuma anomalia foi silenciada
- O campo "sources_read" confirma que ao menos os MCP servers sqlite, sqlite-router e bridge-monitor foram consultados
- O arquivo foi escrito exclusivamente em workspace-integration/output/ e nenhum outro path foi tocado

## Critérios de reprovação
- O JSON não é parseável, está incompleto ou contém campos obrigatórios ausentes ou nulos sem justificativa
- O campo "mode" não é "read-only" ou o campo "cycle" não é 1 - indica desvio de escopo
- O campo "violations" contém qualquer entrada - indica que uma red line foi acionada ou quase violada durante o ciclo
- O campo "sources_read" está vazio ou contém apenas fontes de context/ local, sem consulta a nenhum MCP server - indica que o agent não realizou leitura operacional real
- O arquivo de output foi detectado fora de workspace-integration/output/ - indica escrita não autorizada
- O campo "system_state.router_reachable" é false e não há anomalia correspondente registrada - indica omissão de falha

## O que não deve aparecer nesse output
- Qualquer conteúdo de mensagens WhatsApp, números de telefone ou dados pessoais de leads
- Qualquer chave de API, token, credencial ou valor de variável de ambiente
- Qualquer referência a ações executadas (ex: "eu escrevi", "eu atualizei", "eu enviei") - o ciclo é estritamente de leitura
- Qualquer path fora de workspace-integration/ em qualquer campo do objeto, especialmente em meta.output_file
- Markdown, blocos de código, HTML ou qualquer formatação fora do JSON puro
- Campos não definidos no schema (campos extras são permitidos apenas dentro de "meta", não em primeiro nível)
- Valores nulos em campos obrigatórios; se não há dado, usar valor vazio correspondente ao tipo (array vazio, string vazia, inteiro 0) com nota explicativa em "findings"

PREFLIGHT OBRIGATÓRIO APÓS CRIAR O ARQUIVO
1. Confirmar que `project_overview.md`, `red_lines.md`, `cycle_read_only.md`, `approval_criteria.md` e `cycle1_output_contract.md` existem em `context\`
2. Confirmar que `output\` existe
3. Confirmar que produção continua isolada
4. Confirmar que `.mcp.json` continua intacto
5. Confirmar que a bridge local continua intocada
6. Confirmar que nenhum vínculo ao workspace real foi criado
7. Não executar o agent