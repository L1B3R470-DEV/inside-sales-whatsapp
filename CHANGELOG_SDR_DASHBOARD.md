# CHANGELOG — SDR Dashboard Fixes
**Data:** 2026-04-16
**Autor:** Claude (sessão Cowork)
**Sessão:** Diagnóstico e correção de anomalias do `/sdr-dashboard`

---

## ⚠️ ATENÇÃO: REBUILD NECESSÁRIO

Após este changelog, execute o script de migração e rebuild:

```powershell
# No diretório do projeto, como Administrador:
.\migrate_crm_and_rebuild.ps1
```

Ou manualmente:
```powershell
Copy-Item crm_operacional.sqlite C:\AUTOMACAO\dados\crm_operacional.sqlite
docker build -t attendant-router:latest -f docker/router/Dockerfile .
docker compose up -d --no-deps router
```

---

## BUG CRÍTICO #1 — CRM desconectado do volume persistente

**Arquivo:** `docker-compose.yml` + `router_service.py`
**Severidade:** CRÍTICA — perda de dados ao reiniciar container

### Causa raiz
O Dockerfile usa `WORKDIR /app`. A variável `crm_path = ROOT_DIR / 'crm_operacional.sqlite'` resolve para `/app/crm_operacional.sqlite` dentro do container, que **não está mapeado em nenhum volume Docker**. Resultado:
- A cada restart do container, o CRM é recriado vazio
- O dashboard sempre mostrava `LEADS = 0` e `MSGS HOJE = 0`
- `leads_raw = []` sem exceção (SQLite cria arquivo vazio silenciosamente)
- O painel "Leads" exibia "Nenhum lead"

### Solução
**`router_service.py` (linha 68):** adicionada constante configurável via env var:
```python
# ANTES
# (sem CRM_PATH — hardcoded em sdr_dashboard_data)

# DEPOIS
CRM_PATH = Path(os.getenv('ROUTER_CRM_PATH', ROOT_DIR / 'crm_operacional.sqlite'))
```

**`router_service.py` (em `sdr_dashboard_data`):**
```python
# ANTES
crm_path = ROOT_DIR / 'crm_operacional.sqlite'

# DEPOIS
crm_path = CRM_PATH
```

**`docker-compose.yml` (seção `router` → `environment`):**
```yaml
# ADICIONADO
- ROUTER_CRM_PATH=/runtime/crm_operacional.sqlite
```

O volume `/runtime` já estava mapeado para `C:\AUTOMACAO\dados`, então o CRM agora persiste junto ao `router_runtime.sqlite`.

---

## BUG #2 — Conexão CRM sem WAL mode e sem busy_timeout

**Arquivo:** `router_service.py`
**Severidade:** ALTA — race condition leva a `OperationalError: database is locked`

### Causa raiz
A conexão SQLite ao `crm_operacional.sqlite` não configurava `journal_mode=WAL` nem `busy_timeout`. Com escritas concorrentes (crm_cycle_engine, crm_sheet_sync), a conexão pode falhar silenciosamente, devolvendo stats zerados.

### Solução
```python
# ADICIONADO após sqlite3.connect(...)
crm.execute('PRAGMA journal_mode=WAL')
crm.execute('PRAGMA busy_timeout=5000')
```

---

## BUG #3 — `r['created_at'][:19]` sem guarda de nulo

**Arquivo:** `router_service.py` — loop `for r in recent_routes`
**Severidade:** MÉDIA — TypeError silencioso derruba o bloco try/except

### Causa raiz
```python
r_ts = r['created_at'][:19]  # TypeError se created_at for None
```
Se algum registro de `route_logs` tiver `created_at = NULL`, o slice lança `TypeError` que é capturado pelo `except Exception` externo, zerando todo o bloco de stats CRM.

### Solução
```python
# ANTES
r_ts = r['created_at'][:19]

# DEPOIS
r_ts = (r.get('created_at') or '')[:19]
if not r_ts:
    continue
```

---

## BUG #4 — `outbound_by_number` com chave None

**Arquivo:** `router_service.py`
**Severidade:** BAIXA — inconsistência de lookup

### Causa raiz
Interações com `number = NULL` geravam chave `None` no dict, enquanto o lookup buscava por `''` (string vazia).

