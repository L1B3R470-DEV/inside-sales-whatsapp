# CHANGELOG — 2026-04-16

> **Sessão de emergência** desencadeada por desconexão da Evolution API (código 401, 17:32 UTC) e falha de atendimento ao lead Emersoninho (fase de pagamento). Todas as mudanças abaixo estão prontas no repositório local e aguardam commit + deploy.

---

## CRÍTICO — Correção de LID JID (bloqueio total de atendimento)

**Problema:** WhatsApp passou a usar JIDs internos (`@lid`) para alguns contatos. Quando o LID não é resolvido para número de telefone, o campo `recipientNumber` chega vazio no guardrails, que bloqueia toda a resposta (`allowAi=false`, `sendEligible=false`, `reason='no_recipient'`). O resultado: silêncio total — nenhuma mensagem é enviada ao lead.

**Correção aplicada em dois níveis:**

### 1. `guardrails.js` — `lidManualMap`
```js
const lidManualMap = {
  '114062134407423@lid': '557588340000',         // mapeamento anterior
  '5093848051920@lid':   '557591691926',          // Emersoninho +55 75 9169-1926 — 2026-04-16
  '181475437711612@lid': '558781050990'           // Rejane Monteiro +55 87 8105-0990 — 2026-04-16
};
```

### 2. `router_service.py` — banco `lid_mappings`
Ambos os LIDs registrados via `POST http://100.113.13.27:8091/resolve-recipient` (em produção, efeito imediato):
- `5093848051920@lid` → `557591691926` ✅ **ativo em produção**
- `181475437711612@lid` → `558781050990` ✅ **ativo em produção**

---

## 1. `guardrails.js`

### Identidade do consultor
- Nome alterado de `Eduardo` → `Eduardo Vinhas` em todos os pontos de configuração e mensagens.
- Nome da empresa simplificado de `Classe Couro` → `Classe` nas mensagens ao cliente (instrução explícita: nunca escrever "Classe Couro" nas falas do atendente).

### Mensagens de fallback — reescritas (mais curtas e objetivas)
| Campo | Antes | Depois |
|---|---|---|
| `outOfHoursMessage` | Texto longo com janela de horário completa | `"Aqui é Eduardo Vinhas, da Classe. Recebi sua mensagem. No próximo horário eu sigo com prioridade."` |
| `highVolumeMessage` | Texto longo | `"Aqui é Eduardo Vinhas, da Classe. Seu atendimento já está em prioridade. Me diga o produto e a quantidade desejada."` |
| `unresolvedRecipientMessage` | Texto longo | `"Aqui é Eduardo Vinhas, da Classe. Tive uma instabilidade para identificar seu contato. Pode repetir sua mensagem?"` |
| `missingKeyMessage` | Texto longo | `"Aqui é Eduardo Vinhas, da Classe. Seu contato já foi registrado e sigo com você por aqui."` |

### Modo de teste desabilitado
- `testModeOnlyAllowedNumbers: false` — permite atendimento a todos os leads (não apenas números autorizados).

### Fluxo B2B — entrega automática de credenciais
- URL do portal B2B configurada: `https://mstabletssl.ddns.net/wsB2BProspClasseCouro1ssl/acessocliente.aspx`
- `operatorApprovalRequired: false` — link enviado automaticamente, sem aprovação manual.
- `buildB2BAccessReply()` reescrita: entrega login (CNPJ) e senha inicial (8 primeiros dígitos do CNPJ) diretamente na conversa.
- Novo fluxo `b2bCredentialFlow`: quando CNPJ está disponível e lead pede acesso B2B, entrega credenciais imediatamente e avança estado do perfil.
- Novo fluxo `explicitB2BRequest`: quando lead pede B2B sem CNPJ, envia link sem senha e solicita CNPJ.
- Keywords adicionais de detecção: `'link do b2b'`, `'site do b2b'`, `'portal do b2b'`, `'me enviar o link do b2b'`, `'me manda o link do b2b'`.

### Mensagens simplificadas (tom mais direto)
- `buildSalesBookPresentation()` — modo `resend` e modo padrão: texto reduzido, sem redundância.
- `buildVitrinePresentationReply()` — texto reduzido.
- `buildSemCnpjSiteReply()` — texto reduzido, removido "Obrigado pelo seu contato e conte com a gente".
- Resposta de lead sem loja física — texto reduzido.
- Caption do Sales Book: `'BOOK DE VENDAS | Colecao Classe'`.

### LID Manual Map atualizado
- Emersoninho e Rejane adicionados (ver seção CRÍTICO acima).

---

## 2. `router_service.py`

### Transcrição de áudio — Strategy 1: Evolution API (NOVO)
**Problema identificado:** URLs de áudio do WhatsApp apontam para CDN criptografado (`mmg.whatsapp.net`, `media.whatsapp.net`, etc.). O áudio nesses URLs é encriptado end-to-end e não pode ser transcrito diretamente pelo OpenAI. Resultado: `audio_untranscribed` silencioso.

**Solução:** Novo pipeline de transcrição em duas estratégias:

- **Strategy 1 (preferida):** Quando URL é WhatsApp CDN criptografado, busca o áudio descriptografado via `POST /chat/getBase64FromMediaMessage/{instance}` na Evolution API. Evolution retorna o áudio em base64 já descriptografado. Envia para OpenAI Whisper.
- **Strategy 2 (fallback):** Tenta URL direta ou base64 do payload (comportamento anterior).

**Novas funções:**
- `_is_whatsapp_cdn_url(url)` — detecta URLs de CDN criptografado.
- `_fetch_audio_via_evolution(message_id, remote_jid, instance)` — busca áudio via Evolution API.
- `_call_openai_transcription(audio_bytes, mime_type, file_name)` — refatoração da chamada OpenAI para função reutilizável.

