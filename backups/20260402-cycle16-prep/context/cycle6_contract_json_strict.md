# Contrato do Ciclo 6 — Isolated Write Planning — JSON Strict — Modelo 0A/0B

## Veredito
O ciclo 6 é o primeiro ciclo com intenção de escrita, mas ainda não escreve. Ele toma o primeiro item `ready` do ciclo 5, lê o arquivo-alvo real em modo estritamente read-only, descreve o estado atual com precisão e produz um plano de escrita isolada completo: espelhamento do arquivo em sandbox, diff descritivo, pré-condições verificadas ao vivo, critérios de validação pós-escrita e procedimento de rollback específico ao arquivo. O agent não aplica nada. A resposta deve ser APENAS JSON válido.

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

## Objetivo do ciclo 6A
Selecionar o primeiro item com `readiness_level = ready` e `application_order = 1` do `cycle-005-write-proposals.json`, ler o arquivo-alvo real em modo estritamente read-only, verificar as pré-condições ao vivo e produzir um plano de escrita isolada completo com espelhamento de sandbox, descrição precisa do estado atual, descrição precisa do estado proposto, diff descritivo não executável, critérios de validação pós-escrita e procedimento de rollback específico, sem aplicar nada.

## Fontes permitidas
- workspace-integration/output/cycle-005-write-proposals.json
- workspace-integration/output/cycle-004-execution-plan.json
- workspace-integration/output/cycle-003-improvement-plan.json
- workspace-integration/cycle6-input/first_write_candidate.json
- workspace-integration/cycle6-input/isolated_write_scope.json
- workspace-integration/cycle6-input/validation_and_rollback.json
- workspace-integration/cycle6-input/artifact_index.json
- workspace-integration/context/
- bridge-monitor
- uma única superfície SQLite genérica por convenção de unicidade, vinculada explicitamente ao alvo ativo da rodada
- leitura read-only do único arquivo-alvo real declarado em `write_scope.target_file` do item selecionado

## Proibido
- qualquer write_query, create_table ou append_insight em qualquer MCP
- qualquer file write pelo agent
- qualquer escrita no projeto real
- leitura de mais de um arquivo-alvo real neste ciclo
- qualquer diff em formato executável
- qualquer patch
- qualquer bloco de código pronto para aplicar
- qualquer conteúdo com PII
- processar itens com `application_order > 1`

## Critério de sucesso
- payload JSON válido e parseável
- exatamente 1 item em `write_plan`
- `selected_item` corresponde ao item `application_order = 1` do ciclo 5
- `current_state_observed` preenchido com base na leitura real do arquivo
- todas as pré-condições reavaliadas com `verified` e `verification_source`
- `sandbox_plan.mirror_path` especificado fora do projeto real
- `write_readiness` declarado
- `rollback_plan.procedure` específico ao arquivo lido
- `violations` vazio ou contendo apenas auto-relatos legítimos
- zero PII

## Critério de bloqueio
- qualquer PII
- arquivo-alvo não encontrado no projeto real
- qualquer pré-condição com `verified = false` e `blocking = true`
- `current_state_observed` ausente
- diff executável em qualquer campo
- mais de 1 item em `write_plan`
- qualquer texto fora do objeto JSON

## Skeleton obrigatório do objeto raiz
Use EXATAMENTE esta estrutura de topo e esta ordem de campos.
O skeleton abaixo define a ESTRUTURA, não os valores.

{
  "cycle": 6,
  "mode": "isolated-write-planning",
  "agent": "integration",
  "generated_at": "ISO-8601-UTC",
  "input_cycle": 5,
  "input_file": "cycle-005-write-proposals.json",
  "selected_item": "",
  "sources_read": [],
  "context_binding": {
    "sqlite_generic_bound_to": "",
    "sqlite_router_absent": true,
    "crm_live_not_consulted": true,
    "binding_note": ""
  },
  "target_summary": {
    "rec_id": "",
    "target_file": "",
    "target_component": "",
    "change_type": "",
    "file_found": false,
    "file_size_lines": 0
  },
  "write_plan": [],
  "pre_condition_check": [],
  "write_readiness": "",
  "write_readiness_reason": "",
  "anomalies": [],
  "violations": [],
  "previous_cycle": {
    "file": "cycle-005-write-proposals.json",
    "status": "approved"
  },
  "next_steps": [],
  "meta": {
    "workspace": "",
    "context_files_read": [],
    "output_file": "output/cycle-006-isolated-write-plan.json",
    "target_file_lines_read": 0
  }
}

