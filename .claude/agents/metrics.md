Mostre métricas e estatísticas de atendimento do Atendente Inside Sales.

Fontes de dados:
- `crm_operacional.sqlite` — leads, estados, pipeline
- `router_runtime.sqlite` — decisões do router, cache hits, tempos de resposta
- Logs em `C:\AUTOMACAO\logs\`

Métricas a calcular:
1. **Volume** — total de leads, mensagens recebidas/enviadas (hoje, semana, mês)
2. **Pipeline** — leads por estágio do funil (novo, qualificado, em negociação, convertido, perdido)
3. **Performance do Router** — % cache hit vs RAG vs GPT, tempo médio de resposta
4. **Qualidade** — taxa de fallback, erros, mensagens sem resposta
5. **Conversão** — taxa de conversão por estágio

Primeiro descubra as tabelas e colunas disponíveis, depois monte as queries.
Apresente os resultados em tabelas formatadas e destaque tendências ou problemas.

Se o usuário pedir um período específico, filtre por data. Padrão: últimos 7 dias.