**Novas constantes de ambiente:**
- `EVOLUTION_API_KEY` → `os.getenv('EVOLUTION_API_KEY')`
- `EVOLUTION_API_URL` → `os.getenv('ROUTER_EVOLUTION_API_URL', 'http://evolution:8080')`

**Logging melhorado:** Logs `INFO` com `has_url`, `is_encrypted_cdn`, `has_base64`, `has_evolution_key`, `instance`, `message_id` para diagnóstico completo de falhas de transcrição.

### Staged (aguardando commit)
- 6 linhas adicionais já em staging (`git add`).

---

## 3. `extract-reply.js`

### Novas funções de sanitização de texto
- `sentenceTrim(text, maxSentences, maxChars)` — limita resposta a N frases e M caracteres, cortando em pontuação limpa.
- `dropLocationSentences(text)` — remove frases que mencionam cidades/regiões (evita `"para sua região"`, `"na cidade de X"`).
- `sanitizeCommercialStyle(value, ctx)` — sanitização completa de estilo comercial (remove markdown, separadores `---`, controla tamanho).
- `escapeRegExp(value)` — utilitário para escapar strings em regex.

### Mensagens de fallback atualizadas
- `fallbackBusy`: `'Seu atendimento já está em prioridade. Me diga qual produto você precisa para eu adiantar por aqui.'`
- `fallbackWaiting`: `'Recebi sua mensagem e já sigo com você por aqui. Me diga qual produto você precisa e a quantidade desejada.'`

---

## 4. `build-fallback-reply.js`

- Mesmas funções compartilhadas importadas/replicadas: `sentenceTrim`, `dropLocationSentences`, `sanitizeCommercialStyle`, `escapeRegExp`.
- Sanitização de markdown (`*+`) e separadores `---` aplicada nos fallbacks.

---

## 5. `normalize-payload.js`

### Extração de campos de remetente expandida
Novos candidatos extraídos do payload de entrada:
- `senderPhoneCandidate` — tenta `senderPn`, `sender_pn`, `senderPhone`, `sender_phone` (payload e body).
- `participantJidCandidate` — tenta `key.participant`, `payload.participant`, `participantJid`, `body.participant`, `contextInfo.participant` (normaliza `:\d+@` → `@`).
- `senderJidCandidate` — tenta `senderJid`, `senderLid`, `fromJid` (payload e body).
- `quotedMessageId` — exposto no output normalizado.

---

## 6. `docker-compose.yml`

- Remoção do BOM UTF-8 (`﻿services` → `services`).
- `ROUTER_CRM_PATH=/runtime/crm_operacional.sqlite` adicionado ao router.
- `ROUTER_BASE_URL` alterado de `http://router:8091` → `http://host.docker.internal:8091` (permite acesso externo ao router local).
- `ROUTER_EVOLUTION_API_URL=http://evolution:8080` adicionado (necessário para Strategy 1 de transcrição de áudio).
- Router: `expose: ["8091"]` substituído por `ports: ["8091:8091"]` (porta exposta no host).

---

## 7. `sdr_prompt.txt`

- `"Eduardo, Consultor de Vendas Internas da Classe Couro"` → `"Eduardo Vinhas, Consultor de Vendas Internas da Classe"`.
- Foco do lead: `"produto, quantidade, cidade/estado, prazo"` → `"produto, quantidade e próximo passo comercial, sem textão"`.
- Novas restrições explícitas:
  - `"Use somente o nome Classe. Nunca escreva Classe Couro."`
  - `"Nunca use premium."`
  - `"Nunca defina produtos por gênero."`
  - `"Nunca mencione a cidade informada pelo lead na resposta."`
  - `"Se precisar pedir CNPJ, faça isso uma única vez e sem assinatura longa."`

---

## 8. Novos arquivos (não commitados)

| Arquivo | Descrição |
|---|---|
| `diag_audio_transcricao.ps1` | Script PowerShell de diagnóstico de falhas de transcrição de áudio |
| `migrate_crm_and_rebuild.ps1` | Script de migração do CRM e rebuild do router |
| `qr_reconectar.html` | Página HTML de reconexão Evolution (QR code auto-refresh) — gerada na sessão de emergência |
| `rebuild_router.bat` / `rebuild_router.ps1` | Scripts de rebuild e restart do container do router |
| `sanitize_runtime_texts.py` | Script para sanitizar textos antigos no banco de runtime |

---

## 9. Arquivos com alterações menores

- `backfill_response_cache.py` — ajuste pontual.
- `claude_cowork_worker.py` — ajuste de 19 linhas.
- `docker/router/Dockerfile` — adição de dependência.
- `requirements-router.txt` — nova dependência.
- `patch_workflow_intelligence_v1.py` — 120+ linhas de expansão.
- `sales_book_asset_snapshot.json` — 4 linhas.
- `sync_sales_book_asset.py` — ajuste pontual.
- `.gitignore` — 4 linhas adicionadas.
- `Enable-Aspia.ps1` — **removido** (373 linhas deletadas).

---

## Status de deploy

| Componente | Status |
|---|---|
| LID Emersoninho no router DB | ✅ **ativo em produção** |
| LID Rejane no router DB | ✅ **ativo em produção** |
| `guardrails.js` (arquivo local) | ⚠️ **não deployado no n8n** |
| `router_service.py` (Strategy 1 áudio) | ⚠️ **não deployado — aguarda rebuild do container** |
| Evolution API | ⚠️ **desconectada — aguarda reconexão** |
| Commit git | ⚠️ **pendente** |
\n
