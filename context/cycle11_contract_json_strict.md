# Contrato do Ciclo 11 — Post-Write Observation — JSON Strict — Modelo 0A/0B

## Veredito
O ciclo 11 é o ciclo de estabilização. Ele confirma que a primeira escrita real produziu um estado persistente e coerente, e emite uma decisão objetiva sobre R6 antes de qualquer discussão de próximo item. Não escreve nada; apenas lê, compara e decide. A resposta deve ser APENAS JSON válido.

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

## Objetivo do ciclo 11A
Ler o estado atual de `router_runtime.sqlite` via sqlite-router MCP em modo read-only, comparar com a evidência materializada do ciclo 10, verificar persistência e integridade de `cache_observability_windows`, detectar qualquer deriva inesperada e emitir decisão de estabilidade de `R6`.

## Fontes permitidas
- sqlite-router MCP via convenção de unicidade
- bridge-monitor MCP
- workspace-integration/output/cycle-010-real-write-evidence.json
- workspace-integration/output/cycle-009-real-write-handoff.json
- workspace-integration/output/cycle-007-sandbox-write-evidence.json
- workspace-integration/context/
- workspace-integration/cycle11-input/

## Proibido
- qualquer write_query
- qualquer create_table
- qualquer append_insight
- qualquer operação de escrita em qualquer MCP
- qualquer escrita no projeto real
- qualquer conteúdo com PII
- promoção automática do próximo item
- `stable_closed` com checklist incompleto ou com item failed/inconclusive

## Critério de sucesso
- payload JSON válido
- `cache_observability_windows` confirmada presente ao vivo
- `COUNT(*) = 0` confirmado ao vivo
- schema atual comparado ao ciclo 7/10 campo a campo
- checklist de coerência completo
- `stability_decision` declarado com `stability_justification` não vazia
- `violations` vazio ou contendo apenas auto-relatos legítimos
- zero PII

## Critério de bloqueio
- qualquer PII
- `stability_decision` sem `stability_justification`
- checklist incompleto
- `cache_observability_windows` ausente
- `COUNT(*) > 0`
- qualquer texto fora do objeto JSON

## Skeleton obrigatório do objeto raiz
Use EXATAMENTE esta estrutura de topo e esta ordem de campos.
O skeleton abaixo define a ESTRUTURA, não os valores.

{
  "cycle": 11,
  "mode": "post-write-observation",
  "agent": "integration",
  "generated_at": "ISO-8601-UTC",
  "input_cycle": 10,
  "input_file": "cycle-010-real-write-evidence.json",
  "sources_read": [],
  "context_binding": {
    "sqlite_generic_bound_to": "",
    "sqlite_router_absent": false,
    "crm_live_not_consulted": true,
    "binding_note": ""
  },
  "current_db_state": {
    "tables_present": [],
    "cache_observability_windows_found": false,
    "cache_observability_windows_row_count": 0,
    "schema_columns": [],
    "observed_at": ""
  },
  "coherence_checklist": [],
  "drift_analysis": {
    "drift_detected": false,
    "drift_type": null,
    "drift_detail": null,
    "drift_severity": "none"
  },
  "bridge_state_post_write": {},
  "stability_decision": "",
  "stability_justification": "",
  "progression_conditions": [],
  "anomalies": [],
  "violations": [],
  "previous_cycle": {
    "file": "cycle-010-real-write-evidence.json",
    "status": "approved"
  },
  "next_steps": [],
  "meta": {
    "workspace": "",
    "context_files_read": [],
    "output_file": "output/cycle-011-stability-report.json",
    "checklist_items_total": 0,
    "checklist_items_passed": 0
  }
}

## Regras de current_db_state
Deve conter:
- `tables_present`
- `cache_observability_windows_found`
- `cache_observability_windows_row_count`
- `schema_columns`
- `observed_at`

## Regras de coherence_checklist
Deve conter exatamente estes checks:
- `table_exists`
- `row_count_zero`
- `schema_matches_cycle10`
- `schema_matches_cycle7`
- `no_new_unexpected_tables`
- `existing_tables_unchanged`

Cada item deve conter:
- `check`
- `result`
- `observation`
- `source`

## Regras de drift_analysis
- se qualquer item do checklist for `failed`, então `drift_detected = true`
- se todos os itens forem `passed`, então `drift_detected = false`

## Regras de decisão
`stability_decision` só pode ser:
- `stable_closed`
- `stable_monitoring`
- `drift_detected`

## Restrições de conteúdo
- todas as queries do checklist devem ser executadas ao vivo neste ciclo
- `observed_at` deve refletir leitura deste ciclo
- `progression_conditions` só pode ser preenchido se `stability_decision` for `stable_closed` ou `stable_monitoring`
- se `stability_decision = drift_detected`, então `progression_conditions` deve estar vazio

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
- cycle11-input existe
- artifact_index.json existe
- post_write_target.json existe
- refreshed_baseline_scope.json existe
- observation_gate.json existe
- next_item_readiness.json existe
- cycle-010-real-write-evidence.json existe
- cycle-009-real-write-handoff.json existe
- cycle-007-sandbox-write-evidence.json existe
- cycle11_contract_json_strict.md existe
- Invoke-OpenClawSafe.ps1 existe
- o launcher seguro continua validado
- embedded/local está pronto
- gateway não será usado
- sqlite-router MCP está acessível em read-only
- bridge-monitor MCP está acessível

EXECUÇÃO
- usar embedded/local
- usar agent integration
- usar exclusivamente Invoke-OpenClawSafe.ps1
- não usar gateway
- não usar deliver
- não usar bindings
- timeout máximo de 5 minutos
- uma única tentativa apenas
- não executar nenhuma escrita

VALIDAÇÃO OBRIGATÓRIA APÓS EXECUÇÃO
- payload foi retornado
- JSON parseável
- cycle = 11
- mode = post-write-observation
- `cache_observability_windows_found = true`
- `cache_observability_windows_row_count = 0`
- checklist completo
- `stability_decision` preenchido
- `stability_justification` preenchida
- nenhuma PII detectada
- não existe texto fora do objeto JSON
- .mcp.json segue intacto
- bridge segue intacta
- produção segue isolada
- nenhuma escrita ocorreu nesta rodada