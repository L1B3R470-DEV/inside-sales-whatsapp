Aplique mudanças e reinicie serviços de forma segura.

Checklist de deploy:

1. **Verificar estado atual** — `git status` para ver o que mudou
2. **Validar sintaxe JS** — rode `node check_js_syntax.js` nos arquivos .js alterados
3. **Validar sintaxe Python** — rode `python -m py_compile` nos .py alterados
4. **Commit** — faça commit das mudanças com mensagem descritiva
5. **Reiniciar serviços afetados:**
   - Se mudou `.js` (n8n nodes) → reiniciar n8n: `docker restart n8n`
   - Se mudou `router_service.py` → reiniciar router
   - Se mudou `docker-compose.yml` → `docker compose down && docker compose up -d`
   - Se mudou `guardrails.js` → reiniciar n8n: `docker restart n8n`
6. **Health check** — confirmar que tudo voltou OK

Diretório: `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES`
Git identity: Inside Sales Dev <dev@insidesales.local>

Sempre reporte o que foi deployado e o estado final dos serviços.
