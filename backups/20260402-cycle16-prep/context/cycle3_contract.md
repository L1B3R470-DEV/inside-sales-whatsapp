# Contrato do Ciclo 3 — Improvement Analysis — Modelo 0A/0B

## Veredito
O ciclo 3 é o primeiro ciclo orientado a produto, não a infraestrutura. O agent integration deve produzir diagnóstico estruturado e plano priorizado de melhorias do atendente, sempre com evidência rastreável em dados lidos ou em artefatos já aprovados. Nenhuma recomendação pode ser baseada apenas em inferência do contexto injetado.

## Definição do ciclo 3A
Objetivo: produzir diagnóstico estruturado e plano priorizado de melhorias do atendente com base em dados operacionais reais, sem aplicar nenhuma mudança. Cada recomendação deve citar a fonte de evidência que a sustenta.

Fontes permitidas:
- bridge-monitor
  - bridge_status
  - pending_tasks
  - recent_replies
- uma única superfície SQLite genérica por convenção de unicidade, vinculada explicitamente ao alvo ativo da rodada
- arquivos em workspace-integration/context/
- outputs aprovados em workspace-integration/output/
- artefatos consolidados em workspace-integration/cycle3-input/

Output esperado:
- payload JSON válido via resposta do agent
- seção diagnosis por categoria
- array de recommendations estruturadas com evidência
- priorização objetiva
- indicação explícita de validation_required quando necessário

Proibido:
- qualquer PII em qualquer campo
- qualquer patch, diff ou instrução diretamente aplicável no código
- qualquer recomendação sem evidência rastreável
- qualquer recomendação baseada apenas em “conhecimento geral”
- qualquer tool de escrita SQLite
- qualquer escrita em arquivo pelo agent

Critério de sucesso:
- payload JSON válido
- ao menos 4 recomendações
- evidence preenchido de forma rastreável em cada recomendação
- diagnosis preenchido para ao menos 4 das 6 categorias
- nenhum PII detectado
- violations vazio ou contendo apenas auto-reportes legítimos
- recomendações de maior risco marcadas com validation_required = true

Critério de bloqueio:
- qualquer PII
- qualquer recomendação sem evidence válido
- payload com menos de 4 recomendações
- diagnosis ausente ou vazio
- violations não inspecionado
- qualquer patch, diff ou instrução executável no payload

## Definição do ciclo 3B
Objetivo: materializar o relatório de melhoria do ciclo 3 em arquivo persistente e legível, após inspeção completa de PII e qualidade de evidências pelo orquestrador.

Entrada esperada:
- payload JSON aprovado no ciclo 3A

Ação permitida:
- o orquestrador escreve workspace-integration/output/cycle-003-improvement-plan.json com conteúdo idêntico ao payload aprovado
- opcionalmente gerar versão Markdown legível depois, fora desta rodada

Critério de sucesso:
- arquivo existe
- parseável
- idêntico ao payload aprovado
- cada recomendação possui evidência rastreável validada pelo orquestrador

Critério de bloqueio:
- qualquer recomendação sem evidência válida
- qualquer PII
- conteúdo divergente do payload aprovado

## Schema lógico do payload do ciclo 3A
O payload é um único objeto JSON com os seguintes campos obrigatórios:

- cycle = inteiro 3
- mode = string "improvement-analysis"
- agent = string "integration"
- generated_at = string ISO 8601 UTC
- sources_read = array de strings com todas as fontes consultadas
- bridge_state = objeto com:
  - inbox_pending_count
  - outbox_reply_count
  - last_reply_id
  - acks_count
- context_binding = objeto com declaração da convenção SQLite da rodada
- diagnosis = objeto com uma chave por categoria analisada:
  - cache
  - routing
  - fallback
  - guardrails
  - persona
  - crm_coverage
  e cada chave contendo:
  - status
  - summary
  - key_metric
- recommendations = array de objetos com:
  - id
  - category
  - title
  - hypothesis
  - evidence
  - expected_impact
  - implementation_risk
  - validation_required
  - validation_note
  - priority
- improvement_plan = array de strings ordenado pela prioridade
- anomalies = array de objetos com:
  - source
  - description
  - severity
  - suggested_action
- violations = array de strings
- previous_cycle = objeto com:
  - file = "cycle-002-crm-snapshot.json"
  - status = "passed"
- next_steps = array de strings com no máximo 5 itens
- meta = objeto com:
  - workspace
  - context_files_read
  - output_file = "output/cycle-003-improvement-plan.json"
  - recommendations_count

CATEGORIAS DE MELHORIA QUE DEVEM SER ANALISADAS
- cache
- routing
- fallback
- guardrails
- persona
- crm_coverage

FORMATO DAS RECOMENDAÇÕES
- cada recomendação deve ter evidence com fonte e dado concreto
- hypothesis descreve o problema percebido, não a solução
- validation_required deve ser true para mudanças de guardrails, persona ou routing em produção
- priority deve refletir impacto x risco

O QUE NÃO PODE APARECER NO PAYLOAD
- números de telefone
- nomes de leads
- texto bruto de mensagens
- qualquer dado pessoal identificável
- patch de código
- diff
- instrução diretamente executável
- recomendação sem evidência

O QUE DEVE SER PRIORIZADO
- anomalias já observadas com evidência direta
- melhorias de alto impacto e baixo risco
- recomendações sustentadas por múltiplas fontes
- recomendações com impacto mensurável

PRÉ-CHECAGEM OBRIGATÓRIA
Antes da execução, confirme:
- produção continua isolada
- cycle3-input existe
- artifact_index.json existe
- system_scope.json existe
- improvement_targets.json existe
- current_state_summary.json existe
- cycle-000-bridge-only.json existe
- cycle-001-router-read.json existe
- cycle-002-crm-snapshot.json existe
- cycle3_contract.md existe
- embedded/local está pronto
- gateway não será usado

INSTRUÇÃO OPERACIONAL DO CICLO 3A
Você é o agent integration operando no ciclo 3A em modo improvement-analysis.

Tarefa:
- Ler apenas as fontes autorizadas
- Produzir um diagnóstico estruturado do atendente
- Gerar recomendações priorizadas com evidência rastreável
- Não gerar patch, diff ou instrução diretamente aplicável
- Não escrever nenhum arquivo
- Não incluir PII
- Se não houver evidência suficiente para uma recomendação, não a inclua
- Se houver ambiguidade, limitação ou bloqueio legítimo, registrar em violations com precisão

EXECUÇÃO
- usar embedded/local
- usar agent integration
- não usar gateway
- não usar deliver
- não usar bindings
- timeout máximo de 5 minutos
- uma única tentativa apenas

VALIDAÇÃO OBRIGATÓRIA APÓS EXECUÇÃO
- payload foi retornado
- JSON parseável
- cycle = 3
- mode = improvement-analysis
- previous_cycle.status = passed
- diagnosis contém ao menos 4 categorias preenchidas
- recommendations contém ao menos 4 itens
- toda recommendation possui evidence rastreável
- nenhuma recommendation contém patch/diff/instrução diretamente aplicável
- nenhuma PII detectada
- .mcp.json segue intacto
- bridge segue intacta
- produção segue isolada

PROIBIDO
- Não executar o ciclo 3B
- Não materializar output/cycle-003-improvement-plan.json nesta rodada
- Não gerar patch
- Não aplicar mudança
- Não tocar em C:\AUTOMACAO\cowork\
- Não tocar em produção
- Não alterar gateway
- Não criar bindings ao workspace real
- Não fazer segunda tentativa nesta mesma rodada
