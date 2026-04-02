# Contrato do Ciclo 5 — Write Preparation — JSON Strict V2 — Modelo 0A/0B

## Veredito
O ciclo 5 transforma itens low risk e ready_for_execution do ciclo 4 em propostas de escrita auditáveis, sem aplicar nada. O agent deve produzir apenas preparação de escrita: escopo, estado atual descrito, estado proposto descrito, plano de validação, plano de rollback e ordem segura futura. A resposta deve ser APENAS JSON válido.

## Regra Absoluta de Formato
Sua resposta COMPLETA deve ser APENAS JSON válido.

Regras obrigatórias:
- não escrever nenhum texto antes do JSON
- não escrever nenhum texto depois do JSON
- não usar markdown
- não usar ```json
- não usar comentários
- a resposta deve começar com `{`
- a resposta deve terminar com `}`
- todos os campos estruturais abaixo são de primeiro nível do objeto raiz
- se você não conseguir preencher algum campo sem inventar dados, use valor estrutural válido e registre a limitação em `violations`

## Regra Estrutural Crítica
`write_proposals` e `blocked_proposals` são dois arrays distintos no nível raiz do objeto JSON.
`blocked_proposals` começa APÓS o fechamento `]` de `write_proposals`.
`blocked_proposals` NUNCA pode ser elemento dentro de `write_proposals`.
Nenhum campo de nível raiz pode ser elemento de outro campo de nível raiz.

## Objetivo do ciclo 5A
Ler os itens `status = ready_for_execution` e `risk_level = low` do `cycle-004-execution-plan.json` e produzir, para cada um, uma proposta de escrita detalhada com escopo de mudança, estado atual descrito, estado proposto descrito, plano de validação objetivo e plano de rollback, sem aplicar nada.

## Fontes permitidas
- workspace-integration/output/cycle-004-execution-plan.json
- workspace-integration/output/cycle-003-improvement-plan.json
- workspace-integration/output/cycle-002-crm-snapshot.json
- workspace-integration/output/cycle-001-router-read.json
- workspace-integration/cycle5-input/low_risk_candidates.json
- workspace-integration/cycle5-input/write_scope_draft.json
- workspace-integration/cycle5-input/validation_matrix.json
- workspace-integration/cycle5-input/artifact_index.json
- workspace-integration/context/
- bridge-monitor
- uma única superfície SQLite genérica por convenção de unicidade, vinculada explicitamente ao alvo ativo da rodada

## Proibido
- qualquer write_query, create_table ou append_insight em qualquer MCP
- qualquer file write pelo agent
- qualquer patch, diff executável ou bloco de código pronto para aplicar
- qualquer conteúdo com PII
- propostas para itens que não estejam como `low` e `ready_for_execution` no ciclo 4
- qualquer instrução ambígua sem critério de validação objetivo
- `blocked_proposals` aninhado dentro de `write_proposals`

## Critério de sucesso
- payload JSON válido
- todos os itens `low` + `ready_for_execution` do ciclo 4 presentes em `write_proposals`
- `readiness_level` declarado para cada item
- ao menos 1 item com `readiness_level = ready`
- `validation_plan.success_criteria` objetivo e verificável para todos os itens `ready`
- `rollback_plan.procedure` preenchido para todos os itens `ready`
- `violations` vazio ou contendo apenas auto-relatos legítimos
- zero PII detectado
- `write_proposals` e `blocked_proposals` existem como arrays irmãos no nível raiz

## Critério de bloqueio
- qualquer PII
- qualquer item `low` do ciclo 4 ausente do payload sem justificativa
- `validation_plan.success_criteria` subjetivo em qualquer item `ready`
- `rollback_plan` ausente em qualquer item `ready`
- payload com zero itens `readiness_level = ready` sem justificativa de bloqueio documentada
- qualquer texto fora do objeto JSON
- `blocked_proposals` aninhado dentro de `write_proposals`
- qualquer campo de nível raiz aninhado dentro de outro campo de nível raiz

## Skeleton obrigatório do objeto raiz
Use EXATAMENTE esta estrutura de topo e esta ordem de campos.
O skeleton abaixo define a ESTRUTURA, não os valores.

{
  "cycle": 5,
  "mode": "write-preparation",
  "agent": "integration",
  "generated_at": "ISO-8601-UTC",
  "input_cycle": 4,
  "input_file": "cycle-004-execution-plan.json",
  "sources_read": [],
  "context_binding": {
    "sqlite_generic_bound_to": "",
    "sqlite_router_absent": true,
    "crm_live_not_consulted": true,
    "binding_note": ""
  },
  "readiness_summary": {
    "total_candidates": 0,
    "ready_count": 0,
    "pending_pre_condition_count": 0,
    "blocked_count": 0
  },
  "write_proposals": [],
  "blocked_proposals": [],
  "anomalies": [],
  "violations": [],
  "previous_cycle": {
    "file": "cycle-004-execution-plan.json",
    "status": "approved"
  },
  "next_steps": [],
  "meta": {
    "workspace": "",
    "context_files_read": [],
    "output_file": "output/cycle-005-write-proposals.json",
    "proposals_count": 0,
    "ready_count": 0
  }
}

## Regras de cada item de write_proposals
Cada item deve conter:
- rec_id
- title
- category
- readiness_level
- readiness_reason
- application_order
- write_scope
- validation_plan
- rollback_plan
- dependencies

## Regras de write_scope
`write_scope` deve conter:
- target_file
- target_component
- change_type
- current_state
- proposed_state
- change_summary
- estimated_scope
- pre_conditions

## Regras de validation_plan
`validation_plan` deve conter:
- method
- success_criteria
- observation_window
- test_steps

Os `success_criteria` devem ser objetivos e verificáveis.

## Regras de rollback_plan
`rollback_plan` deve conter:
- procedure
- estimated_effort
- risk_if_rollback_fails

## Classificação de prontidão
- ready
- pending_pre_condition
- blocked

## Restrições de conteúdo
- `current_state` e `proposed_state` devem ser descrições em linguagem natural
- nunca usar diff
- nunca usar bloco de código
- nunca usar instrução pronta para colar/aplicar
- `application_order` deve respeitar a ordem do ciclo 4 para itens `ready`

## Instrução operacional final
Sua resposta COMPLETA deve ser APENAS o objeto JSON final.
Sem texto antes.
Sem texto depois.
Sem markdown.
Sem bloco de código.
Comece com `{` e termine com `}`.

PRÉ-CHECAGEM OBRIGATÓRIA
Antes da execução, confirme:
- produção continua isolada
- cycle5-input existe
- artifact_index.json existe
- low_risk_candidates.json existe
- write_scope_draft.json existe
- validation_matrix.json existe
- cycle-004-execution-plan.json existe
- cycle-003-improvement-plan.json existe
- cycle-002-crm-snapshot.json existe
- cycle-001-router-read.json existe
- cycle5_contract_json_strict_v2.md existe
- Invoke-OpenClawSafe.ps1 existe
- o launcher seguro continua validado
- embedded/local está pronto
- gateway não será usado

EXECUÇÃO
- usar embedded/local
- usar agent integration
- usar exclusivamente Invoke-OpenClawSafe.ps1
- não usar gateway
- não usar deliver
- não usar bindings
- timeout máximo de 5 minutos
- uma única tentativa apenas

VALIDAÇÃO OBRIGATÓRIA APÓS EXECUÇÃO
- payload foi retornado
- JSON parseável
- cycle = 5
- mode = write-preparation
- input_cycle = 4
- input_file = cycle-004-execution-plan.json
- todos os itens low + ready_for_execution do ciclo 4 estão presentes
- há ao menos 1 item com readiness_level = ready
- success_criteria é objetivo em todos os itens ready
- rollback_plan está completo em todos os itens ready
- `write_proposals` e `blocked_proposals` são arrays irmãos no nível raiz
- nenhuma entrada contém patch/diff/instrução diretamente aplicável
- nenhuma PII detectada
- não existe texto fora do objeto JSON
- .mcp.json segue intacto
- bridge segue intacta
- produção segue isolada

FORMATO OBRIGATÓRIO DA RESPOSTA

INÍCIO DO RELATÓRIO

STATUS GERAL
- concluído: [sim/não/parcial]
- risco operacional atual: [baixo/médio/alto]

PRÉ-EXECUÇÃO
- produção continua isolada: [sim/não]
- cycle5-input presente: [sim/não]
- artifact_index.json presente: [sim/não]
- low_risk_candidates.json presente: [sim/não]
- write_scope_draft.json presente: [sim/não]
- validation_matrix.json presente: [sim/não]
- ciclos 1/2/3/4 presentes: [sim/não]
- contrato JSON strict v2 criado: [sim/não]
- launcher seguro presente: [sim/não]
- launcher seguro utilizado: [sim/não]
- embedded/local pronto: [sim/não]
- gateway não utilizado: [sim/não]

EXECUÇÃO
- ciclo 5A executado: [sim/não]
- timeout acionado: [sim/não]
- caminho usado: [embedded/local]
- observações:

PAYLOAD
- payload retornado: [sim/não]
- JSON parseável: [sim/não]
- cycle = 5: [sim/não]
- mode = write-preparation: [sim/não]
- input_cycle = 4: [sim/não]
- input_file = cycle-004-execution-plan.json: [sim/não]
- readiness_summary presente: [sim/não]
- todos os itens low + ready do ciclo 4 presentes: [sim/não/parcial]
- ao menos 1 item com readiness_level = ready: [sim/não]
- success_criteria objetivo nos itens ready: [sim/não/parcial]
- rollback_plan completo nos itens ready: [sim/não/parcial]
- write_proposals e blocked_proposals como irmãos no nível raiz: [sim/não]
- texto fora do JSON detectado: [sim/não]
- violations vazio ou apenas auto-reporte legítimo: [sim/não/parcial]

INSPEÇÃO DE QUALIDADE
- propostas sem patch/diff/instrução executável: [sim/não]
- nenhuma PII detectada: [sim/não]
- prontidão coerente: [sim/não/parcial]
- ordem de aplicação coerente: [sim/não/parcial]
- observações:

ISOLAMENTO PRESERVADO
- .mcp.json do projeto permaneceu intocado: [sim/não]
- bridge local permaneceu intocada: [sim/não]
- produção continua isolada após execução: [sim/não]
- nenhum vínculo ao workspace real foi criado: [sim/não]

CONCLUSÃO
- ciclo 5A aprovado: [sim/não/condicional]
- maior risco observado:
- pronto para discutir ciclo 5B: [sim/não]
- próximo passo sugerido:

ARTEFATOS
- relatório salvo em:
- payload/log fonte:
- launcher usado:
- contrato criado:
- configs alteradas nesta rodada:

FIM DO RELATÓRIO
