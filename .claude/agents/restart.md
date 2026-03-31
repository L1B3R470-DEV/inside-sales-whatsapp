Reinicie componentes da stack do Atendente Inside Sales.

O usuário pode pedir para reiniciar um componente específico ou tudo. Identifique o que foi pedido e execute:

- **"tudo" / "all" / "stack"** → `docker compose down && docker compose up -d` + reiniciar router
- **"docker"** → `docker compose down && docker compose up -d`
- **"n8n"** → `docker restart n8n`
- **"evolution"** → `docker restart evolution`
- **"router"** → Parar o processo router_service.py e reiniciar via `start-router-service-detached.ps1`
- **"redis"** → `docker restart evolution-redis`
- **"postgres"** → `docker restart evolution-postgres`

Após reiniciar:
1. Aguarde 5-10 segundos
2. Confirme que o componente voltou com health check
3. Reporte o resultado

Diretório do docker-compose: `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES`
