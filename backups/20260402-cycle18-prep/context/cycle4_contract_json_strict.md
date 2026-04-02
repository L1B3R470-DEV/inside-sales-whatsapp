# Contrato do Ciclo 4 — Execution Planning — JSON Strict — Modelo 0A/0B

## Veredito
O ciclo 4 transforma recomendações analíticas aprovadas em propostas técnicas concretas, classificadas por risco e ordenadas para execução supervisionada futura. O agent não aplica nada; ele produz apenas um plano técnico rastreável ao ciclo 3. A resposta deve ser APENAS JSON válido.

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

## Objetivo do ciclo 4A
Ler o cycle-003-improvement-plan.json aprovado e produzir, para cada recomendação do ciclo 3, uma classificação de risco, uma proposta técnica concreta e um status de elegibilidade para execução supervisionada, sem aplicar nenhuma mudança.

## Fontes permitidas
- workspace-integration/output/cycle-003-improvement-plan.json
- workspace-integration/output/cycle-002-crm-snapshot.json
- workspace-integration/output/cycle-001-router-read.json
- workspace-integration/cycle4-input/
- workspace-integration/context/
- bridge-monitor
- uma única superfície SQLite genérica por convenção de unicidade, vinculada explicitamente ao alvo ativo da rodada

## Proibido
- qualquer patch, diff ou instrução diretamente aplicável ao projeto real
- qualquer write_query ou create_table em qualquer MCP
- qualquer conteúdo com PII
- qualquer file write pelo agent
- qualquer item não rastreável ao cycle-003-improvement-plan.json
- qualquer ambiguidade sem validation_criteria correspondente

## Critério de sucesso
- payload JSON válido
- todas as recomendações do ciclo 3 classificadas por risco
- ao menos 2 itens com status = ready_for_execution
- cada item low ou medium com technical_spec completa
- violations vazio ou contendo apenas auto-relatos legítimos
- zero PII detectado

## Critério de bloqueio
- qualquer PII
- qualquer item sem rec_id rastreável ao ciclo 3
- payload sem risk_summary
- payload com zero itens ready_for_execution sem justificativa
- technical_spec ausente em item low ou medium
- qualquer texto fora do objeto JSON

## Template rígido obrigatório do objeto raiz
Use EXATAMENTE esta estrutura de topo e esta ordem de campos:

{
  "cycle": 4,
  "mode": "execution-planning",
  "agent": "integration",
  "generated_at": "ISO-8601-UTC",
  "input_cycle": 3,
  "input_file": "cycle-003-improvement-plan.json",
  "sources_read": [],
  "context_binding": {
    "sqlite_generic_bound_to": "",
    "sqlite_router_absent": true,
    "crm_live_not_consulted": true,
    "binding_note": ""
  },
  "risk_summary": {
    "low_count": 0,
    "medium_count": 0,
    "high_count": 0,
    "ready_for_execution_count": 0,
    "blocked_count": 0,
    "hypothesis_only_count": 0
  },
  "execution_candidates": [],
  "execution_plan": [],
  "blocked_items": [],
  "hypothesis_only": [],
  "anomalies": [],
  "violations": [],
  "previous_cycle": {
    "file": "cycle-003-improvement-plan.json",
    "status": "approved"
  },
  "next_steps": [],
  "meta": {
    "workspace": "",
    "context_files_read": [],
    "output_file": "output/cycle-004-execution-plan.json",
    "candidates_count": 0
  }
}

## Regras de cada item de execution_candidates
Cada item deve conter:
- rec_id
- title
- category
- risk_level
- risk_rationale
- eligible_for_execution
- status
- status_reason
- dependencies
- execution_order
- technical_spec
- validation_required
- validation_note

## Regras de technical_spec
Para itens low e medium, technical_spec é obrigatório e deve conter:
- target_file
- target_component
- change_type
- description
- pre_conditions
- validation_criteria
- rollback_procedure

Para itens high, technical_spec pode ser nulo somente se o status for hypothesis_only ou blocked com justificativa clara.

## Classificação de risco
- low
- medium
- high

## Instrução operacional final
Sua resposta COMPLETA deve ser APENAS o objeto JSON final.
Sem texto antes.
Sem texto depois.
Sem markdown.
Sem bloco de código.
Comece com `{` e termine com `}`.
