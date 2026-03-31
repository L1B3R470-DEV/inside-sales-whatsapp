# Arquitetura Completa | SDR IA B2B com RAG Autônomo

## Objetivo
Construir um sistema de atendimento inteligente via WhatsApp para:
- captação de leads B2B
- qualificação de revendedores
- respostas comerciais automáticas
- aprendizado contínuo
- baixo custo operacional

## Stack
- `n8n`
- `Evolution`
- `GPT-5.4` via API
- `Python`
- banco vetorial local
- `Windows 11`

## Princípio fundamental
Distribuição de inteligência:
- `70%` regras e cache
- `20%` RAG
- `10%` IA

Regra de decisão:
- `Cache` primeiro
- `RAG` depois
- `IA` por último

## Arquitetura operacional
```text
WhatsApp
  -> Evolution
  -> Webhook n8n
  -> Router lógico
     -> Cache
     -> RAG
     -> GPT
  -> Evolution Send
```

## Estrutura física
`C:\AUTOMACAO\`

- `rag\`
- `scripts\`
- `cache\`
- `logs\`
- `dados\`

Implementação atual:
- `C:\AUTOMACAO\rag\knowledge` aponta para a base local `CHATGPT_MACHINE_LEARNING`
- `C:\AUTOMACAO\rag\vector_store` guarda o banco vetorial local
- `C:\AUTOMACAO\dados\router_runtime.sqlite` guarda cache, logs e chunks
- `C:\AUTOMACAO\logs\` guarda logs do roteador

## Fluxo de atendimento
1. cliente envia mensagem
2. n8n recebe via webhook
3. `Router Decision` consulta cache
4. se não houver cache, classifica a mensagem
5. se for simples, segue para GPT direto
6. se for média/complexa, tenta RAG
7. se houver contexto útil, segue com `rag_gpt`
8. `Router Learn` aprende respostas seguras e reutilizáveis

## Componentes principais
- `router_service.py`: cache, classificação, RAG, score e logs
- `guardrails.js`: regras comerciais, triagem e construção de contexto
- `extract-reply.js`: pós-processamento da resposta
- `build-fallback-reply.js`: resposta sem IA e envio de mídia/documento
- `patch_workflow_router_v1.py`: integra o roteador no workflow do n8n

## Cache
Base local em SQLite:
- `response_cache`

Casos prioritários:
- pedido mínimo
- prazo de entrega
- formas de pagamento
- revenda
- institucional simples

## Classificação
Saídas:
- `simple`
- `medium`
- `complex`

Uso atual:
- simples -> GPT direto
- médio/complexo -> tenta RAG antes de GPT

## RAG
Pipeline:
```text
arquivo -> extração -> limpeza -> chunk -> embedding/busca -> resposta
```

Formatos suportados:
- `.txt`
- `.md`
- `.csv`
- `.json`
- `.xml`
- `.html`
- `.docx`
- `.xlsx`
- `.pdf`
- `.rtf`

Chunking:
- alvo aproximado: `420 tokens`
- faixa operacional: `300–800 tokens`

Busca:
- `top 3` para mensagens médias
- `top 5` para mensagens complexas

Fallback resiliente:
- se embeddings falharem ou a quota da OpenAI estiver indisponível, o sistema usa busca lexical local e não interrompe o atendimento

## Metadados
Persistidos por chunk/documento:
- fonte
- tipo
- data de indexação
- hash
- prioridade implícita por score de busca

## Score de lead
Regras atuais no roteador:
- revenda / atacado / lojista / representante -> soma
- presença de CNPJ -> soma
- sinais de volume/prazo/entrega -> soma
- categorias de produto -> soma

Uso:
- priorização
- enriquecimento de contexto
- base para futura fila humana

## Aprendizado contínuo
Pipeline:
```text
conversa -> resposta segura -> learn-response -> response_cache
```

Critérios:
- confiança alta
- intenção segura
- mensagem não ambígua
- resposta curta e reutilizável

## Logs e rastreabilidade
Tabela:
- `route_logs`

Campos principais:
- número
- nome
- texto recebido
- rota escolhida
- complexidade
- cache hit
- lead score
- score do RAG
- timestamp

## Observações práticas
- o workflow principal ativo é `zN3heKJVLO8w4dG6`
- o roteador local fica em `http://localhost:8091`
- o n8n acessa o roteador por `http://host.docker.internal:8091`
- o modelo operacional principal está em `gpt-5.4`

## Restrições respeitadas
- sem `OpenClaw`
- sem `Claude`
- foco em execução real no `Windows`
- sem depender totalmente da IA

## Próxima evolução recomendada
1. normalizar quota de embeddings da OpenAI
2. ativar busca híbrida vetorial + lexical
3. criar dashboard de métricas
4. criar fila humana baseada em lead score e intenção