### Solução
```python
# ANTES
outbound_by_number.setdefault(row['number'], []).append(dict(row))

# DEPOIS
outbound_by_number.setdefault(str(row['number'] or ''), []).append(dict(row))
```

---

## BUG #5 — Display "ERRO OPERACIONAL / Numero nao resolvido" para contatos LID

**Arquivos:** `router_service.py` + `dashboard_sdr.html`
**Severidade:** BAIXA — label incorreto e alarmante para comportamento esperado

### Causa raiz
Contatos com JID `@lid` (novo formato WhatsApp) têm `number = ''` no `route_logs` pois o mapeamento LID→telefone não foi resolvido. O dashboard exibia isso como erro vermelho "ERRO OPERACIONAL", quando na verdade é um estado informativo.

### Solução
**`router_service.py`:**
```python
# ANTES
display_label = 'Numero nao resolvido'

# DEPOIS
display_label = 'JID nao resolvido'
```

**`dashboard_sdr.html`:**
```javascript
// ANTES
statusBubble = `<div class="bbl bbl-err">...ERRO OPERACIONAL...`

// DEPOIS
statusBubble = `<div class="bbl bbl-wait">...JID não resolvido — contato via LID...`
```
Mudado de vermelho (`bbl-err`) para cinza-espera (`bbl-wait`).

---

## BUG #6 — Label "AUDIO_UNTRAI" truncada na Distribuição

**Arquivo:** `dashboard_sdr.html`
**Severidade:** BAIXA — cosmético

### Causa raiz
A função `routeMeta()` não tratava a rota `audio_untranscribed`, caindo no caso `rb-unknown` que usa o valor bruto `"audio_untranscribed"` como label. Com `.dist-lbl { width: 80px }`, o texto era cortado para "AUDIO_UNTRAI".

### Solução
```javascript
// ADICIONADO em routeMeta()
if (r.includes('audio'))
  return { cls:'rb-unknown', lbl:'Áudio', desc:'Áudio não transcrito (mensagem de voz sem texto)' };
```

Também aumentada a largura da label de distribuição de `80px` para `90px`.

---

## BUG #7 — Exceções CRM engolidas sem visibilidade

**Arquivo:** `router_service.py`
**Severidade:** BAIXA — dificulta diagnóstico futuro

### Solução
Adicionado `_debug` no payload de resposta e traceback completo no log:
```python
# ADICIONADO no except
import traceback as _tb
_crm_error_msg = f'{type(exc).__name__}: {exc}'
log.warning('sdr_dashboard_data_crm_error', error=_crm_error_msg, traceback=_tb.format_exc())

# ADICIONADO no response
'_debug': {'crmError': _crm_error_msg} if _crm_error_msg else {},
```

Quando houver erro, `/sdr-dashboard-data` retorna `"_debug": {"crmError": "..."}` para diagnóstico via DevTools.

---

## Arquivos modificados

| Arquivo | Tipo de mudança |
|---|---|
| `router_service.py` | Bug fixes #1, #2, #3, #4, #5, #7 |
| `dashboard_sdr.html` | Bug fixes #5, #6 |
| `docker-compose.yml` | Bug fix #1 — env var `ROUTER_CRM_PATH` |
| `migrate_crm_and_rebuild.ps1` | **NOVO** — script de migração e rebuild |

---

## O que NÃO foi alterado (para CODEX não sobrescrever)

- Lógica de roteamento (`route_message`, `log_route`) — intacta
- Esquema do `router_runtime.sqlite` — intacto
- Esquema do `crm_operacional.sqlite` — intacto
- Fluxo n8n — não tocado
- `guardrails.js`, `extract-reply.js`, `normalize-payload.js` — não tocados
- Autenticação, rate-limit, RAG, cache semântico — não tocados

---

## Status após rebuild

Após executar `migrate_crm_and_rebuild.ps1`, o dashboard deve exibir:
- ✅ `LEADS` → número real de leads do CRM
- ✅ `MSGS HOJE` → contagem real de interações do dia
- ✅ Painel "Leads" → lista de leads com stage e city
- ✅ `DISTRIBUIÇÃO HOJE` → "Áudio" em vez de "AUDIO_UNTRAI"
- ✅ Contatos LID → card cinza informativo em vez de erro vermelho
- ✅ Exceções CRM → expostas em `_debug.crmError` no JSON
\n
