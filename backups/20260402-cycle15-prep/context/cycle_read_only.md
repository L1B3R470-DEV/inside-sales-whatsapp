# Ciclo READ-ONLY - Definição Operacional

Duração: 1 ciclo completo de polling do agent integration
Escopo: somente leitura dos seguintes recursos

## Fontes permitidas:
- Arquivos desta pasta de contexto (workspace-integration/context/)
- MCP server sqlite -> tabelas: leads, interactions, knowledge_rules
- MCP server sqlite-router -> tabelas: response_cache, route_logs
- MCP server bridge-monitor -> bridge_status, pending_tasks, recent_replies
- MCP server fetch -> URLs previamente aprovadas apenas

## Ações permitidas:
- Ler, listar, contar, resumir
- Gerar relatório de diagnóstico como texto
- Identificar anomalias e reportar

## Ações proibidas:
- Qualquer escrita em disco (fora do workspace isolado)
- Qualquer chamada POST/PUT/DELETE a APIs
- Qualquer modificação de estado da bridge
- Qualquer acesso ao filesystem do projeto real

## Output esperado:
- Um único arquivo JSON em workspace-integration/output/
- Schema: { "cycle": 1, "mode": "read-only", "findings": [...],
             "anomalies": [...], "next_steps": [...] }