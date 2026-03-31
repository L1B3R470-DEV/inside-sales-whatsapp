# Google Sheets Bidirecional (OAuth de Usuario - Recomendado neste ambiente)

## Arquivos esperados em C:\ai
- `google-oauth-client.json` (OAuth Client ID tipo Desktop app)
- `google-oauth-token.json` (gerado automaticamente no bootstrap)
- `.env` com:
  - `GOOGLE_AUTH_MODE=oauth_user`
  - `GOOGLE_OAUTH_CLIENT_SECRET_JSON_PATH=/work/google-oauth-client.json`
  - `GOOGLE_OAUTH_TOKEN_JSON_PATH=/work/google-oauth-token.json`

## 1) Criar OAuth Client ID no Google Cloud
1. APIs and Services -> Credentials -> Create credentials -> OAuth client ID
2. Tipo: `Desktop app`
3. Baixe o JSON e salve em: `C:\ai\google-oauth-client.json`

## 2) Bootstrap OAuth + criacao de planilha
```powershell
powershell -ExecutionPolicy Bypass -File C:\ai\bootstrap-google-oauth-user.ps1
```

Esse comando:
- abre fluxo OAuth (URL + codigo) no terminal
- grava token em `C:\ai\google-oauth-token.json`
- cria planilha se `GOOGLE_SHEETS_SPREADSHEET_ID` estiver vazio
- grava `GOOGLE_SHEETS_SPREADSHEET_ID` no `.env`

## 3) Teste de sincronizacao bidirecional
```powershell
powershell -ExecutionPolicy Bypass -File C:\ai\run-crm-sheet-sync.ps1
```

Abas:
- `leads_snapshot`
- `open_backlog`
- `active_rules`
- `knowledge_cycles`
- `knowledge_rules_input` (entrada manual -> volta para SQLite/n8n)
- `backlog_updates` (entrada manual -> atualiza backlog)

## 4) Rotina automatica
Tarefa agendada `CRM_CYCLE_N8N` (15 min) roda:
- `C:\ai\run-crm-cycle-with-sheets.ps1`

## 5) Diagnostico rapido
```powershell
powershell -ExecutionPolicy Bypass -File C:\ai\check-google-sheets-ready.ps1
```

## Opcional: modo Service Account (fallback)
Se sua org liberar chave JSON de service account, o modo legado continua suportado com:
- `GOOGLE_AUTH_MODE=service_account`
- `GOOGLE_SERVICE_ACCOUNT_JSON_PATH=/work/google-service-account.json`
