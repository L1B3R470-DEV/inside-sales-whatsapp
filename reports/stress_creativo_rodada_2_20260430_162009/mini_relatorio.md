# Mini relatorio - Stress criativo rodada 2

## Objetivo

Avaliar a capacidade criativa/comercial do atendente WhatsApp B2B da Classe em perguntas nao-triagem, usando material real de aprendizado e novas informacoes comerciais criticas.

## Material consultado

- C:\AUTOMACAO\rag\knowledge
-
outer_runtime.sqlite: tabelas
ag_documents,
ag_chunks,
esponse_cache,
oute_logs
- crm_operacional.sqlite: tabelas knowledge_rules, knowledge_documents, knowledge_cycles
- Documentos RAG: book extraido, ranking comercial, ranking por categoria, scripts de revenda, direcionamento PF, pedidos sugeridos R$ 2.000/R$ 4.000/R$ 6.000 e novos documentos comerciais da rodada.
- Relatorio anterior: stress-test-runs\creative_capacity_after_fix_20260428_193204 e saneamentos posteriores.

## Execucao

- Endpoint real usado: POST http://localhost:8091/route
- Numeros sinteticos isolados usados para nao contaminar leads reais.
- Total de perguntas: 40
- LLM observado nas respostas: llmProvider=anthropic, rota predominante
ag_claude.

## Resultado inicial

- SATISFATORIA: 26
- PARCIALMENTE_UTIL: 3
- FRACA: 5
- INSATISFATORIA: 6

## Melhorias feitas

- Conhecimento comercial critico inserido no RAG ativo.
- Prompt SDR reforcado para SAC, pagamento, prazo, suporte, nota cheia, B2B e markup.
- Router ajustado para recuperar documentos comerciais criticos por gatilho e secao.
- Snippet RAG ajustado para nao perder kits, PV/PVL e secoes comerciais especificas.
- Retestes executados nos casos insuficientes.

## Resultado final

- SATISFATORIA: 40
- Total: 40
- Nenhuma resposta final classificada como PARCIALMENTE_UTIL, FRACA, INSATISFATORIA, RISCO_COMERCIAL ou NAO_RESPONDEU.

## Pontos fortes

- O atendente recuperou corretamente as novas regras de SAC, pagamento, prazo, nota fiscal e markup.
- O uso de Claude/Anthropic no fluxo
ag_claude ficou consistente.
- O RAG passou a responder melhor perguntas curtas que antes poderiam cair em resposta generica.

## Riscos remanescentes

- O documento antigo SOBRE A MARCA - CLASSE COURO.docx e alguns scripts antigos ainda contêm termos legados. O sanitizador impede saida direta, mas o ideal e higienizar a origem em rodada propria.
- Existe SyntaxWarning antigo em
outer_service.py sobre regex SQL \D; nao bloqueia runtime, mas deve ser corrigido em manutencao tecnica.
- A avaliacao foi feita pelo caminho router /route, nao por inbound real Evolution->n8n->router->Evolution.

## Conclusao

Com as correcoes aplicadas e retestadas, o atendente ficou pronto para responder a rodada criativa/comercial proposta no escopo do router, com 40/40 respostas satisfatorias apos saneamento.
