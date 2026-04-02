# Contrato do Ciclo 7 — Sandbox Write — JSON Strict — Modelo 0A/0B

## Veredito
O ciclo 7 é o primeiro ciclo com escrita real, mas estritamente restrita ao arquivo espelhado na sandbox. O agent lê o plano aprovado do ciclo 6, relê o arquivo-alvo real em modo read-only, cria o espelho na sandbox, aplica a mudança aprovada exclusivamente no espelho, registra before/after auditável e valida o resultado localmente. O projeto real não é tocado em nenhuma etapa. A resposta deve ser APENAS JSON válido.

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

## Objetivo do ciclo 7A
Criar o arquivo espelho do item aprovado no ciclo 6 dentro da sandbox, aplicar exclusivamente a mudança descrita em `diff_description` do ciclo 6 sobre o espelho, registrar estados before/after auditáveis e executar os `test_steps` de validação local, sem tocar no projeto real.

## Fontes permitidas
- workspace-integration/output/cycle-006-isolated-write-plan.json
- workspace-integration/output/cycle-005-write-proposals.json
- workspace-integration/output/cycle-004-execution-plan.json
- workspace-integration/cycle7-input/selected_sandbox_write.json
- workspace-integration/cycle7-input/sandbox_manifest.json
- workspace-integration/cycle7-input/write_guardrails.json
- workspace-integration/cycle7-input/validation_checkpoint.json
- workspace-integration/cycle7-input/artifact_index.json
- workspace-integration/context/
- bridge-monitor
- uma única superfície SQLite genérica por convenção de unicidade, vinculada explicitamente ao alvo ativo da rodada
- leitura read-only do único arquivo-alvo real declarado no ciclo 6
- escrita SOMENTE no arquivo espelhado dentro de workspace-integration/sandbox/

## Proibido
- qualquer escrita fora de `workspace-integration/sandbox/`
- qualquer escrita no projeto real
- qualquer write_query, create_table ou append_insight em qualquer MCP
- modificação de qualquer arquivo fora da sandbox
- processamento de mais de um item
- qualquer conteúdo com PII
- aplicar mudança diferente da descrita em `diff_description` do ciclo 6
- criar arquivos fora do diretório `workspace-integration/sandbox/`

## Critério de sucesso
- payload JSON válido
- `sandbox_write_result.applied = true`
- `before_state` preenchido com conteúdo real antes da escrita
- `after_state` preenchido com conteúdo real após a escrita no espelho
- `before_state` e `after_state` distinguíveis
- `validation_results` com resultado objetivo de cada `test_step`
- `real_file_untouched = true`
- `violations` vazio ou contendo apenas auto-relatos legítimos
- zero PII

## Critério de bloqueio
- qualquer PII
- `sandbox_write_result.applied = false` sem diagnóstico claro
- `before_state` ausente ou idêntico a `after_state`
- evidência de escrita fora de `sandbox_plan.mirror_path`
- `real_file_untouched` ausente ou false
- mais de um item processado
- mudança aplicada diferente da descrita em `diff_description` do ciclo 6
- qualquer texto fora do objeto JSON

## Skeleton obrigatório do objeto raiz
Use EXATAMENTE esta estrutura de topo e esta ordem de campos.
O skeleton abaixo define a ESTRUTURA, não os valores.

{
  "cycle": 7,
  "mode": "sandbox-write",
  "agent": "integration",
  "generated_at": "ISO-8601-UTC",
  "input_cycle": 6,
  "input_file": "cycle-006-isolated-write-plan.json",
  "selected_item": "",
  "sources_read": [],
  "context_binding": {
    "sqlite_generic_bound_to": "",
    "sqlite_router_absent": true,
    "crm_live_not_consulted": true,
    "binding_note": ""
  },
  "sandbox_execution": {
    "mirror_path_used": "",
    "mirror_created": false,
    "mirror_creation_source": "",
    "change_applied": false,
    "change_description_used": ""
  },
  "sandbox_write_result": {
    "applied": false,
    "apply_method": "",
    "lines_affected": 0,
    "result_status": "",
    "failure_reason": ""
  },
  "before_state": {
    "component": "",
    "content": "",
    "line_range": ""
  },
  "after_state": {
    "component": "",
    "content": "",
    "line_range": ""
  },
  "validation_results": [],
  "real_file_untouched": true,
  "rollback_status": {
    "sandbox_rollback_available": false,
    "real_file_rollback_needed": false,
    "rollback_procedure": ""
  },
  "anomalies": [],
  "violations": [],
  "previous_cycle": {
    "file": "cycle-006-isolated-write-plan.json",
    "status": "approved"
  },
  "next_steps": [],
  "meta": {
    "workspace": "",
    "context_files_read": [],
    "output_file": "output/cycle-007-sandbox-write-evidence.json",
    "sandbox_path": "",
    "lines_affected": 0
  }
}

## Regras de sandbox_execution
Deve conter:
- mirror_path_used
- mirror_created
- mirror_creation_source
- change_applied
- change_description_used

