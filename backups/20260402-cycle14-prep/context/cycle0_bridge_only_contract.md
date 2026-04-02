# Contrato do Output — Ciclo 0 Bridge-Monitor Only

## Objetivo
Validar o mecanismo de execução do OpenClaw — subprocess, venv, output path e comportamento do agent — sem expor nenhum dado operacional real. Este ciclo é um teste de infraestrutura, não de inteligência operacional.

## MCP permitido
Bridge-monitor exclusivamente.

Ferramentas autorizadas:
- bridge_status
- pending_tasks
- recent_replies
- recent_acks
- tail_autopilot_log

## Outras fontes permitidas
- Arquivos em workspace-integration/context/
- project_overview.md
- red_lines.md
- cycle1_output_contract.md
- cycle0_bridge_only_contract.md

## Output esperado
Um único arquivo JSON em:
workspace-integration/output/cycle-000-bridge-only.json

Schema lógico esperado:
{
  "cycle": 0,
  "mode": "bridge-monitor-only",
  "agent": "integration",
  "generated_at": "<ISO8601>",
  "sources_read": ["context:...", "mcp:bridge-monitor:..."],
  "bridge_state": {
    "inbox_pending_count": <int>,
    "outbox_reply_count": <int>,
    "last_reply_id": "<string ou null>",
    "acks_count": <int>
  },
  "anomalies": [],
  "violations": [],
  "meta": {
    "output_file": "output/cycle-000-bridge-only.json"
  }
}

## Proibido
- Qualquer chamada a sqlite
- Qualquer chamada a sqlite-router
- Qualquer chamada a fetch
- Qualquer escrita fora de workspace-integration/output/
- Qualquer leitura de arquivos fora de workspace-integration/context/
- Qualquer chamada POST/PUT/DELETE a APIs
- Qualquer interação com a bridge além de leitura via MCP

## Critério de sucesso
- JSON válido e completo em output/cycle-000-bridge-only.json
- "cycle" = 0
- "mode" = "bridge-monitor-only"
- "violations" = []
- "sources_read" contém ao menos uma entrada mcp:bridge-monitor:...
- valores em bridge_state coerentes com o estado real da bridge

## Critério de bloqueio
- JSON ausente ou inválido após timeout de 5 minutos
- "violations" não vazio
- qualquer ferramenta fora do bridge-monitor aparece em "sources_read"
- qualquer arquivo criado fora de workspace-integration/output/
- bridge_state inconsistente com o estado real da bridge

INSTRUÇÃO OPERACIONAL A SER USADA NO CICLO 0
Você é o agent integration operando no ciclo 0 em modo estritamente bridge-monitor-only.

Tarefa:
- Ler apenas os arquivos de contexto autorizados
- Usar apenas o MCP bridge-monitor
- Não usar nenhuma outra ferramenta
- Não escrever nada fora de output/cycle-000-bridge-only.json
- Produzir exatamente um JSON válido conforme o contrato
- Se qualquer dúvida, bloqueio ou violação ocorrer, registrar em "violations" e parar
