# Projeto: WhatsApp B2B Inside Sales - Classe Couro
> Contexto de leitura para agent `integration` (OpenClaw)
> Status: READ-ONLY - não modificar nada sem autorização explícita

## Objetivo do sistema
Sistema de atendimento inteligente via WhatsApp para captação e qualificação de
leads B2B (revendedores de couro). Responde automaticamente como SDR humano
("Eduardo"), aprende com interações reais e escala qualificação sem custo de
atendimento humano.

## Stack ativa (host: Windows 10, C:\AUTOMACAO\)

| Componente         | Tecnologia             | Porta  | Status         |
|--------------------|------------------------|--------|----------------|
| WhatsApp gateway   | Evolution API (Docker) | 8080   | produção ativa |
| Automação de fluxo | n8n (Docker)           | 5678   | produção ativa |
| Router de decisão  | Flask/Python local     | 8091   | produção ativa |
| Banco CRM          | SQLite                 | -      | crm_operacional.sqlite |
| Banco runtime      | SQLite                 | -      | router_runtime.sqlite  |
| Vetorial RAG       | Qdrant local           | 6333   | ativo          |
| Backend Evolution  | PostgreSQL + Redis     | 5432/6379 | Docker      |
| LLM principal      | GPT-5.4 (OpenAI)       | -      | 10% dos casos  |
| LLM auxiliar       | Claude Sonnet 4.6      | -      | bridge/cowork  |

## Fluxo de mensagem

WhatsApp -> Evolution (8080) -> n8n webhook (5678) -> Router (8091)
  |- Cache SQLite       -> resposta direta (70%)
  |- RAG Qdrant/lexical -> contexto + GPT (20%)
  '- GPT direto         -> resposta IA (10%)
-> Evolution Send -> WhatsApp

## Arquivos principais do projeto

| Arquivo               | Função                                         |
|-----------------------|------------------------------------------------|
| router_service.py     | Núcleo de decisão: cache, RAG, GPT, rate-limit |
| guardrails.js         | Regras comerciais, horário, bloqueio, intents  |
| extract-reply.js      | Pós-processamento da resposta                  |
| build-fallback-reply.js | Fallback sem IA, mídia, saudação             |
| normalize-payload.js  | Normalização de payload inbound                |
| docker-compose.yml    | Infraestrutura completa                        |

## Bancos de dados

router_runtime.sqlite
- response_cache - respostas cacheadas por hash de mensagem
- route_logs - histórico de decisões do router
- rag_documents / rag_chunks - base vetorial lexical

crm_operacional.sqlite
- leads - leads ativos com score e status
- interactions - histórico completo de mensagens
- knowledge_rules - regras aprendidas (22 ativas)
- knowledge_cycles - 895 ciclos executados
- ignored_contacts_registry - 27 contatos bloqueados

## Ponte Claude<->Codex (bridge local)

Diretório base: C:\AUTOMACAO\cowork\claude_bridge\

| Diretório           | Função                                        |
|---------------------|-----------------------------------------------|
| inbox_for_claude/   | Tarefas JSON enviadas ao Claude para execução |
| outbox_from_claude/ | Respostas REPLY-*.json do Claude              |
| ack_from_codex/     | ACKs de confirmação do Codex                  |
| autoplan_inbox/     | Tarefas master para decomposição automática   |

Polling: 5s (worker), 4s (autopilot). Protocolo: JSON estruturado.
Dois processos ativos: claude_cowork_worker.py + claude_codex_autopilot.py

## Estado do CRM (marco 2026)
- 9 leads ativos (3 novos, 6 qualificando)
- 138 interações registradas
- 22 regras de conhecimento ativas
- 61 documentos indexados

## Persona SDR
- Nome: Eduardo
- Tom: humano, consultivo, comercial
- Horário: Seg-Sex 08:00-12:00 e 13:30-18:00 (America/Bahia)
- Instância Evolution ativa: ATENDIMENTO_VENDAS_CLEAN