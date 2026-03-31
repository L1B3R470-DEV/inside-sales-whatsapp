Analise os logs recentes da stack buscando erros e anomalias:

1. **Docker logs** — rode `docker logs --tail 100 evolution` e `docker logs --tail 100 n8n` procurando erros
2. **Router logs** — verifique `C:\AUTOMACAO\logs\` por logs recentes do router_service
3. **n8n executions** — se possível, cheque execuções recentes com erro via API n8n

Para cada erro encontrado:
- Mostre timestamp, componente e mensagem
- Classifique a severidade (crítico / warning / info)
- Sugira ação corretiva quando aplicável

Se não houver erros, confirme que a stack está saudável.
Foque nos últimos 30 minutos por padrão, a menos que o usuário peça outro período.
