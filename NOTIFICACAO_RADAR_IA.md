# Radar IA Codex - melhorias encontradas

Execucao: 2026-05-04T19:05:25-03:00
Projeto: `C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES`
Maquina: PC CLS (`100.113.13.27`)

Novidades relevantes encontradas: 9
Melhorias aplicaveis ao stack: 11

Relatorio completo: `C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES\ANALISES\RADAR_IA_CODEX.md`

## Top 3 recomendacoes

1. Testar upgrade n8n em laboratorio antes de producao.
   Motivo: local esta em `2.11.3`; upstream atual traz MCP mais maduro, redacao e protecao SSRF disponivel desde `2.12.0`.

2. Testar Evolution v2.3.7 em staging e criar alerta de decriptacao.
   Motivo: local reporta `2.2.3` e logs recentes mostram `SessionError`, `Bad MAC`, decrypt failed e timeout Baileys.

3. Criar benchmark Qdrant hybrid em colecao paralela.
   Motivo: RAG atual tem baixa superficie ativa e ainda depende de BM25 local custom no router.

Acao humana necessaria: sim - aprovar janela/branch para backup, laboratorio n8n/Evolution e testes RAG/Responses.

Classificacao: `novas melhorias relevantes encontradas`
