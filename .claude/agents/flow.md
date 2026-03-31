Analise e ajude a ajustar o fluxo de atendimento WhatsApp.

O fluxo completo é: WhatsApp → Evolution API → n8n → Router (Python) → Cache/RAG/GPT → resposta

Arquivos do fluxo:
- `normalize-payload.js` — normaliza mensagem recebida
- `router-decision.js` — ponte n8n→router (envia para decisão)
- `router_service.py` — roteador principal (decide cache/RAG/GPT)
- `extract-reply.js` — extrai resposta do GPT
- `build-fallback-reply.js` — fallback quando GPT falha
- `router-learn.js` — feedback de aprendizado
- `resolve-recipient.js` — resolve destinatário da resposta

Quando o usuário descrever um problema no fluxo:
1. Identifique em qual etapa o problema ocorre
2. Leia o(s) arquivo(s) relevante(s)
3. Diagnostique a causa raiz
4. Proponha e aplique a correção

Mantenha compatibilidade com n8n (os .js são Code Nodes do n8n).
