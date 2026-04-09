# WhatsApp B2B SDR | Execução Prática

## Arquitetura
- WhatsApp -> Evolution -> n8n -> Router Local -> Cache | RAG | GPT-5.4
- Prioridade operacional: `Cache -> RAG -> GPT`
- Distribuição de inteligência: `70% regras/cache`, `20% RAG`, `10% IA`

## Topologia operacional obrigatoria
- `PC CLS` (`100.113.13.27`) e a origem unica das IAs operacionais do atendente.
- `PC CLS` (`100.113.13.27`) hospeda o Docker operacional do projeto.
- `PC LBN` (`100.101.106.95`) e somente interface interativa, coordenacao humana e distribuicao manual de prompts.
- O Docker do `PC LBN` nao participa do runtime real do atendente.
- Definicao estrutural detalhada: [ATTENDANT_RUNTIME_TOPOLOGY.md](C:\Users\User\Desktop\PROJETO%20ATENDIMENTO%20WHATSAPP%20INSIDE%20SALES\ATTENDANT_RUNTIME_TOPOLOGY.md)

## Pastas
### Código-fonte
- `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES`

### Runtime operacional
- `C:\AUTOMACAO\rag`
- `C:\AUTOMACAO\cache`
- `C:\AUTOMACAO\logs`
- `C:\AUTOMACAO\dados`
- `C:\AUTOMACAO\scripts`

## Componentes
- `router_service.py`: roteador, cache, score, RAG e logs
- `start-router-service.ps1`: sobe o roteador usando `C:\AUTOMACAO`
- `start-router-service-detached.ps1`: sobe em background com logs
- `router-watchdog.ps1`: monitora saúde do roteador e reinicia automaticamente
- `setup-automacao-runtime.ps1`: prepara `C:\AUTOMACAO`
- `reset-lead-state.ps1`: limpa um lead em todas as camadas
- `reset-lead-state-menu.ps1`: menu interativo para reset de lead
- `patch_workflow_intelligence_v1.py`: atualiza nós principais do workflow
- `patch_workflow_router_v1.py`: integra `Router Decision` e `Router Learn`

## Setup do runtime
```powershell
powershell -ExecutionPolicy Bypass -File ".\setup-automacao-runtime.ps1"
```

## Subir Docker
```powershell
cd "C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES"
docker compose up -d
```

## Subir roteador
Foreground:
```powershell
powershell -ExecutionPolicy Bypass -File ".\start-router-service.ps1"
```

Background:
```powershell
powershell -ExecutionPolicy Bypass -File ".\start-router-service-detached.ps1"
```

## Tarefas agendadas
- `WA_Router_Service`
- `WA_Router_Watchdog`

Executar:
```powershell
Start-ScheduledTask -TaskName "WA_Router_Service"
Start-ScheduledTask -TaskName "WA_Router_Watchdog"
```

Watchdog manual:
```powershell
powershell -NoLogo -ExecutionPolicy Bypass -File "C:\AUTOMACAO\scripts\router-watchdog.ps1"
```

## Endpoints locais
Health:
```powershell
Invoke-RestMethod http://localhost:8091/health
```

Route:
```powershell
$body = @{ number = '557583211367'; pushName = 'Welber'; inboundText = 'Como faço para revender Classe?' } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8091/route -Method Post -ContentType 'application/json' -Body $body
```

## Reset rápido de lead
### Modo mais simples: menu interativo
```powershell
powershell -ExecutionPolicy Bypass -File "C:\AUTOMACAO\scripts\reset-lead-state-menu.ps1"
```

Fluxo:
- cola o número
- confirma `S/N`
- escolhe simulação, backup e restart
- executa a limpeza completa

### Modo direto
Com backup automático:
```powershell
powershell -ExecutionPolicy Bypass -File "C:\AUTOMACAO\scripts\reset-lead-state.ps1" -Number "557588340000"
```

Somente simulação:
```powershell
powershell -ExecutionPolicy Bypass -File "C:\AUTOMACAO\scripts\reset-lead-state.ps1" -Number "557588340000" -DryRun
```

Sem backup e sem restart:
```powershell
powershell -ExecutionPolicy Bypass -File "C:\AUTOMACAO\scripts\reset-lead-state.ps1" -Number "557588340000" -SkipBackup -SkipRestart
```

O script limpa:
- CRM operacional
- router local
- `staticData` e execuções salvas do `n8n`
- contato, mensagens e updates no Evolution

## Observabilidade
Logs:
- `C:\AUTOMACAO\logs\router-service.out.log`
- `C:\AUTOMACAO\logs\router-service.err.log`
- `C:\AUTOMACAO\logs\router-watchdog.log`

## Planilha de leads
- Planilha principal autoalimentada:
  - `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\LEADS_INSIDE_SALES_AUTO.xlsx`
- Cópia em exports:
  - `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\crm_exports\LEADS_INSIDE_SALES_AUTO.xlsx`
- Atualização:
  - a cada ciclo do `CRM_CYCLE_N8N`
  - frequência atual: `15 minutos`
- Abas:
  - `leads_operacional`
  - `interacoes_recentes`
  - `resumo_funil`

Banco:
- `C:\AUTOMACAO\dados\router_runtime.sqlite`

Backups:
- `C:\AUTOMACAO\dados\backups`

## Observação importante
- Quando embeddings estiverem indisponíveis por quota da OpenAI, o sistema mantém o atendimento com busca lexical local e não interrompe o fluxo.
- O reset limpa o estado do sistema. O histórico visual no app/WhatsApp Web pode depender da própria conta do WhatsApp.
