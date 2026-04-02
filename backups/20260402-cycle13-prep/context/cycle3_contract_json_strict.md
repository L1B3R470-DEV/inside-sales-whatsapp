# Contrato do Ciclo 3 — Improvement Analysis — JSON Strict — Modelo 0A/0B

## Veredito
O objetivo analítico do ciclo 3 permanece o mesmo. Esta revisão existe apenas para estabilizar o formato de saída. A resposta do agent deve ser APENAS um objeto JSON válido, sem markdown, sem bloco de código, sem texto introdutório e sem texto final.

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
- `diagnosis` deve ser fechado completamente antes de abrir `recommendations`
- `recommendations`, `improvement_plan`, `anomalies`, `violations`, `previous_cycle`, `next_steps` e `meta` são campos de primeiro nível do objeto raiz
- se você não conseguir preencher algum campo sem inventar dados, preencha com valor estrutural válido e registre a limitação em `violations`

## Objetivo do ciclo 3A
Produzir diagnóstico estruturado e plano priorizado de melhorias do atendente com base em dados operacionais reais, sem aplicar nenhuma mudança. Cada recomendação deve citar a fonte de evidência que a sustenta.

## Fontes permitidas
- bridge-monitor
  - bridge_status
  - pending_tasks
  - recent_replies
- uma única superfície SQLite genérica por convenção de unicidade, vinculada explicitamente ao alvo ativo da rodada
- arquivos em workspace-integration/context/
- outputs aprovados em workspace-integration/output/
- artefatos consolidados em workspace-integration/cycle3-input/

## Proibido
- qualquer PII em qualquer campo
- qualquer patch, diff ou instrução diretamente aplicável no código
- qualquer recomendação sem evidência rastreável
- qualquer recomendação baseada apenas em “conhecimento geral”
- qualquer tool de escrita SQLite
- qualquer escrita em arquivo pelo agent

## Critério de sucesso
- payload JSON válido
- ao menos 4 recomendações
- evidence preenchido de forma rastreável em cada recomendação
- diagnosis preenchido para ao menos 4 das 6 categorias
- nenhum PII detectado
- violations vazio ou contendo apenas auto-reportes legítimos
- recomendações de maior risco marcadas com validation_required = true

## Critério de bloqueio
- qualquer PII
- qualquer recomendação sem evidence válido
- payload com menos de 4 recomendações
- diagnosis ausente ou vazio
- violations não inspecionado
- qualquer patch, diff ou instrução executável no payload
- qualquer texto fora do objeto JSON
- qualquer campo estrutural de topo aninhado incorretamente dentro de `diagnosis`

## Template rígido obrigatório do objeto raiz
Use EXATAMENTE esta estrutura de topo e esta ordem de campos:

{
  "cycle": 3,
  "mode": "improvement-analysis",
  "agent": "integration",
  "generated_at": "ISO-8601-UTC",
  "sources_read": [],
  "bridge_state": {
    "inbox_pending_count": 0,
    "outbox_reply_count": 0,
    "last_reply_id": "",
    "acks_count": 0
  },
  "context_binding": {
    "sqlite_generic_bound_to": "",
    "sqlite_router_absent": true,
    "crm_live_not_consulted": true,
    "binding_note": ""
  },
  "diagnosis": {
    "cache": {
      "status": "",
      "summary": "",
      "key_metric": ""
    },
    "routing": {
      "status": "",
      "summary": "",
      "key_metric": ""
    },
    "fallback": {
      "status": "",
      "summary": "",
      "key_metric": ""
    },
    "guardrails": {
      "status": "",
      "summary": "",
      "key_metric": ""
    },
    "persona": {
      "status": "",
      "summary": "",
      "key_metric": ""
    },
    "crm_coverage": {
      "status": "",
      "summary": "",
      "key_metric": ""
    }
  },
  "recommendations": [],
  "improvement_plan": [],
  "anomalies": [],
  "violations": [],
  "previous_cycle": {
    "file": "cycle-002-crm-snapshot.json",
    "status": "passed"
  },
  "next_steps": [],
  "meta": {
    "workspace": "",
    "context_files_read": [],
    "output_file": "output/cycle-003-improvement-plan.json",
    "recommendations_count": 0
  }
}

## Regras das recomendações
Cada item de `recommendations` deve ser um objeto com:
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

## Categorias obrigatórias de diagnosis
- cache
- routing
- fallback
- guardrails
- persona
- crm_coverage

## Instrução operacional final
Sua resposta COMPLETA deve ser APENAS o objeto JSON final.
Sem texto antes.
Sem texto depois.
Sem markdown.
Sem bloco de código.
Comece com `{` e termine com `}`.
