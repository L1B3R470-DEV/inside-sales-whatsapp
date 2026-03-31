Simule o envio de uma mensagem para testar o fluxo de atendimento.

Use o payload de teste como base: `payload_test_inbound.json`

Opções de teste:
1. **Testar router direto** — enviar POST para `http://localhost:8091` com payload simulado
2. **Testar n8n webhook** — se o webhook estiver configurado, enviar via curl
3. **Testar Evolution** — enviar mensagem real via Evolution API na porta 8080

Quando o usuário pedir um teste:
1. Pergunte qual tipo de teste (router / n8n / evolution) se não especificado
2. Monte o payload com a mensagem desejada
3. Execute o curl e mostre a resposta completa
4. Analise a resposta: identificou o intent? Usou cache/RAG/GPT? Resposta faz sentido?

Para teste do router:
```
curl -X POST http://localhost:8091/router -H "Content-Type: application/json" -d '{"phone":"5511999999999","message":"MENSAGEM_AQUI"}'
```

Adapte o payload conforme o schema real do router (leia router_service.py se necessário).