## Regras de write_plan
`write_plan` deve conter EXATAMENTE 1 objeto com:
- rec_id
- title
- category
- current_state_observed
- proposed_state
- change_summary
- estimated_scope
- diff_description
- sandbox_plan
- validation_plan
- rollback_plan
- application_order

## Regras de sandbox_plan
`sandbox_plan` deve conter:
- mirror_path
- mirror_strategy
- isolation_confirmed

Regras:
- `mirror_path` deve ser caminho absoluto fora do projeto real
- `isolation_confirmed` deve ser `false` neste ciclo

## Regras de pre_condition_check
Cada item deve conter:
- condition
- verified
- verification_source
- blocking
- notes

## Regras de conteúdo
- `current_state_observed` deve ser explicitamente baseado na leitura real do arquivo neste ciclo
- `diff_description` deve ser descrição em linguagem natural, nunca diff executável
- processar exatamente 1 item neste ciclo
- `write_readiness` só pode ser:
  - approved
  - pending
  - blocked

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
- cycle6-input existe
- artifact_index.json existe
- first_write_candidate.json existe
- isolated_write_scope.json existe
- validation_and_rollback.json existe
- cycle-005-write-proposals.json existe
- cycle-004-execution-plan.json existe
- cycle-003-improvement-plan.json existe
- cycle6_contract_json_strict.md existe
- Invoke-OpenClawSafe.ps1 existe
- o launcher seguro continua validado
- embedded/local está pronto
- gateway não será usado
- o item selecionado é `application_order = 1`
- o arquivo-alvo real do item selecionado foi resolvido para leitura read-only

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
- cycle = 6
- mode = isolated-write-planning
- input_cycle = 5
- input_file = cycle-005-write-proposals.json
- selected_item corresponde ao item correto
- exatamente 1 item em write_plan
- arquivo-alvo foi encontrado e lido
- current_state_observed reflete releitura real
- file_size_lines > 0
- sandbox_plan.mirror_path está fora do projeto real
- sandbox_plan.isolation_confirmed = false
- write_readiness foi declarado
- nenhuma entrada contém patch/diff executável
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
- cycle6-input presente: [sim/não]
- artifact_index.json presente: [sim/não]
- first_write_candidate.json presente: [sim/não]
- isolated_write_scope.json presente: [sim/não]
- validation_and_rollback.json presente: [sim/não]
- ciclos 3/4/5 presentes: [sim/não]
- contrato JSON strict criado: [sim/não]
- launcher seguro presente: [sim/não]
- launcher seguro utilizado: [sim/não]
- embedded/local pronto: [sim/não]
- gateway não utilizado: [sim/não]
- item selecionado resolvido: [sim/não]
- arquivo-alvo real legível em read-only: [sim/não]

EXECUÇÃO
- ciclo 6A executado: [sim/não]
- timeout acionado: [sim/não]
- caminho usado: [embedded/local]
- observações:

PAYLOAD
- payload retornado: [sim/não]
- JSON parseável: [sim/não]
- cycle = 6: [sim/não]
- mode = isolated-write-planning: [sim/não]
- input_cycle = 5: [sim/não]
- selected_item correto: [sim/não]
- exatamente 1 item em write_plan: [sim/não]
- target_summary.file_found = true: [sim/não]
- current_state_observed baseado em leitura real: [sim/não/parcial]
- file_size_lines > 0: [sim/não]
- sandbox fora do projeto real: [sim/não]
- write_readiness declarado: [sim/não]
- texto fora do JSON detectado: [sim/não]
- violations vazio ou apenas auto-reporte legítimo: [sim/não/parcial]

INSPEÇÃO DE QUALIDADE
- plano sem patch/diff executável: [sim/não]
- nenhuma PII detectada: [sim/não]
- pré-condições verificadas coerentemente: [sim/não/parcial]
- validação e rollback coerentes: [sim/não/parcial]
- observações:

ISOLAMENTO PRESERVADO
- .mcp.json do projeto permaneceu intocado: [sim/não]
- bridge local permaneceu intocada: [sim/não]
- produção continua isolada após execução: [sim/não]
- nenhum vínculo ao workspace real foi criado: [sim/não]
- nenhum arquivo real foi escrito: [sim/não]

CONCLUSÃO
- ciclo 6A aprovado: [sim/não/condicional]
- maior risco observado:
- pronto para discutir ciclo 6B: [sim/não]
- próximo passo sugerido:

ARTEFATOS
- relatório salvo em:
- payload/log fonte:
- launcher usado:
- contrato criado:
- configs alteradas nesta rodada:

FIM DO RELATÓRIO
