Analise e melhore o router_service.py — o cérebro do atendente.

Leia `router_service.py` e entenda a lógica atual de roteamento:
- Cache hit → resposta instantânea
- RAG match → resposta por contexto vetorial
- GPT fallback → resposta gerada pela IA
- Rate limiting, LID (Language Intent Detection), etc.

Quando o usuário pedir:
- **Análise** → Explique o fluxo de decisão atual, com pontos fortes e fracos
- **Performance** → Identifique gargalos e sugira otimizações
- **Nova rota** → Adicione novo caminho de decisão mantendo a arquitetura
- **Bug fix** → Investigue e corrija o problema reportado

Arquivo: `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\router_service.py`
Banco: `C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES\router_runtime.sqlite`
Venv: `.venv-router/Scripts/activate`
Porta: 8091
