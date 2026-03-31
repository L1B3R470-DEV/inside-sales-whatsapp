Verifique a saúde completa da stack do Atendente Inside Sales:

1. **Docker containers** — rode `docker ps` e confirme que estão UP: n8n (5678), evolution (8080), evolution-redis (6379), evolution-postgres (5432)
2. **Router Service** — verifique se `router_service.py` está rodando na porta 8091 (`curl http://localhost:8091/health` ou cheque o processo)
3. **n8n** — acesse `http://localhost:5678/healthz` e confirme que está respondendo
4. **Evolution API** — acesse `http://localhost:8080/` e confirme resposta
5. **Bancos SQLite** — confirme que `crm_operacional.sqlite` e `router_runtime.sqlite` existem e não estão corrompidos (tente um `SELECT 1` via sqlite3)

Apresente um resumo em tabela com: componente | status | porta | observações.
Se algo estiver fora, sugira o comando exato para corrigir.
