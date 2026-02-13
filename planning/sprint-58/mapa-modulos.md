# Mapa de Modulos - Agente Julia

> Documento de referencia para Sprint 58 (Refatoracao Estrategica).
> Gerado em 2026-02-12.

## Estrutura de Alto Nivel

```
app/
├── api/routes/      (28 routers)     — Endpoints HTTP
├── services/        (268+ arquivos)  — Logica de negocio
├── tools/           (9+ arquivos)    — Tools do LLM
├── pipeline/        (22 arquivos)    — Pipeline de mensagens
├── workers/         (10 arquivos)    — Jobs em background
├── core/            (14 arquivos)    — Infraestrutura base
├── prompts/         (3 arquivos)     — Prompts dinamicos
├── schemas/         (2 arquivos)     — Pydantic schemas
├── repositories/    (3 arquivos)     — Data access
├── config/          (3 arquivos)     — Config estatica
├── fragmentos/      (2 arquivos)     — Templates de msg
└── constants/       (1 arquivo)      — Constantes
```

## Modulos de Servico (app/services/)

| Modulo | Arquivos | Funcao |
|--------|----------|--------|
| `julia/` | 7 | Agente conversacional principal |
| `llm/` | 7 | Abstracao de LLM (Haiku/Sonnet) |
| `helena/` | 2 | Agente analytics no Slack |
| `policy/` | 14 | Motor de decisao deterministico |
| `chips/` | 13 | Orquestracao multi-chip WhatsApp |
| `campanhas/` | 3 | Gestao de campanhas |
| `grupos/` | 17 | Pipeline de grupos WhatsApp |
| `extraction/` | 4 | Inteligencia de conversas |
| `conhecimento/` | 6 | RAG / conhecimento dinamico |
| `warmer/` | 11 | Aquecimento de chips |
| `vagas/` | 9 | Busca e reserva de plantoes |
| `guardrails/` | 2 | Controle de envio outbound |
| `business_events/` | 15 | Tracking de funil |
| `handoff/` | 3 | Handoff IA <-> humano |
| `slack/` | 5 | Agente NLP no Slack |
| `whatsapp_providers/` | 3 | Multi-provider WhatsApp |
| `jobs/` | 4 | Gestao de jobs em background |
| + ~70 standalone | - | Agente, contexto, memoria, deteccoes, metricas, etc. |

## Dependencias Cruzadas Principais

| De -> Para | Dependencias |
|-----------|-------------|
| **webhook** -> pipeline | Toda mensagem passa pelo pipeline |
| **pipeline** -> policy | Pre-processor consulta estado do medico |
| **policy** -> supabase | Estado persistido em `doctor_states` |
| **julia/agent** -> llm, tools, conhecimento | Gera resposta usando LLM + tools + RAG |
| **llm/** -> Anthropic | Claude Haiku (80%) e Sonnet (20%) |
| **tools** -> vagas, handoff, memoria | Tools executam acoes de negocio |
| **outbound** -> guardrails, chips | Toda saida passa por guardrails e chip selector |
| **chips/** -> whatsapp_providers | Abstracao sobre Evolution/Z-API |
| **campanhas** -> fila_mensagens -> fila_worker | Campanhas viram msgs na fila |
| **grupos/** -> llm, vagas | Classifica msgs e importa vagas |
| **warmer/** -> chips, whatsapp_providers | Aquece chips novos |
| **slack/helena** -> llm, supabase | Agents de gestao no Slack |
| **dashboard** -> api/routes -> services | Frontend consome a API REST |
| **workers** -> todos os services | Jobs rodam logica de negocio em background |
| **Tudo** -> supabase, redis, core | Infraestrutura compartilhada |

## Servicos Externos

| Servico | Proposito | Usado Por |
|---------|-----------|-----------|
| **Supabase** | PostgreSQL + pgvector | Todos (database) |
| **Anthropic** | Claude LLM (Haiku, Sonnet) | llm/, julia/, helena/, grupos/ |
| **Voyage AI** | Text embeddings | conhecimento/, memoria/ |
| **Evolution API** | WhatsApp provider | whatsapp.py, chips/ |
| **Z-API** | WhatsApp provider (alt) | whatsapp_providers/zapi.py |
| **Chatwoot** | Customer support | chatwoot.py |
| **Slack** | Notificacoes + comandos | slack/, helena/ |
| **Google Docs** | Briefing generation | google_docs.py, briefing.py |
| **Redis** | Cache + rate limiting | redis.py, rate_limiter.py |

## Fluxo Principal (Mensagem Inbound)

```
Evolution Webhook -> webhook.py -> pipeline (pre) -> agente.py ->
policy.decide -> llm.generate -> tools -> pipeline (post) ->
outbound.send -> chips.sender -> WhatsApp Provider
```

## Fluxo Campanhas

```
Dashboard/Slack -> campanhas/executor -> segmentacao -> fila_mensagens ->
fila_worker -> guardrails -> chips/sender -> WhatsApp
```

## Fluxo Pipeline Grupos

```
Grupo WhatsApp -> group_entry -> ingestor -> fila_grupos ->
grupos_worker -> pipeline (heuristic -> llm -> extract -> normalize ->
dedup -> validate -> import) -> tabela vagas
```

## Metricas do Codebase

| Recurso | Quantidade |
|---------|------------|
| Arquivos Python | ~386 |
| Modulos de servico | ~268 |
| Tabelas no banco | 90+ |
| Testes | ~2662 |
| Routers API | 28 |
