Consulte e opere o CRM operacional do Atendente Inside Sales.

Banco: `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\crm_operacional.sqlite`

Comandos úteis:
- **Listar leads** → `SELECT * FROM leads ORDER BY updated_at DESC LIMIT 20`
- **Buscar lead** → por telefone, nome ou estado
- **Pipeline** → mostrar leads por estágio do funil
- **Estatísticas** → contagem por estado, conversão, etc.

Primeiro descubra o schema: `SELECT name FROM sqlite_master WHERE type='table'` e `.schema` das tabelas principais.

Quando o usuário pedir:
- **Consulta** → Execute SELECT e apresente resultados formatados
- **Atualização** → Execute UPDATE/INSERT com cuidado, sempre mostrando o antes/depois
- **Relatório** → Gere relatório com os dados pedidos
- **Reset de lead** → Resete estado de um lead específico (confirme o número antes)

NUNCA faça DELETE sem confirmação explícita. Para updates, sempre mostre o registro atual antes de modificar.

Scripts relacionados: `crm_cycle_engine.py`, `crm_sheet_sync.py`, `reset-lead-state.py`
