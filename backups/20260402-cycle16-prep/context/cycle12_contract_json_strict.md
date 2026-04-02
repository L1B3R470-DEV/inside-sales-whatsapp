# Contrato do Ciclo 12 — Next Item Reopen — JSON Strict — Modelo 0A/0B

## Veredito
O ciclo 12 é o ciclo de reabertura controlada do próximo item após o fechamento estável de `R6`. Ele existe para identificar formalmente o item sucessor, verificar se ele continua válido no baseline pós-`R6` e definir a cadeia mínima obrigatória antes de qualquer futura escrita. A resposta deve ser APENAS JSON válido.

## Regra Absoluta de Formato
Sua resposta COMPLETA deve ser APENAS JSON válido.

Regras obrigatórias:
- não escrever nenhum texto antes do JSON
- não escrever nenhum texto depois do JSON
- não usar markdown
- não usar comentários
- a resposta deve começar com `{`
- a resposta deve terminar com `}`
- todos os campos estruturais abaixo são de primeiro nível do objeto raiz
- se você não conseguir preencher algum campo sem inventar dados, use valor estrutural válido e registre a limitação em `violations`

## Objetivo do ciclo 12A
Identificar formalmente o próximo item elegível após `R6`, verificar se ele continua válido no baseline pós-`R6` e definir a cadeia mínima obrigatória anterior a qualquer futura escrita.

## Fontes permitidas
Use EXCLUSIVAMENTE estas fontes, com esta precedência lógica:
- cycle-011-stability-report.json
- cycle-010-real-write-evidence.json
- cycle-009-real-write-handoff.json
- cycle-005-write-proposals.json
- cycle-004-execution-plan.json
- cycle-003-improvement-plan.json

## Proibido
- assumir que `R2` é o próximo item sem prova cruzada nas fontes
- usar artefatos fora da lista oficial como verdade
- propor SQL, DDL, DML, comandos operacionais, patches ou paths de execução
- carregar permissões, escopo ou autorização de escrita de `R6`
- qualquer escrita
- qualquer conteúdo com PII

## Critério de sucesso
- payload JSON válido
- identifica um único próximo item elegível ou declara `undetermined`
- demonstra rastreabilidade entre as fontes
- declara compatibilidade ou incompatibilidade com o baseline pós-`R6`
- define a cadeia mínima anterior a qualquer futura escrita
- declara explicitamente `authorization_inheritance = false`
- `violations` vazio ou contendo apenas auto-relatos legítimos
- zero PII

## Critério de bloqueio
- conflito entre fontes oficiais
- ausência de prova suficiente para ordenar o próximo item
- incompatibilidade do candidato com o baseline pós-`R6`
- qualquer indício de autorização herdada de `R6`
- qualquer conteúdo que antecipe escrita futura como autorizada
- qualquer texto fora do objeto JSON

## Skeleton obrigatório do objeto raiz
Use EXATAMENTE esta estrutura de topo e esta ordem de campos.
O skeleton abaixo define a ESTRUTURA, não os valores.

{
  "cycle_id": "12A",
  "mode": "next-item-reopen",
  "agent": "integration",
  "generated_at": "ISO-8601-UTC",
  "input_cycle": 11,
  "input_file": "cycle-011-stability-report.json",
  "closed_item_reference": "R6",
  "source_precedence": [],
  "baseline_post_r6": {
    "target_db": "",
    "wal_mode_confirmed": true,
    "cache_observability_windows_exists": false,
    "cache_observability_windows_row_count": 0,
    "schema_stable": false,
    "drift_absent": false,
    "other_tables_unchanged": false
  },
  "candidate_items": [],
  "next_eligible_item": "",
  "eligibility_justification": "",
  "post_r6_compatibility": {
    "status": "",
    "reason": ""
  },
  "minimal_required_chain": [],
  "readiness_classification": "",
  "authorization_reset": {
    "authorization_inheritance": false,
    "scope_reused": false,
    "premises_reused": false,
    "note": ""
  },
  "blockers": [],
  "prohibitions": [],
  "recommended_next_step": "",
  "evidence_trace": [],
  "anomalies": [],
  "violations": [],
  "previous_cycle": {
    "file": "cycle-011-stability-report.json",
    "status": "approved"
  },
  "next_steps": [],
  "meta": {
    "workspace": "",
    "context_files_read": [],
    "output_file": "output/cycle-012A-next-item-reopen-contract.json"
  }
}

## Regras de candidate_items
Cada item deve conter:
- rec_id
- source_cycle
- historical_priority
- historical_execution_order
- historical_application_order
- historical_status
- evidence
- conflicts

## Regras de next_eligible_item
- deve conter um único `rec_id` ou o literal `undetermined`
- `R2` só pode aparecer se for sustentado pelas fontes oficiais

## Classificação de prontidão
`readiness_classification` só pode ser:
- `BLOQUEADO`
- `ELEGIVEL_CONDICIONAL`
- `PRONTO_PARA_REABERTURA_CONTROLADA`

## Regras de autorização
- `authorization_inheritance` deve ser `false`
- nenhuma autorização de `R6` pode ser herdada
- a saída do ciclo 12 não autoriza escrita; no máximo autoriza a próxima fase analítica/read-only do item reaberto

## Instrução operacional final
Sua resposta COMPLETA deve ser APENAS o objeto JSON final.
Sem texto antes.
Sem texto depois.
Sem markdown.
Comece com `{` e termine com `}`.

PRÉ-CHECAGEM OBRIGATÓRIA
Antes da execução, confirme:
- produção continua isolada
- cycle12-input existe
- artifact_index.json existe
- closed_item_record.json existe
- next_candidate_registry.json existe
- post_r6_constraints.json existe
- cycle12_scope_draft.json existe
- cycle-011-stability-report.json existe
- cycle-010-real-write-evidence.json existe
- cycle-009-real-write-handoff.json existe
- cycle-005-write-proposals.json existe
- cycle-004-execution-plan.json existe
- cycle-003-improvement-plan.json existe
- cycle12_contract_json_strict.md existe
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
- não executar nenhuma escrita

VALIDAÇÃO OBRIGATÓRIA APÓS EXECUÇÃO
- payload foi retornado
- JSON parseável
- cycle_id = 12A
- mode = next-item-reopen
- closed_item_reference = R6
- source_precedence preenchido corretamente
- next_eligible_item preenchido
- authorization_inheritance = false
- readiness_classification preenchida
- evidence_trace presente
- nenhuma PII detectada
- não existe texto fora do objeto JSON
- .mcp.json segue intacto
- bridge segue intacta
- produção segue isolada
- nenhuma escrita ocorreu nesta rodada
