# Contrato do Ciclo 9 — Supervised Real Write — JSON Strict — Modelo 0A/0B

## Veredito
O ciclo 9 é a primeira escrita supervisionada no projeto real. A escrita é restrita a um único item (`R6`), um único arquivo real, com backup obrigatório imediato antes de qualquer modificação. A resposta deve ser APENAS JSON válido.

## Regra Absoluta de Formato
Sua resposta COMPLETA deve ser APENAS JSON válido.
- sem texto antes
- sem texto depois
- sem markdown
- sem comentários
- começar com `{`
- terminar com `}`

## Objetivo do ciclo 9A
Criar backup do arquivo-alvo real, aplicar exclusivamente a mudança aprovada para `R6`, registrar before/after auditável, executar validação imediata e declarar o resultado.

## Fontes permitidas
- workspace-integration/output/cycle-008-promotion-decision.json
- workspace-integration/output/cycle-007-sandbox-write-evidence.json
- workspace-integration/output/cycle-006-isolated-write-plan.json
- workspace-integration/context/
- leitura read-only do único arquivo-alvo real
- bridge-monitor
- uma única superfície SQLite genérica por convenção de unicidade, vinculada explicitamente ao alvo ativo da rodada

## Proibido
- qualquer escrita antes do backup
- escrita em mais de um arquivo real
- escrita fora do target_file aprovado
- qualquer mudança em produção
- qualquer conteúdo com PII
- processar qualquer item além de `R6`

## Critério de sucesso
- payload JSON válido
- backup_created = true
- backup_path preenchido e fora de produção
- before_state e after_state preenchidos
- before_state.content diferente de after_state.content
- write_result.applied = true
- validation_results preenchidos
- zero PII

## Critério de bloqueio
- backup_created = false
- qualquer ambiguidade técnica para escrever com segurança no arquivo `.sqlite`
- before_state.content idêntico a after_state.content
- escrita fora do target_file
- qualquer evidência de modificação em produção
- mais de um arquivo modificado
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
    "change_type": "",
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
    "apply_method": "",
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
Se houver ambiguidade para aplicar com segurança no arquivo `.sqlite`, interrompa imediatamente.
Se houver qualquer escrita fora do arquivo autorizado, declare falha crítica.
Se houver falha após escrita parcial, execute rollback imediato a partir do backup.

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
- cycle9_contract_json_strict.md existe
- Invoke-OpenClawSafe.ps1 existe
- launcher seguro continua validado
- embedded/local está pronto
- gateway não será usado
- selected_item = R6
- target_file é o único arquivo autorizado
- diretório de backup fora do projeto real está disponível
- a mudança é tecnicamente determinística e segura para o arquivo `.sqlite`; se não for, interromper antes de escrever

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
- before_state preenchido
- after_state preenchido
- before_state diferente de after_state
- write_result.applied = true ou bloqueio formal antes da escrita
- nenhuma PII detectada
- .mcp.json intacto
- bridge intacta
- produção isolada
