# Contrato do Ciclo 9 — Real Write Handoff — JSON Strict — Hybrid

## Veredito
O ciclo 9 passa a operar em modo híbrido. O agent NÃO executa a escrita real. O agent produz o artefato exato e auditado da operação DDL-only para `R6`, e a execução real fica reservada ao orquestrador local.

## Regra Absoluta de Formato
Sua resposta COMPLETA deve ser APENAS JSON válido.
- sem texto antes
- sem texto depois
- sem markdown
- sem comentários
- começar com `{`
- terminar com `}`

## Objetivo do ciclo 9A híbrido
Produzir o pacote técnico final e auditado da operação real de `R6` no arquivo:
C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\router_runtime.sqlite

Sem executar:
- backup
- DDL
- validação real
- rollback real

## Operação autorizada
A única operação que poderá ser executada futuramente pelo orquestrador local é:

CREATE TABLE IF NOT EXISTS cache_observability_windows (
  window_start TEXT NOT NULL,
  window_end TEXT NOT NULL,
  response_cache_count INTEGER NOT NULL,
  cache_hit_count INTEGER NOT NULL,
  notes TEXT NOT NULL
)

## Operações proibidas
- qualquer INSERT
- qualquer UPDATE
- qualquer DELETE
- qualquer escrita em outra tabela
- qualquer escrita em outro arquivo
- qualquer mudança em produção
- qualquer execução real nesta rodada

## Fontes permitidas
- workspace-integration/output/cycle-008-promotion-decision.json
- workspace-integration/output/cycle-007-sandbox-write-evidence.json
- workspace-integration/output/cycle-006-isolated-write-plan.json
- workspace-integration/context/
- workspace-integration/cycle9-input/
- leitura read-only do único arquivo-alvo real
- bridge-monitor
- uma única superfície SQLite genérica por convenção de unicidade, vinculada explicitamente ao alvo ativo da rodada

## Critério de sucesso
- payload JSON válido
- selected_item = R6
- target_file único confirmado
- ddl_statement exato presente
- ddl_statement contém apenas DDL
- validation_queries exatas presentes
- backup_plan exato presente
- rollback_plan exato presente
- execution_sequence completa
- zero PII
- nenhuma execução real ocorreu

## Critério de bloqueio
- qualquer ambiguidade sobre o schema
- qualquer INSERT, UPDATE ou DELETE no payload
- qualquer referência a mais de um arquivo real
- qualquer texto fora do JSON
- ausência de backup_plan
- ausência de validation_queries
- ausência de rollback_plan

## Skeleton obrigatório do objeto raiz
{
  "cycle": 9,
  "mode": "real-write-handoff",
  "agent": "integration",
  "generated_at": "ISO-8601-UTC",
  "input_cycle": 8,
  "input_file": "cycle-008-promotion-decision.json",
  "selected_item": "R6",
  "sources_read": [],
  "context_binding": {
    "sqlite_generic_bound_to": "",
    "sqlite_router_absent": true,
    "crm_live_not_consulted": true,
    "binding_note": ""
  },
  "target_summary": {
    "rec_id": "R6",
    "target_file": "",
    "target_component": "",
    "change_type": "ddl_only",
    "promotion_decision_confirmed": false
  },
  "baseline_confirmation": {
    "target_exists": false,
    "target_hash_sha256": "",
    "target_size_bytes": 0,
    "target_last_write_utc": "",
    "table_absent_precheck": false
  },
  "ddl_artifact": {
    "ddl_statement": "",
    "ddl_purpose": "",
    "ddl_only_confirmed": false,
    "schema_matches_cycle7": false
  },
  "backup_plan": {
    "backup_required": true,
    "backup_path": "",
    "backup_method": "full_copy",
    "backup_verification_required": true
  },
  "validation_queries": {
    "table_exists_query": "",
    "table_empty_query": "",
    "expected_table_exists": true,
    "expected_row_count": 0
  },
  "rollback_plan": {
    "rollback_trigger": "",
    "rollback_method": "restore_full_backup",
    "rollback_path": "",
    "rollback_verification_required": true
  },
  "execution_sequence": [],
  "handoff_decision": "",
  "handoff_justification": "",
  "handoff_conditions": [],
  "anomalies": [],
  "violations": [],
  "previous_cycle": {
    "file": "cycle-008-promotion-decision.json",
    "status": "approved"
  },
  "next_steps": [],
  "meta": {
    "workspace": "",
    "context_files_read": [],
    "output_file": "output/cycle-009-real-write-handoff.json"
  }
}

## Regras do payload
- `ddl_statement` deve conter EXATAMENTE o DDL aprovado
- `ddl_statement` não pode conter DML
- `execution_sequence` deve listar somente passos do orquestrador local
- `handoff_decision` só pode ser:
  - ready_for_local_execution
  - pending_conditions
  - blocked
- o payload deve deixar explícito que nenhuma execução real ocorreu nesta rodada

## Instrução operacional final
Sua resposta COMPLETA deve ser APENAS o objeto JSON final.
Sem texto antes.
Sem texto depois.
Comece com `{` e termine com `}`.

PRÉ-CHECAGEM OBRIGATÓRIA
Antes da execução, confirme:
- produção continua isolada
- cycle9-input existe
- artifact_index.json existe
- real_write_target.json existe
- rollback_baseline.json existe
- write_scope_lock.json existe
- promotion_gate.json existe
- cycle-008-promotion-decision.json existe
- cycle9_contract_json_strict_hybrid.md existe
- Invoke-OpenClawSafe.ps1 existe
- launcher seguro continua validado
- embedded/local está pronto
- gateway não será usado
- selected_item = R6
- target_file é o único arquivo autorizado
- o schema DDL exato está claro
- a operação permanece DDL-only
- nenhuma execução real será feita nesta rodada

EXECUÇÃO
- usar embedded/local
- usar agent integration
- usar exclusivamente Invoke-OpenClawSafe.ps1
- timeout máximo de 5 minutos
- uma única tentativa apenas
- não executar backup real
- não executar DDL real

VALIDAÇÃO OBRIGATÓRIA APÓS EXECUÇÃO
- payload retornado
- JSON parseável
- cycle = 9
- mode = real-write-handoff
- selected_item = R6
- ddl_statement presente
- ddl_only_confirmed = true
- schema_matches_cycle7 = true
- backup_plan presente
- validation_queries presentes
- rollback_plan presente
- handoff_decision preenchido
- nenhuma DML detectada
- nenhuma PII detectada
- nenhuma execução real ocorreu
