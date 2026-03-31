Investigue o estado e histórico de um lead/número específico no sistema.

O usuário vai fornecer um número de telefone ou nome. Faça:

1. **CRM** — Consulte `crm_operacional.sqlite`:
   - `SELECT * FROM leads WHERE phone LIKE '%NUMERO%' OR name LIKE '%NOME%'`
   - Mostre estado atual, último contato, pipeline stage

2. **Router runtime** — Consulte `router_runtime.sqlite`:
   - Procure registros do lead (cache, estados, decisões do router)
   - Mostre últimas interações e decisões tomadas

3. **Logs** — Procure menções ao número nos logs em `C:\AUTOMACAO\logs\`

4. **Cache** — Verifique se há cache ativo para esse lead em `reference_patterns_cache/`

Apresente uma timeline do lead: quando entrou, mensagens trocadas, decisões do router, estado atual.
Se houver algo errado (lead preso, sem resposta, loop), diagnostique a causa e sugira correção.

Caminhos dos bancos:
- `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\crm_operacional.sqlite`
- `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\router_runtime.sqlite`
