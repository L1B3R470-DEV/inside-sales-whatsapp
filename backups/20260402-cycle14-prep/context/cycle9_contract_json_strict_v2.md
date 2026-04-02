# Contrato do Ciclo 9 — Supervised Real Write — JSON Strict V2 — DDL-Only

## Veredito
O ciclo 9 é a primeira escrita supervisionada no projeto real. Nesta revisão, a operação autorizada para `R6` fica restrita a DDL-only no arquivo real `router_runtime.sqlite`. Nenhum dado sintético pode ser inserido. A resposta deve ser APENAS JSON válido.

## Regra Absoluta de Formato
Sua resposta COMPLETA deve ser APENAS JSON válido.
- sem texto antes
- sem texto depois
- sem markdown
- sem comentários
- começar com `{`
- terminar com `}`

## Objetivo do ciclo 9A
Criar backup do arquivo-alvo real, aplicar exclusivamente o DDL aprovado para `R6`, registrar before/after auditável, executar validação imediata de existência da tabela e de vazio da tabela, e declarar o resultado.

## Operação autorizada
A única operação autorizada nesta rodada é:
- `CREATE TABLE IF NOT EXISTS cache_observability_windows (...)`
com o schema EXATO aprovado no ciclo 7.

## Operações proibidas
- qualquer INSERT
- qualquer UPDATE
- qualquer DELETE
- qualquer escrita em outra tabela
- qualquer escrita em outro arquivo
- qualquer mudança em produção

## Fontes permitidas
- workspace-integration/output/cycle-008-promotion-decision.json
- workspace-integration/output/cycle-007-sandbox-write-evidence.json
- workspace-integration/output/cycle-006-isolated-write-plan.json
- workspace-integration/context/
- leitura read-only do único arquivo-alvo real
- bridge-monitor
- uma única superfície SQLite genérica por convenção de unicidade, vinculada explicitamente ao alvo ativo da rodada

## Critério de sucesso
- payload JSON válido
- backup_created = true
- backup_path preenchido
- backup criado antes do DDL
- write_result.applied = true
- `cache_observability_windows` existe após a operação
- `SELECT COUNT(*) FROM cache_observability_windows` retorna 0
- zero PII
- nenhuma DML executada

## Critério de bloqueio
- backup_created = false
- qualquer ambiguidade sobre o schema exato
- qualquer INSERT, UPDATE ou DELETE
- qualquer escrita fora do arquivo autorizado
- qualquer modificação em produção
- qualquer texto fora do JSON

## Skeleton obrigatório do objeto raiz
{
  "cycle": 9,
  "mode": "supervised-real-write",
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
    "promotion_decision_confirmed": false,
    "diff_description_used": ""
  },
  "backup_record": {
    "backup_created": false,
    "backup_path": "",
    "backup_created_at": "",
    "backup_size_lines": 0,
    "backup_method": "full_copy"
  },
  "before_state": {
    "component": "",
    "content": "",
    "line_range": "",
    "captured_at": ""
  },
  "write_execution": {
    "write_applied_at": "",
    "apply_method": "ddl_only",
    "lines_affected": 0,
    "target_file_confirmed": ""
  },
  "after_state": {
    "component": "",
    "content": "",
    "line_range": "",
    "captured_at": ""
  },
  "write_result": {
    "applied": false,
    "result_status": "",
    "failure_reason": "",
    "divergence_from_sandbox": null
  },
  "validation_results": [],
  "rollback_record": {
    "rollback_needed": false,
    "rollback_procedure_available": "",
    "rollback_estimated_effort": "",
    "rollback_executed": false,
    "rollback_result": null
  },
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
    "output_file": "output/cycle-009-real-write-evidence.json",
    "backup_path": "",
    "lines_affected": 0,
    "write_applied_at": ""
  }
}

## Regra operacional crítica
Se o backup falhar, interrompa imediatamente.
Se houver qualquer dúvida sobre o schema exato, interrompa imediatamente.
Se houver qualquer DML, a rodada falhou.
Se houver falha após DDL parcial, execute rollback imediato a partir do backup.

## Validação obrigatória pós-DDL
Após a operação, verifique explicitamente:
- `SELECT name FROM sqlite_master WHERE type='table' AND name='cache_observability_windows'`
- `SELECT COUNT(*) FROM cache_observability_windows`
A tabela deve existir e o count deve ser 0.

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
- cycle9_contract_json_strict_v2.md existe
- Invoke-OpenClawSafe.ps1 existe
- launcher seguro continua validado
- embedded/local está pronto
- gateway não será usado
- selected_item = R6
- target_file é o único arquivo autorizado
- diretório de backup fora do projeto real está disponível
- o schema DDL exato aprovado no ciclo 7 está claro e pode ser reproduzido sem ambiguidade
- a operação continua sendo DDL-only

EXECUÇÃO
- usar embedded/local
- usar agent integration
- usar exclusivamente Invoke-OpenClawSafe.ps1
- timeout máximo de 5 minutos
- uma única tentativa apenas

VALIDAÇÃO OBRIGATÓRIA APÓS EXECUÇÃO
- payload retornado
- JSON parseável
- cycle = 9
- mode = supervised-real-write
- selected_item = R6
- backup_created = true
- write_result.applied = true
- nenhum DML executado
- tabela `cache_observability_windows` existe
- count da tabela = 0
- nenhuma PII detectada
- .mcp.json intacto
- bridge intacta
- produção isolada