Regras:
- `mirror_path_used` deve coincidir com o caminho planejado do ciclo 6
- `mirror_created` deve refletir criação real do espelho
- `change_description_used` deve usar o texto da mudança autorizada no ciclo 6

## Regras de sandbox_write_result
Deve conter:
- applied
- apply_method
- lines_affected
- result_status
- failure_reason

## Regras de before_state e after_state
- `before_state.content` deve ser capturado do espelho imediatamente após a cópia e antes da modificação
- `after_state.content` deve ser capturado do espelho imediatamente após a modificação
- ambos devem ser livres de PII
- ambos devem refletir o mesmo componente

## Regras de validation_results
Cada item deve conter:
- step
- method
- result
- observation
- notes

## Regras de rollback_status
Deve conter:
- sandbox_rollback_available
- real_file_rollback_needed
- rollback_procedure

Regras:
- `real_file_rollback_needed` deve ser sempre `false`
- o rollback deve se referir somente ao sandbox

## Restrições de conteúdo
- não usar diff executável
- não usar patch
- não usar bloco de código pronto para aplicar
- processar exatamente 1 item
- `real_file_untouched` deve ser `true`

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
- cycle7-input existe
- artifact_index.json existe
- selected_sandbox_write.json existe
- sandbox_manifest.json existe
- write_guardrails.json existe
- validation_checkpoint.json existe
- cycle-006-isolated-write-plan.json existe
- cycle-005-write-proposals.json existe
- cycle-004-execution-plan.json existe
- cycle7_contract_json_strict.md existe
- Invoke-OpenClawSafe.ps1 existe
- o launcher seguro continua validado
- embedded/local está pronto
- gateway não será usado
- o item selecionado continua sendo o único item autorizado
- o caminho de sandbox está fora do projeto real

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
- cycle = 7
- mode = sandbox-write
- input_cycle = 6
- selected_item correto
- mirror_created = true
- sandbox_write_result.applied = true
- before_state e after_state estão preenchidos
- before_state e after_state são diferentes
- real_file_untouched = true
- nenhuma entrada contém patch/diff executável
- nenhuma PII detectada
- não existe texto fora do objeto JSON
- .mcp.json segue intacto
- bridge segue intacta
- produção segue isolada
- nenhum arquivo real foi escrito

FORMATO OBRIGATÓRIO DA RESPOSTA

INÍCIO DO RELATÓRIO

STATUS GERAL
- concluído: [sim/não/parcial]
- risco operacional atual: [baixo/médio/alto]

PRÉ-EXECUÇÃO
- produção continua isolada: [sim/não]
- cycle7-input presente: [sim/não]
- artifact_index.json presente: [sim/não]
- selected_sandbox_write.json presente: [sim/não]
- sandbox_manifest.json presente: [sim/não]
- write_guardrails.json presente: [sim/não]
- validation_checkpoint.json presente: [sim/não]
- ciclos 4/5/6 presentes: [sim/não]
- contrato JSON strict criado: [sim/não]
- launcher seguro presente: [sim/não]
- launcher seguro utilizado: [sim/não]
- embedded/local pronto: [sim/não]
- gateway não utilizado: [sim/não]
- item selecionado resolvido: [sim/não]
- sandbox path fora do projeto real: [sim/não]

EXECUÇÃO
- ciclo 7A executado: [sim/não]
- timeout acionado: [sim/não]
- caminho usado: [embedded/local]
- observações:

PAYLOAD
- payload retornado: [sim/não]
- JSON parseável: [sim/não]
- cycle = 7: [sim/não]
- mode = sandbox-write: [sim/não]
- input_cycle = 6: [sim/não]
- selected_item correto: [sim/não]
- mirror_created = true: [sim/não]
- sandbox_write_result.applied = true: [sim/não]
- before_state preenchido: [sim/não]
- after_state preenchido: [sim/não]
- before_state diferente de after_state: [sim/não]
- real_file_untouched = true: [sim/não]
- texto fora do JSON detectado: [sim/não]
- violations vazio ou apenas auto-reporte legítimo: [sim/não/parcial]

INSPEÇÃO DE QUALIDADE
- escrita restrita à sandbox: [sim/não]
- plano sem patch/diff executável: [sim/não]
- nenhuma PII detectada: [sim/não]
- validação local coerente: [sim/não/parcial]
- rollback local coerente: [sim/não/parcial]
- observações:

ISOLAMENTO PRESERVADO
- .mcp.json do projeto permaneceu intocado: [sim/não]
- bridge local permaneceu intocada: [sim/não]
- produção continua isolada após execução: [sim/não]
- nenhum vínculo ao workspace real foi criado: [sim/não]
- nenhum arquivo real foi escrito: [sim/não]

CONCLUSÃO
- ciclo 7A aprovado: [sim/não/condicional]
- maior risco observado:
- pronto para discutir ciclo 7B: [sim/não]
- próximo passo sugerido:

ARTEFATOS
- relatório salvo em:
- payload/log fonte:
- launcher usado:
- contrato criado:
- configs alteradas nesta rodada:

FIM DO RELATÓRIO
