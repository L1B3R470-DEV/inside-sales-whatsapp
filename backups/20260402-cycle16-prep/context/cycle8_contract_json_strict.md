# Contrato do Ciclo 8 — Sandbox Inspection — JSON Strict — Modelo 0A/0B

## Veredito
O ciclo 8 é o ciclo de inspeção e veredicto. Ele lê o artefato sandbox produzido no ciclo 7, cruza com o plano aprovado do ciclo 6 e emite uma decisão técnica de promoção. Não escreve, não modifica e não toca em produção. A resposta deve ser APENAS JSON válido.

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

## Objetivo do ciclo 8A
Ler o artefato sandbox do ciclo 7 e o plano aprovado do ciclo 6, comparar o `after_state` com o `proposed_state` autorizado, verificar integridade de escopo, avaliar suficiência da validação local e emitir decisão de promoção fundamentada, sem escrever nada.

## Fontes permitidas
- workspace-integration/output/cycle-007-sandbox-write-evidence.json
- workspace-integration/output/cycle-006-isolated-write-plan.json
- workspace-integration/output/cycle-005-write-proposals.json
- workspace-integration/output/cycle-003-improvement-plan.json
- workspace-integration/cycle8-input/artifact_index.json
- workspace-integration/cycle8-input/sandbox_artifact_target.json
- workspace-integration/cycle8-input/before_after_review.json
- workspace-integration/cycle8-input/promotion_criteria.json
- workspace-integration/cycle8-input/scope_integrity.json
- workspace-integration/context/
- leitura read-only do arquivo espelho em sandbox já usado no ciclo 7

## Proibido
- qualquer escrita no projeto real
- qualquer escrita na sandbox
- qualquer modificação de artefato existente
- qualquer write_query, create_table ou append_insight em qualquer MCP
- qualquer conteúdo com PII
- processar mais de um item
- emitir approved_for_promotion sem checklist completo com todos os itens passed

## Critério de sucesso
- payload JSON válido
- todos os itens do integrity_checklist preenchidos com result e observation
- after_state_vs_proposed com comparação explícita
- scope_extrapolation_detected declarado
- validation_sufficiency avaliado
- promotion_decision declarado com justification não vazia
- violations vazio ou contendo apenas auto-relatos legítimos
- zero PII

## Critério de bloqueio
- qualquer PII
- promotion_decision sem justification
- integrity_checklist incompleto
- after_state_vs_proposed.match ausente
- artefato sandbox não encontrado em mirror_path
- scope_extrapolation_detected = true sem análise de impacto
- qualquer texto fora do objeto JSON

## Skeleton obrigatório do objeto raiz
Use EXATAMENTE esta estrutura de topo e esta ordem de campos.
O skeleton abaixo define a ESTRUTURA, não os valores.

{
  "cycle": 8,
  "mode": "sandbox-inspection",
  "agent": "integration",
  "generated_at": "ISO-8601-UTC",
  "input_cycle": 7,
  "input_file": "cycle-007-sandbox-write-evidence.json",
  "selected_item": "",
  "sources_read": [],
  "context_binding": {
    "sqlite_generic_bound_to": "",
    "sqlite_router_absent": true,
    "crm_live_not_consulted": true,
    "binding_note": ""
  },
  "artifact_summary": {
    "sandbox_file_read": false,
    "mirror_path_confirmed": "",
    "target_file": "",
    "change_type": "",
    "lines_affected_cycle7": 0,
    "sandbox_current_state_matches_after_state": false
  },
  "integrity_checklist": [],
  "after_state_vs_proposed": {
    "proposed_state_cycle6": "",
    "after_state_cycle7": "",
    "match": "",
    "divergence_detail": ""
  },
  "scope_extrapolation_detected": false,
  "scope_extrapolation_detail": null,
  "validation_sufficiency": {
    "steps_total": 0,
    "steps_executed": 0,
    "steps_passed": 0,
    "steps_not_applicable": 0,
    "sufficient_for_promotion": false,
    "insufficiency_reason": ""
  },
  "promotion_decision": "",
  "promotion_justification": "",
  "promotion_conditions": [],
  "anomalies": [],
  "violations": [],
  "previous_cycle": {
    "file": "cycle-007-sandbox-write-evidence.json",
    "status": "approved"
  },
  "next_steps": [],
  "meta": {
    "workspace": "",
    "context_files_read": [],
    "output_file": "output/cycle-008-promotion-decision.json",
    "checklist_items_total": 0,
    "checklist_items_passed": 0
  }
}

## Regras de integrity_checklist
Deve conter exatamente estes checks:
- after_state_matches_proposed
- change_scope_within_bounds
- no_unintended_modifications
- pre_conditions_were_satisfied
- validation_steps_executed
- real_file_confirmed_untouched
- rollback_available

Cada item deve conter:
- check
- result
- observation
- source

## Regras de decisão
promotion_decision só pode ser:
- approved_for_promotion
- pending_conditions
- blocked

## Restrições de conteúdo
- o payload deve tratar somente o item selecionado
- deve haver releitura direta do espelho em sandbox neste ciclo
- não usar diff executável
- não escrever nada

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
- cycle8-input existe
- artifact_index.json existe
- sandbox_artifact_target.json existe
- before_after_review.json existe
- promotion_criteria.json existe
- scope_integrity.json existe
- cycle-007-sandbox-write-evidence.json existe
- cycle-006-isolated-write-plan.json existe
- cycle-005-write-proposals.json existe
- cycle8_contract_json_strict.md existe
- Invoke-OpenClawSafe.ps1 existe
- o launcher seguro continua validado
- embedded/local está pronto
- gateway não será usado
- o item selecionado continua sendo o único item autorizado
- o arquivo espelho em sandbox está legível em read-only

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
- cycle = 8
- mode = sandbox-inspection
- input_cycle = 7
- selected_item correto
- sandbox_file_read = true
- integrity_checklist completo
- after_state_vs_proposed.match preenchido
- promotion_decision preenchido
- promotion_justification preenchida
- nenhuma entrada contém PII
- não existe texto fora do objeto JSON
- .mcp.json segue intacto
- bridge segue intacta
- produção segue isolada
- nenhuma escrita ocorreu nesta rodada
