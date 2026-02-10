# Visão Geral da Arquitetura do Sistema

Documento técnico completo que descreve a arquitetura de camada zero do Agente Júlia, uma solução de automação conversacional de staffing médico via WhatsApp, com supervisão humana, inteligência artificial distribuída e orquestração multi-canal.

**Data de Atualização:** 09/02/2026
**Status:** Versão 2.0 (Completa com Sprints 1-53)
**Manutentor:** Engenharia

---

## 1. Visão Geral Executiva

### Objetivo do Sistema

Implementar um agente de inteligência artificial autônomo que prospecta médicos, oferece plantões, gerencia relacionamentos e fecha vagas via WhatsApp, passando no teste de Turing (médicos não percebem que estão falando com uma IA).

### Contexto de Negócio Crítico

| Realidade | Implicação |
|-----------|-----------|
| Médicos saturados de mensagens de staffing | Qualidade >> quantidade |
| Todos são contatos frios | Debe parecer conversa genuína |
| Sem risco regulatório CFM | Usar contato automatizado com segurança |
| Único cliente (Revoluna) | Design monolítico, não multi-tenant |

### Métricas Chave do Projeto

| Métrica | Valor | Método |
|---------|-------|--------|
| Arquivos Python | 386 | `find app -name "*.py" \| wc -l` |
| Módulos de Serviço | 73+ | `ls app/services/` |
| Tabelas no Banco | 64+ | `mcp__supabase__list_tables` |
| Testes Automatizados | 2.550+ | `grep -r "def test_" tests/` |
| Routers API | 28 | `ls app/api/routes/` |
| Workers | 10 | `ls app/workers/` |
| Migrations Aplicadas | 93 | Supabase dashboard |
| Sprints Implementadas | 53 | planning/README.md |

---

## 2. Arquitetura Global

### 2.1 Diagrama de Arquitetura Completo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            MÉDICOS (WhatsApp)                              │
│                                                                              │
│  • Conversa com Júlia via Evolution ou Z-API                               │
│  • Grupos WhatsApp monitorados por extraction pipeline                     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
                ▼                  ▼                  ▼
┌──────────────────────────┐ ┌──────────────────┐ ┌────────────────────────┐
│  EVOLUTION API (Docker)  │ │  Z-API (HTTP)    │ │ WhatsApp Groups        │
│  Porta: 8080             │ │ Alternative      │ │ (Messages extraction)  │
│                          │ │ provider         │ │                        │
│  • Multi-device WhatsApp │ └──────────────────┘ │ + Discovery            │
│  • Webhook endpoint      │                      │   intelligence         │
│  • Message delivery      │                      └────────────────────────┘
└──────────────┬───────────┘
               │ POST /webhook/(evolution|zapi)
               │
               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI APP (Python 3.13+)                        │
│                          Porta: 8000                                       │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      WEBHOOK HANDLERS                                │ │
│  │                                                                       │ │
│  │  • app/api/routes/webhook.py (Evolution)                            │ │
│  │  • app/api/routes/webhook_zapi.py (Z-API)                          │ │
│  │  • app/api/routes/webhook_router.py (Router dispatcher)            │ │
│  │                                                                       │ │
│  │  Pipeline de Processamento:                                          │ │
│  │  1. Recebe e parseia payload                                        │ │
│  │  2. Detecta tipo (mensagem, status delivery, etc)                  │ │
│  │  3. Marca como lida + online                                        │ │
│  │  4. Valida opt-out                                                  │ │
│  │  5. Detecta trigger handoff                                         │ │
│  │  6. Verifica rate limit (Redis)                                     │ │
│  │  7. Valida horários comerciais                                      │ │
│  │  8. Executa pipeline de pré-processamento                          │ │
│  │  9. Chama agente LLM com tools                                     │ │
│  │  10. Executa pós-processamento                                      │ │
│  │  11. Calcula delay humanizado (45-180s)                            │ │
│  │  12. Mostra "digitando..." no WhatsApp                             │ │
│  │  13. Envia resposta em chunks (quebra em múltiplas)                │ │
│  │  14. Salva interação e emite business events                       │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    ROUTERS API (28 endpoints)                        │ │
│  │                                                                       │ │
│  │  Core:                          Operações:                          │ │
│  │  • health.py (liveness)         • jobs.py (cron handlers)           │ │
│  │  • test_db.py (connectivity)    • scheduler triggers                │ │
│  │  • sse.py (real-time events)    • sistema.py (status global)       │ │
│  │                                                                       │ │
│  │  Supervisão:                     Dashboards:                         │ │
│  │  • handoff.py                    • dashboard_conversations.py        │ │
│  │  • supervisor_channel.py         • metricas.py                       │ │
│  │  • chatwoot.py (sync)            • metricas_grupos.py               │ │
│  │                                                                       │ │
│  │  Campanhas & Vagas:               WhatsApp Multi-Chip:               │ │
│  │  • campanhas.py                  • warmer.py (aquecimento)          │ │
│  │  • guardrails.py (validação)     • chips_dashboard.py               │ │
│  │                                                                       │ │
│  │  Modo Operacional:                Discovery & Análise:               │ │
│  │  • piloto.py (pilot mode)        • extraction.py (LLM extraction)   │ │
│  │  • policy.py (decision engine)   • group_entry.py (monitoramento)   │ │
│  │                                                                       │ │
│  │  Debug:                           Integridades & Health:             │ │
│  │  • debug_llm.py                  • integridade.py (data checks)     │ │
│  │  • debug_whatsapp.py             • incidents.py (alertas)           │ │
│  │  • admin.py (operações)                                              │ │
│  │                                                                       │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    CORE ENGINES                                      │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │ LLM Orchestration (Hybrid Strategy)                          │   │ │
│  │  │ • Claude 3.5 Haiku (80% calls) - $0.25/1M tokens            │   │ │
│  │  │ • Claude 4 Sonnet (20% calls) - Complex negotiation         │   │ │
│  │  │ • Cost reduction: 73% vs single Sonnet                      │   │ │
│  │  │ • Prompt system: dynamic injection (Sprint 13 knowledge)    │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │ Pipeline de Processamento (Pluggable)                        │   │ │
│  │  │ • Pre-processors: detecção opt-out, bot, rate limit         │   │ │
│  │  │ • Core: LLM call com tools                                  │   │ │
│  │  │ • Post-processors: humanização, emissão de eventos          │   │ │
│  │  │ • Base abstrata em app/pipeline/base.py                    │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │ Agent Tools Registry (11 tools)                              │   │ │
│  │  │                                                               │   │ │
│  │  │ Vagas:                  Slack Integration:                  │   │ │
│  │  │ • buscar_vagas          • slack_tools (14 tools Helena)    │   │ │
│  │  │ • reservar_plantao      • helena/ (analytics agent)         │   │ │
│  │  │ • atualizar_preferencias                                     │   │ │
│  │  │                          Memória & Contexto:                 │   │ │
│  │  │ Follow-ups & Lembretes: • memoria.py (RAG, embeddings)    │   │ │
│  │  │ • agendar_lembrete      • intermediacao.py (bridge)         │   │ │
│  │  │ • enviar_lembrete       • response_formatter.py             │   │ │
│  │  │ • agenda_followup                                            │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │ Resilience & Control                                         │   │ │
│  │  │ • Rate Limiting: 20/hora, 100/dia via Redis                │   │ │
│  │  │ • Circuit Breaker: Claude, Evolution, Supabase, Chatwoot   │   │ │
│  │  │ • Retry Logic: exponential backoff + max attempts           │   │ │
│  │  │ • Distributed Lock: para operações críticas                 │   │ │
│  │  │ • Health Checks: dependências + custom metrics              │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │ Core Modules (app/core/)                                     │   │ │
│  │  │ • config.py: Environment + feature flags                    │   │ │
│  │  │ • logging.py: Structured JSON logging com contexto          │   │ │
│  │  │ • metrics.py: Prometheus-compatible metrics                 │   │ │
│  │  │ • exceptions.py: Exception hierarchy customizada             │   │ │
│  │  │ • decorators.py: async/await + timing helpers              │   │ │
│  │  │ • distributed_lock.py: Redis-based locking                 │   │ │
│  │  │ • prompts.py: Dynamic prompt management                     │   │ │
│  │  │ • tracing.py: Distributed tracing setup                    │   │ │
│  │  │ • timezone.py: BRT/timezone utilities                       │   │ │
│  │  │ • tasks.py: Background task dispatch                        │   │ │
│  │  │ • constants.py: Global constants                            │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │ Service Modules (73+ services em app/services/)             │   │ │
│  │  │ • Database: supabase.py (Supabase client + migrations)      │   │ │
│  │  │ • LLM: claude.py (API calls + response formatting)          │   │ │
│  │  │ • WhatsApp: evolution.py, zapi.py (message send/receive)    │   │ │
│  │  │ • Business: clientes.py, vagas.py, campanhas/, conversas.py│   │ │
│  │  │ • Analytics: metricas.py, deteccao_bot.py, avaliacao.py    │   │ │
│  │  │ • External: chatwoot.py, slack.py, google_docs.py           │   │ │
│  │  │ • Advanced: memoria.py (RAG), grupos.py (extraction)        │   │ │
│  │  │ • System: health.py, config_runtime.py                      │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    WORKERS (Processamento Background)                │ │
│  │                                                                       │ │
│  │  Scheduler (scheduler.py):                                          │ │
│  │  • Cron expressions para jobs periodicos                           │ │
│  │  • Report generation a cada 1h / 6h / 24h                          │ │
│  │  • Alertas de status (15min)                                        │ │
│  │  • Sincronizacao de briefing Google Docs (1h)                      │ │
│  │  • Limpeza de cache + métricas                                      │ │
│  │                                                                       │ │
│  │  Fila Worker (fila_worker.py):                                      │ │
│  │  • Processa fila_mensagens (messages queued)                        │ │
│  │  • Follow-ups agendados                                             │ │
│  │  • Lembretes automáticos                                            │ │
│  │  • Respects rate limits + business hours                            │ │
│  │                                                                       │ │
│  │  Grupos Worker (grupos_worker.py):                                  │ │
│  │  • Monitora grupos WhatsApp em tempo real                           │ │
│  │  • Dispara extraction pipeline (Sprint 52-53)                       │ │
│  │  • Discovery intelligence (mapping médicos)                          │ │
│  │  • Tracking de engajamento em grupos                                │ │
│  │                                                                       │ │
│  │  Handoff Processor (handoff_processor.py):                          │ │
│  │  • Verifica handoffs pendentes                                      │ │
│  │  • Sincroniza status com Chatwoot                                   │ │
│  │  • Notificacoes Slack para supervisores                             │ │
│  │  • Escalação automática de tickets                                  │ │
│  │                                                                       │ │
│  │  Pilot Mode (pilot_mode.py):                                        │ │
│  │  • Modo teste com grupo restrito de médicos                        │ │
│  │  • Metrics & feedback collection                                    │ │
│  │  • Antes de deploy em produção                                      │ │
│  │                                                                       │ │
│  │  Retomada Fora de Horário (retomada_fora_horario.py):              │ │
│  │  • Processa mensagens recebidas fora do horário comercial          │ │
│  │  • Re-enfilera com delay apropriado para próximo horário            │ │
│  │                                                                       │ │
│  │  Temperature Decay (temperature_decay.py):                          │ │
│  │  • Ajusta temperatura do LLM conforme histórico                    │ │
│  │  • Mais determinístico se padrões repetidos                        │ │
│  │  • Mais criativo se primeira vez conversando                        │ │
│  │                                                                       │ │
│  │  Backfill Extraction (backfill_extraction.py):                      │ │
│  │  • Extrai dados de conversas históricas                             │ │
│  │  • Treino de modelos de detecção + analytics                       │ │
│  │                                                                       │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  │
                ┌─────────────────┼──────────────────┬──────────────────┐
                │                 │                  │                  │
                ▼                 ▼                  ▼                  ▼
        ┌───────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
        │  SUPABASE DB  │ │    REDIS     │ │  CHATWOOT    │ │   SLACK + HELENA │
        │  PostgreSQL   │ │  Cache/Filas │ │  Supervisão  │ │  Analytics Agent │
        │ + pgvector    │ │              │ │              │ │  + Notificações  │
        │               │ │ • Rate limit │ │ • Handoff    │ │                  │
        │ • 64+ tabelas │ │ • Task queue │ │ • Histórico  │ │ • 5 tools pré-   │
        │ • 93+ migrate │ │ • Contexto   │ │ • Chat room  │ │   configuradas   │
        │ • RLS enabled │ │   session    │ │   sync       │ │ • SQL dinâmico   │
        │ • pgvector    │ │              │ │              │ │   (SELECT only)  │
        │   embeddings  │ └──────────────┘ └──────────────┘ └──────────────────┘
        └───────────────┘
                │
                ▼
        ┌──────────────────────────────────────────────┐
        │  Google Cloud Integration                   │
        │  • Google Docs (briefing automático)        │
        │  • Google Drive (templates de campanha)     │
        │  • Google Sheets (exports de relatórios)    │
        └──────────────────────────────────────────────┘
```

### 2.2 Subsistemas Principais

#### A. Agente Conversacional (Core)

**Propósito:** Processar mensagens de médicos em tempo real, gerar respostas inteligentes e gerenciar relacionamentos.

**Componentes:**
- Webhook handlers (Evolution + Z-API)
- Pipeline pluggável (pré/core/pós-processamento)
- LLM orchestration (Haiku 80% + Sonnet 20%)
- Tools registry (vagas, memória, lembretes, Slack)
- Resilience layer (rate limiting, circuit breaker, retry)

**Métricas:**
- Latência: < 30s (p95)
- Taxa sucesso: > 98%
- Detecção bot: < 1%

#### B. Sistema de Chips WhatsApp (Sprints 25-27, 40-41)

**Propósito:** Escalar para múltiplos números WhatsApp com warm-up inteligente e seleção de chip baseada em score.

**Fluxo:**
1. **Aquecimento (Julia Warmer):** Números novos recebem tráfego controlado antes de uso total
2. **Trust Score:** Baseado em delivery rate, engagement, complaint rate
3. **Seleção Automática:** Sistema escolhe chip ótimo para cada conversa
4. **Multi-instância:** Até N instâncias de Evolution/Z-API em paralelo

**Componentes:**
- warmer.py (processo de aquecimento)
- chips_dashboard.py (monitoring + manual override)
- julia_chips table (metadata de chips)
- chip_warmer_metrics (histórico de performance)

**Status:** Operacional com 5+ chips simultâneos

#### C. Pipeline de Grupos (Sprints 14, 51-53)

**Propósito:** Monitorar grupos WhatsApp e extrair inteligência (discovery, leads, análise de mercado).

**Fluxo:**
1. **Entrada:** Grupos mapeados em group_entry
2. **Monitoramento:** Grupos Worker coleta mensagens em tempo real
3. **Extração:** LLM extrai informações relevantes (quem é médico, que especialidade)
4. **Discovery Intelligence:** Identifica leads, oportunidades, trends
5. **Armazenamento:** Dados em grupos table + metricas_grupos

**Componentes:**
- grupos_worker.py (background processor)
- extraction.py (endpoint + orchestration)
- group_entry.py (webhook entry point)
- metricas_grupos.py (analytics + reporting)
- Discovery Intelligence (Sprint 53)

**Status:** Em operação com 12+ grupos monitorados

#### D. Dashboard Admin (Sprints 28, 33, 42-45)

**Propósito:** Interface web (Next.js + TypeScript) para supervisores gerenciarem operações.

**Funcionalidades:**
- Conversa management (visualizar, pesquisar, filtrar)
- Campanhas (criar, executar, pausar, analisar)
- Vagas (CRUD, disponibilidade)
- Chips (warm-up, seleção, métricas)
- Monitoramento (health, performance, alertas)
- Médicos (lookup, editar contexto, opt-out management)

**Localização:** `/dashboard` (separate Next.js app)

**Status:** Completo com navegação agrupada (6 seções semânticas)

#### E. Helena: Analytics Agent (Sprint 47)

**Propósito:** Agente IA no Slack para análise de dados e query SQL dinâmica (SELECT only).

**Características:**
- 5 tools pré-configuradas (metricas, status, handoffs, médicos, campanhas)
- SQL safe: apenas SELECT, LIMIT ≤ 100
- Session manager com TTL 30 min
- Confirmação antes de ações críticas
- Notificações removidas (dashboard substituiu)

**Localização:** `app/tools/helena/`

**Status:** Operacional, reduz carga de queries para humanos

#### F. Campaign Engine (Sprints 5, 35+)

**Propósito:** Criar e executar campanhas de prospecting com templates, segmentação, cooldown e atribuição.

**Fluxo:**
1. **Criação:** Template + segmento de médicos
2. **Agendamento:** Cron expression para envio
3. **Execução:** Fila respeita rate limits + horários
4. **Attribution:** Tracks conversions via business events
5. **Analytics:** Relatórios de taxa de resposta, conversão, ROI

**Componentes:**
- campanhas.py service (CRUD)
- campanha_repository + campanha_executor
- campanhas.py router (API endpoints)
- guardrails.py (validação de conteúdo)

**Status:** Operacional com 20+ campanhas executadas

#### G. Business Events & Policy Engine (Sprint 17, 15)

**Propósito:** Event sourcing para auditoria, automação e decisões baseadas em estado.

**Eventos (17+ tipos):**
- conversa_iniciada
- resposta_recebida
- vaga_reservada
- handoff_escalado
- opt_out_solicitado
- politica_violada
- etc.

**Policy Engine:** Automação condicional (se X então Y)

**Status:** 100+ eventos/hora em operação

#### H. Memory & RAG (Sprints 8, 13)

**Propósito:** Armazenar contexto longo prazo de médicos e fornecer conhecimento injetado no prompt.

**Tecnologia:**
- pgvector embeddings (Voyage AI)
- Chunks de conhecimento em docs/julia/
- Detecção de objeções (10 tipos)
- Detecção de perfil médico (7 perfis)
- Detecção de objetivo (8 tipos)

**Status:** 529 chunks indexados, accuracy 92%

---

## 3. Arquitetura Técnica Detalhada

### 3.1 Stack Tecnológico

| Camada | Tecnologia | Status | Notas |
|--------|-----------|--------|-------|
| **Linguagem** | Python 3.13+ | ✅ | async/await first |
| **Framework Web** | FastAPI | ✅ | Moderno, high-performance |
| **Package Manager** | uv (Astral) | ✅ | 2x mais rápido que pip |
| **ASGI Server** | Uvicorn | ✅ | Com gunicorn em produção |
| **Banco de Dados** | PostgreSQL (Supabase) | ✅ | pgvector + RLS |
| **Vector Search** | pgvector (1536 dims) | ✅ | Voyage AI embeddings |
| **LLM Principal** | Claude 3.5 Haiku | ✅ | $0.25/1M tokens |
| **LLM Complexo** | Claude 4 Sonnet | ✅ | Complex negotiation |
| **WhatsApp (Primary)** | Evolution API | ✅ | Self-hosted (Docker) |
| **WhatsApp (Alt)** | Z-API | ✅ | HTTP fallback |
| **Cache & Filas** | Redis | ✅ | Rate limit + background |
| **Supervision** | Chatwoot | ✅ | Human handoff |
| **Notificações** | Slack | ✅ | Helena agent |
| **Briefing** | Google Docs API | ✅ | Auto-sync |
| **Números Virtuais** | Salvy | ✅ | VPS integration |
| **Deploy** | Railway | ✅ | 3 services (api/worker/scheduler) |
| **Dashboard** | Next.js + TypeScript | ✅ | Separate repo |
| **Testing** | pytest + pytest-asyncio | ✅ | 2.550+ tests |
| **Logging** | Structured JSON | ✅ | app/core/logging.py |
| **Monitoring** | Custom metrics | 🔶 | OpenTelemetry planned |

### 3.2 Estrutura de Diretórios

```
whatsapp-api/
├── app/                          # Aplicação principal
│   ├── main.py                   # FastAPI app factory
│   │
│   ├── api/routes/               # 28 routers API
│   │   ├── webhook.py            # Evolution entrada principal
│   │   ├── webhook_zapi.py       # Z-API fallback
│   │   ├── webhook_router.py     # Dispatcher
│   │   ├── health.py             # Liveness + readiness
│   │   ├── sse.py                # Server-sent events
│   │   ├── jobs.py               # Cron trigger endpoints
│   │   ├── metricas.py           # Analytics
│   │   ├── metricas_grupos.py    # Group analytics
│   │   ├── campanhas.py          # Campaign CRUD
│   │   ├── guardrails.py         # Content validation
│   │   ├── warmer.py             # Chip warm-up
│   │   ├── chips_dashboard.py    # Chip monitoring
│   │   ├── extraction.py         # Group message extraction
│   │   ├── group_entry.py        # Group webhook entry
│   │   ├── piloto.py             # Pilot mode management
│   │   ├── policy.py             # Policy engine
│   │   ├── handoff.py            # Handoff management
│   │   ├── supervisor_channel.py # Supervisor commands
│   │   ├── chatwoot.py           # Chatwoot sync
│   │   ├── dashboard_conversations.py  # Conversation API
│   │   ├── integridade.py        # Data integrity checks
│   │   ├── incidents.py          # Alert management
│   │   ├── sistema.py            # System endpoints
│   │   ├── admin.py              # Admin operations
│   │   ├── debug_llm.py          # LLM debugging
│   │   ├── debug_whatsapp.py     # WhatsApp debugging
│   │   └── test_db.py            # Connectivity tests
│   │
│   ├── services/                 # 73+ service modules
│   │   ├── supabase.py           # DB client + migrations
│   │   ├── claude.py             # LLM API wrapper
│   │   ├── evolution.py          # Evolution API client
│   │   ├── zapi.py               # Z-API client
│   │   ├── chatwoot.py           # Chatwoot API client
│   │   ├── slack.py              # Slack webhook client
│   │   ├── google_docs.py        # Google Docs integration
│   │   │
│   │   ├── clientes.py           # Doctor management
│   │   ├── conversas.py          # Conversation CRUD
│   │   ├── interacoes.py         # Interaction logging
│   │   ├── vagas.py              # Shift management
│   │   ├── campanhas/            # Campaign submodule
│   │   │   ├── __init__.py
│   │   │   ├── campanha_repository.py
│   │   │   ├── campanha_executor.py
│   │   │   ├── segmentacao.py
│   │   │   ├── templates.py
│   │   │   └── types.py
│   │   │
│   │   ├── memoria.py            # RAG + embeddings
│   │   ├── grupos.py             # Group management
│   │   ├── metricas.py           # Analytics compute
│   │   ├── deteccao_bot.py       # Bot detection (37 padrões)
│   │   ├── avaliacao_qualidade.py # Quality metrics
│   │   ├── health.py             # Health checks
│   │   │
│   │   ├── salvy.py              # Virtual numbers (VPS)
│   │   ├── policy_engine.py      # Policy/rule evaluation
│   │   └── [outros serviços]     # ~40+ mais
│   │
│   ├── pipeline/                 # Processamento pluggável
│   │   ├── base.py               # Abstract base classes
│   │   ├── core.py               # Main pipeline orchestrator
│   │   ├── processor.py          # Processor interface
│   │   ├── pre_processors.py     # Validação/detecção
│   │   ├── post_processors.py    # Humanização/eventos
│   │   ├── setup.py              # Pipeline bootstrap
│   │   └── processors/           # Implementações concretas
│   │
│   ├── tools/                    # Agent tools
│   │   ├── registry.py           # Tool dispatcher
│   │   ├── vagas.py              # Shift tools
│   │   ├── memoria.py            # Memory tools
│   │   ├── lembrete.py           # Reminder tools
│   │   ├── intermediacao.py      # Mediation tools
│   │   ├── response_formatter.py # Response formatting
│   │   ├── slack/                # Slack tools for humans
│   │   │   ├── __init__.py
│   │   │   ├── tools.py
│   │   │   └── types.py
│   │   ├── slack_tools.py        # Slack dispatcher
│   │   ├── helena/               # Helena agent
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── tools.py
│   │   │   ├── sql_validator.py
│   │   │   └── session_manager.py
│   │   └── __init__.py
│   │
│   ├── workers/                  # Background processing
│   │   ├── __main__.py           # Worker entry point
│   │   ├── __init__.py
│   │   ├── scheduler.py          # Cron job orchestrator
│   │   ├── fila_worker.py        # Message queue processor
│   │   ├── grupos_worker.py      # Group monitor
│   │   ├── handoff_processor.py  # Handoff lifecycle
│   │   ├── pilot_mode.py         # Test mode processor
│   │   ├── retomada_fora_horario.py  # Off-hours processor
│   │   ├── temperature_decay.py  # LLM temp adjustment
│   │   └── backfill_extraction.py # Historical data extraction
│   │
│   ├── core/                     # System core modules
│   │   ├── config.py             # Environment + feature flags
│   │   ├── constants.py          # Global constants
│   │   ├── decorators.py         # Helper decorators
│   │   ├── distributed_lock.py   # Redis locks
│   │   ├── exceptions.py         # Exception hierarchy
│   │   ├── logging.py            # JSON structured logging
│   │   ├── metrics.py            # Custom metrics
│   │   ├── prompts.py            # Prompt templates
│   │   ├── timezone.py           # BRT utilities
│   │   ├── tracing.py            # Distributed tracing
│   │   ├── tasks.py              # Background task dispatch
│   │   ├── utils.py              # Utility functions
│   │   └── piloto_config.py      # Pilot mode settings
│   │
│   └── CONVENTIONS.md            # Code style guide
│
├── tests/                        # 2.550+ tests
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── conftest.py
│
├── docs/                         # Documentação técnica
│   ├── arquitetura/              # Architecture docs
│   │   ├── visao-geral.md        # Este arquivo
│   │   ├── banco-de-dados.md     # Schema + ER
│   │   ├── endpoints-api.md      # API specifications
│   │   ├── fluxos-dados.md       # Data flow diagrams
│   │   ├── navegacao-dashboard.md # Dashboard navigation
│   │   └── servicios.md          # Service layer guide
│   │
│   ├── setup/                    # Configuração
│   │   ├── instalacao.md         # Development setup
│   │   ├── variavel-ambiente.md  # .env template
│   │   └── producao.md           # Production checklist
│   │
│   ├── operacao/                 # Runbooks
│   │   ├── playbook-handoff.md   # Handoff procedures
│   │   ├── playbook-campanha.md  # Campaign execution
│   │   ├── playbook-incidente.md # Incident response
│   │   └── teste-manual.md       # Manual test guide
│   │
│   ├── integracoes/              # External APIs
│   │   ├── evolution-api-quickref.md
│   │   ├── chatwoot-api-quickref.md
│   │   ├── railway-quickref.md
│   │   ├── railroad-deploy.md
│   │   ├── salvy-quickref.md
│   │   └── README.md
│   │
│   ├── julia/                    # Persona + knowledge
│   │   ├── persona.md            # Júlia character
│   │   ├── prompts/              # Prompt templates
│   │   ├── conhecimento/         # RAG knowledge base
│   │   └── deteccoes.md          # Detectors guide
│   │
│   ├── auditorias/               # Reports
│   │   ├── auditoria-arquitetura.md
│   │   └── audit-*.md
│   │
│   ├── best-practices/           # Guidelines
│   │   └── nextjs-typescript-rules.md
│   │
│   ├── templates/                # Campaign templates
│   └── archive/                  # Obsolete docs
│
├── planning/                     # Sprint planning
│   ├── sprint-*/                 # Sprint 1 through 53
│   ├── epicos/
│   └── README.md                 # Roadmap
│
├── dashboard/                    # Next.js admin app
│   ├── app/
│   ├── components/
│   ├── public/
│   ├── lib/
│   ├── styles/
│   ├── package.json
│   └── [Next.js config]
│
├── docker-compose.yml            # Local services
├── pyproject.toml                # Python dependencies
├── pytest.ini
├── .env.example
├── .gitignore
└── CLAUDE.md                     # AI instructions
```

### 3.3 Fluxos de Dados Críticos

#### Fluxo 1: Mensagem Recebida → Resposta Enviada

```
┌─────────────────────┐
│  Médico no WhatsApp │ Envia: "Oi Júlia, tem vaga?"
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│ Evolution API (Docker :8080)                         │
│ Recebe via WhatsApp, forma payload webhook          │
└──────────┬───────────────────────────────────────────┘
           │
           ▼ POST /webhook/evolution
┌──────────────────────────────────────────────────────┐
│ FastAPI Webhook Handler (webhook.py)                │
│ 1. Parseia payload (validar schema)                  │
│ 2. Extrai: medico_id, mensagem, timestamp            │
│ 3. Retorna 200 OK (não bloqueia)                     │
└──────────┬───────────────────────────────────────────┘
           │
           ▼ (background task)
┌──────────────────────────────────────────────────────┐
│ Pipeline de Processamento                            │
│                                                       │
│ PRE-PROCESSORS:                                      │
│ ├─ Validação mensagem (vazio? media?)               │
│ ├─ Buscar conversa + histórico (DB)                 │
│ ├─ Detecção opt-out (blacklist)                     │
│ ├─ Detecção bot (37 padrões)                        │
│ ├─ Trigger handoff (irritação? pedido humano?)     │
│ └─ Rate limit (Redis check: 20/h, 100/d)           │
│                                                       │
│ Se bloqueado → Return early, salva interação        │
│                                                       │
│ CORE PROCESSOR (LLM):                                │
│ ├─ Buscar contexto médico + memória (RAG)           │
│ ├─ Injetar conhecimento dinâmico (Sprint 13)        │
│ ├─ Chamar Claude API (Haiku 80% ou Sonnet 20%)     │
│ ├─ Claude retorna mensagem + tool_use               │
│ ├─ Se tool: executar (buscar_vagas, agendar, etc)   │
│ ├─ Repetir até resposta final                       │
│ └─ Salvar consumo de tokens                          │
│                                                       │
│ POST-PROCESSORS:                                     │
│ ├─ Quebrar mensagem em chunks (2.000 chars)         │
│ ├─ Validar conteúdo (guardrails)                    │
│ ├─ Calcular delay humanizado (45-180s aleatório)    │
│ ├─ Gerar business event (interação_processada)      │
│ └─ Emitir para policy engine                        │
└──────────┬───────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│ Envio de Resposta                                    │
│ 1. Marcar "digitando..." por X segundos             │
│ 2. Aguardar delay humanizado                        │
│ 3. Enviar cada chunk para Evolution API             │
│ 4. Evolution entrega no WhatsApp                     │
│ 5. Tracking: status delivery (enviado/entregue/lido)│
└──────────┬───────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│ Persistência & Analytics                             │
│ 1. Salvar interação (conversas + interacoes tables) │
│ 2. Atualizar medical context + memória (RAG)        │
│ 3. Emitir business events (auditoria)               │
│ 4. Registrar métricas (latência, custo LLM)         │
│ 5. Notificar Slack se triggers (handoff, erro)      │
└──────────────────────────────────────────────────────┘
```

#### Fluxo 2: Campaign Execution

```
┌─────────────────────────────────────┐
│ Supervisor cria campanha via       │
│ Dashboard ou API /campanhas/create   │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│ Validação (guardrails.py)                           │
│ ├─ Conteúdo não viola policies                     │
│ ├─ Segmento válido (médicos existem)               │
│ ├─ Template dentro de cooldown                      │
│ └─ Horário permitido (08h-20h, Seg-Sex)            │
└──────────┬──────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│ Agendamento (scheduler.py)                          │
│ ├─ Cria entrada em fila_mensagens                  │
│ ├─ Define timestamp de envio (respeita cooldown)   │
│ ├─ Associa campaign_id para tracking                │
│ └─ Next check: próximo slot disponível              │
└──────────┬──────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│ Fila Worker (fila_worker.py)                        │
│ Processa a cada 10s:                                │
│                                                      │
│ LOOP:                                                │
│ 1. Buscar mensagens com timestamp ≤ agora          │
│ 2. Para cada: verificar rate limit (20/h, 100/d)   │
│ 3. Se OK: enviar via Evolution                      │
│ 4. Se rate limit: re-enfilerar com delay           │
│ 5. Se fora de horário: retomada_fora_horario.py    │
│ 6. Registrar delivery status                        │
│ 7. Emitir business_events para attribution         │
└──────────┬──────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│ Attribution & Analytics                             │
│ 1. Webhook chegou resposta? (conversas table)       │
│ 2. Timeline: quando respondeu?                       │
│ 3. Resultado: interesse? reserva? opt-out?         │
│ 4. Agregação: taxa de resposta, conversão, ROI      │
│ 5. Relatório no Dashboard                            │
└──────────────────────────────────────────────────────┘
```

#### Fluxo 3: Handoff IA → Humano

```
┌────────────────────────────────┐
│ Trigger Detectado              │
│ ├─ Médico: "Quero falar com  │
│ │            um humano"         │
│ ├─ Ou: muito irritado           │
│ ├─ Ou: assunto complexo        │
│ └─ Ou: confiança baixa         │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────┐
│ Agente Julia (pipeline.py)                         │
│ 1. Detecta trigger no pós-processamento             │
│ 2. Gera resposta: "Vou pedir ajuda para            │
│                   minha supervisora"                │
└──────────┬─────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────┐
│ Database Update                                    │
│ UPDATE conversations SET controlled_by = 'human'  │
│ WHERE id = {conversa_id}                           │
└──────────┬─────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────┐
│ Chatwoot Sync (chatwoot.py service)                │
│ 1. Criar ticket em Chatwoot                        │
│ 2. Marcar como "escalado de IA"                    │
│ 3. Atribuir a supervisor (round-robin ou skill)    │
│ 4. Sincronizar histórico de conversa              │
└──────────┬─────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────┐
│ Notificação Slack                                  │
│ 1. Mensagem em #handoffs channel                   │
│ 2. Menciona supervisor atribuído                   │
│ 3. Link para Chatwoot conversation                 │
│ 4. Contexto: por que foi escalado                  │
└──────────┬─────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────┐
│ Supervisor no Chatwoot/Slack                       │
│ 1. Assume conversa via Chatwoot                    │
│ 2. Julia para de responder (controlled_by=human)   │
│ 3. Supervisor responde via Chatwoot UI             │
│ 4. Médico recebe via WhatsApp                      │
└──────────┬─────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────┐
│ Resolução                                          │
│ 1. Supervisor resolve ticket em Chatwoot           │
│ 2. Automaticamente: controlled_by volta para 'ai'  │
│ 3. Julia volta a responder se médico mandar msg   │
│ 4. Logging para auditoria                          │
└────────────────────────────────────────────────────┘
```

### 3.4 Modelo de Dados (64+ tabelas)

#### Categorias Principais

| Categoria | Qtd | Tabelas Chave | Propósito |
|-----------|-----|---------------|-----------|
| **Core do Agente** | 10 | clientes, conversations, interacoes, handoffs, doctor_context | Kernel conversacional |
| **Gestão de Vagas** | 10 | vagas, hospitais, especialidades, setores, periodos, tipos_vaga | Inventory de oportunidades |
| **Campanhas** | 8 | campanhas, envios, execucoes_campanhas, metricas_campanhas | Prospecting em massa |
| **Gestão Júlia** | 12 | diretrizes, prompts, julia_status, briefing_config, slack_sessoes | Orquestração + persona |
| **Business Events** | 8 | business_events, event_metrics, kpis, alerts | Auditoria + automação |
| **Chips/Warmer** | 8 | julia_chips, chip_warmer_metrics, salvy_accounts, whatsapp_instances | Multi-número WhatsApp |
| **Analytics** | 10 | metricas_conversa, avaliacoes_qualidade, metricas_deteccao_bot, grupos_metricas | BI + monitoring |
| **Infraestrutura** | 8 | notificacoes_gestor, slack_comandos, distributed_locks, sessions | Sistema operacional |
| **Migrations/Views** | 12 | Views materializadas, tabelas de auditoria | Histórico + reports |

**Detalhe completo:** `docs/arquitetura/banco-de-dados.md`

### 3.5 Padrões de Resiliência

#### Rate Limiting (Redis)

```python
MAX_MSGS_POR_HORA = 20          # Por médico
MAX_MSGS_POR_DIA = 100          # Por médico
INTERVALO_MIN = 45              # Segundos entre msgs
INTERVALO_MAX = 180             # Randomizado (parecer humano)
HORARIO_INICIO = "08:00"        # BRT
HORARIO_FIM = "20:00"           # BRT
DIAS_PERMITIDOS = [0,1,2,3,4]   # Seg-Sex
```

**Implementação:** `app/core/constants.py` + Redis lua scripts

#### Circuit Breaker

Protege contra cascata de falhas:

```
CLOSED (normal)
  ↓ (threshold de erros atingido)
OPEN (bloqueia por X segundos)
  ↓ (timeout expirou)
HALF_OPEN (testa recuperação)
  ↓ (sucesso ou falha)
CLOSED ou OPEN
```

**Circuitos:**
- claude_circuit (Anthropic API)
- evolution_circuit (Evolution API)
- supabase_circuit (Banco de dados)
- chatwoot_circuit (Chatwoot)

#### Retry Logic

```
tentativa 1: imediato
tentativa 2: + 2s (2^1)
tentativa 3: + 4s (2^2)
tentativa 4: + 8s (2^3)
tentativa 5: + jitter aleatório
max attempts: 5
```

#### Distributed Lock

Para operações críticas (não race conditions):

```python
async with DistributedLock(f"campanha:{campaign_id}", ttl=30):
    # Seção crítica protegida
    execute_campaign_chunk()
```

---

## 4. Segurança & Conformidade

### 4.1 RLS (Row Level Security)

Todas as 64+ tabelas possuem políticas RLS ativas:

```sql
-- Padrão: acesso via service_role
CREATE POLICY "Acesso via service key"
ON public.clientes
FOR ALL
USING (auth.role() = 'service_role');
```

**Auditoria:** `docs/auditorias/auditoria-arquitetura.md`

### 4.2 Secrets Management

Nunca commitadas, armazenadas apenas em `.env`:

- `SUPABASE_SERVICE_KEY` - DB access
- `ANTHROPIC_API_KEY` - LLM calls
- `EVOLUTION_API_KEY` - WhatsApp primary
- `ZAPI_API_KEY` - WhatsApp fallback
- `CHATWOOT_API_KEY` - Supervisor sync
- `SLACK_WEBHOOK_URL` - Notifications
- `GOOGLE_DOCS_API_KEY` - Briefing sync
- `REDIS_URL` - Cache + filas
- `SALVY_API_KEY` - Virtual numbers

**Setup:** `docs/setup/variavel-ambiente.md`

### 4.3 Input Validation

```python
# Todos os inputs hostis (browser, webhook, app)
from pydantic import BaseModel, Field, validator

class MensagemRequest(BaseModel):
    medico_id: uuid.UUID
    texto: str = Field(..., max_length=5000)

    @validator('texto')
    def nao_vazio(cls, v):
        if not v.strip():
            raise ValueError('Mensagem vazia')
        return v.strip()
```

---

## 5. Observabilidade & Monitoring

### 5.1 Health Checks

```bash
GET /health                 # Liveness (app running)
GET /health/ready           # Readiness (deps available)
GET /health/circuit         # Circuit breaker status
GET /health/rate            # Rate limit status
```

### 5.2 Logging Estruturado

```json
{
  "timestamp": "2026-02-09T15:30:45.123Z",
  "level": "INFO",
  "logger": "app.pipeline",
  "message": "Mensagem processada com sucesso",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "medico_id": "uuid-do-medico",
  "conversa_id": "uuid-da-conversa",
  "latencia_ms": 1234,
  "tokens_input": 512,
  "tokens_output": 128,
  "modelo_lhm": "claude-3-5-haiku-20241022"
}
```

**Configuração:** `app/core/logging.py`

### 5.3 Métricas Customizadas

- Tempo de resposta (p50, p95, p99)
- Taxa de sucesso (%)
- Contagem de handoffs
- Taxa detecção bot (%)
- Uso de tokens LLM
- Erros por tipo
- Throughput (msgs/min)

**Coleta:** `app/core/metrics.py`

### 5.4 Alertas Automáticos

Canais Slack:
- `#alerts-criticos`: erros, circuit breaker aberto
- `#alerts-normais`: handoffs, campanhas completas
- `#anomalias`: padrões detectados

---

## 6. Escalabilidade & Performance

### 6.1 Escalabilidade Horizontal

**API (Stateless):**
- N instâncias FastAPI (Railway auto-scaling)
- Load balancer na frente
- Session stored em Redis

**Workers:**
- Scheduler: 1 por ambiente (master election)
- Fila Worker: N instâncias (queue dispatcher)
- Grupos Worker: N instâncias (sharding por grupo_id)

**Banco de Dados:**
- Supabase (managed PostgreSQL, auto-scaling)
- Connection pooling (pgBouncer)
- Índices estratégicos em FK + search columns

### 6.2 Escalabilidade Vertical

**Otimizações:**
- LLM calls: gargalo principal
  - Cache de contexto (Redis)
  - Batch processing (10 msgs por batch)
  - Hybrid Haiku (80%) vs Sonnet (20%) = 73% redução de custo

**Database:**
- Indexed queries (sempre usar índices)
- Prepared statements (prevent SQL injection)
- Connection pooling

### 6.3 Benchmarks

| Operação | Latência p95 | Throughput |
|----------|--------------|------------|
| Message process | 2-5s | 100 msgs/min |
| LLM call | 0.5-2s | Limited by rate |
| DB query | 50-200ms | 1.000+ QPS |
| Circuit breaker | < 1ms | N/A |
| Rate limit check | 10-50ms | 10.000+ checks/min |

---

## 7. Deployment & Operação

### 7.1 Arquitetura de Deploy (Railway)

**3 Services:**

1. **API Service** (`whats-agents`)
   - FastAPI app (webhook handlers + routers)
   - Auto-scaling based on CPU/memory
   - Environment: production
   - Health check: GET /health/ready

2. **Worker Service** (`whats-workers`)
   - Background job processors
   - Single instance (scheduler master)
   - Runs: scheduler.py + fila_worker.py + grupos_worker.py
   - Cron: via internal scheduler

3. **Scheduler Service** (opcional, separado)
   - Pure cron orchestration
   - Calls API /jobs/{endpoint}
   - Fallback: scheduler.py em worker

**Database:**
- Supabase (managed)
- Connection string via `DATABASE_URL`

**Cache:**
- Redis (managed ou self-hosted)
- URL via `REDIS_URL`

### 7.2 CI/CD Pipeline

**GitHub Actions:**
- Lint + format (Black, isort, flake8)
- Type checking (mypy)
- Tests (pytest, coverage > 70%)
- Security scan (bandit, safety)
- Build Docker image
- Deploy (Railway git integration)

**Branches:**
- `main` → Production auto-deploy
- `develop` → Staging
- `feature/*` → PR checks

---

## 8. Decisões Arquiteturais Chave

### D1: Hybrid LLM Strategy (80/20 Haiku/Sonnet)

**Decisão:** 80% das calls via Haiku ($0.25/1M), 20% via Sonnet (complexo)

**Justificativa:**
- Haiku: rápido, barato, suficiente para prospecção
- Sonnet: qualidade superior para negociação/objeção
- Resultado: 73% economia vs full Sonnet

**Trade-offs:**
- + : Custo 73% menor
- + : Latência mais rápida (Haiku)
- - : Qualidade média em 80% dos casos
- Mitigação: custom prompts + detecção de complexidade

### D2: Self-Hosted Evolution API

**Decisão:** Docker local vs Evolution SaaS

**Justificativa:**
- Controle total de números/devices
- Múltiplos números simultâneos (chips system)
- API customizável
- Fallback para Z-API

**Trade-offs:**
- + : Controle total
- + : Suporta múltiplos números
- - : DevOps overhead
- Mitigação: docker-compose.yml para setup

### D3: Pipeline Pluggável

**Decisão:** Pre/core/post processors vs monolithic

**Justificativa:**
- Adicionar lógica sem modificar core
- Composição de features
- Testabilidade

**Implementação:** `app/pipeline/base.py` (abstract)

### D4: Business Events

**Decisão:** Event sourcing pattern

**Justificativa:**
- Auditoria completa
- Automação condicional (policy engine)
- Attribution (campaigns)
- Analytics

### D5: Postgres pgvector (não Pinecone)

**Decisão:** Embeddings no mesmo banco (pgvector)

**Justificativa:**
- Custo: sem SaaS externo
- Simplicidade: 1 conexão DB
- Latência: query local
- Trade-off: scaling vs monolith

---

## 9. Monitoramento de Produção

### 9.1 SLOs (Service Level Objectives)

| SLO | Target | Current | Status |
|-----|--------|---------|--------|
| Availability | 99.5% | 99.8% | ✅ |
| Latency p95 | 5s | 2-3s | ✅ |
| Error rate | < 1% | 0.2% | ✅ |
| Bot detection | < 1% | 0.5% | ✅ |

### 9.2 Alertas Críticos

Slack #alerts-criticos dispara se:
- Response time p95 > 10s
- Error rate > 2%
- Circuit breaker OPEN
- Database latency > 2s
- Redis unavailable
- Out of memory
- Handoff queue > 100

### 9.3 Dashboards

- **Live Dashboard:** `http://railway-api-prod.railwayapp.io/metrics`
- **BI Dashboard:** Dashboard app (Next.js)
- **Slack Dashboard:** Helena agent + custom reports

---

## 10. Roadmap Futuro

### Em Consideração

1. **OpenTelemetry** - Distributed tracing + Grafana
2. **LLM Fine-tuning** - Custom model para Júlia
3. **Multi-Tenant** - Suporte para múltiplas agências
4. **Voice WhatsApp** - Audio messages + transcription
5. **Payment Integration** - Checkout direto via WhatsApp
6. **Advanced RAG** - Hybrid search (dense + sparse)
7. **Agents Colaborativos** - Júlia + Helena + novos
8. **Kubernetes** - Migration de Railway para K8s

---

## 11. Referências & Recursos

### Documentação Técnica

| Documento | Localização | Propósito |
|-----------|------------|-----------|
| Bank Schema | `docs/arquitetura/banco-de-dados.md` | Detalhes de tabelas |
| API Endpoints | `docs/arquitetura/endpoints-api.md` | Especificação de routers |
| Data Flows | `docs/arquitetura/fluxos-dados.md` | Diagramas de dados |
| Services Guide | `docs/arquitetura/servicios.md` | Módulos de serviço |
| Navigation | `docs/arquitetura/navegacao-dashboard.md` | Dashboard structure |

### Setup & Deployment

| Documento | Localização | Propósito |
|-----------|------------|-----------|
| Development Setup | `docs/setup/instalacao.md` | Local environment |
| Environment Vars | `docs/setup/variavel-ambiente.md` | .env template |
| Production Deploy | `docs/setup/producao.md` | Railway checklist |

### Integrações Externas

| Integração | Quick Ref | Status |
|------------|-----------|--------|
| Evolution API | `docs/integracoes/evolution-api-quickref.md` | ✅ |
| Chatwoot | `docs/integracoes/chatwoot-api-quickref.md` | ✅ |
| Railway | `docs/integracoes/railway-quickref.md` | ✅ |
| Salvy | `docs/integracoes/salvy-quickref.md` | ✅ |
| Google Docs | `docs/julia/conhecimento/` | ✅ |

### Conventions & Best Practices

| Documento | Localização |
|-----------|------------|
| Code Conventions | `app/CONVENTIONS.md` |
| Next.js Rules | `docs/best-practices/nextjs-typescript-rules.md` |

### Histórico de Sprints

| Detalhe | Localização |
|---------|------------|
| Sprint Planning | `planning/sprint-*/` |
| Roadmap | `planning/README.md` |
| Épicos | `planning/epicos/` |

---

## Apêndice: Glossário de Termos

| Termo | Definição |
|-------|-----------|
| **Júlia** | Agente de IA que prospecta médicos via WhatsApp |
| **Médico/Cliente** | Profissional de saúde alvo de prospecting |
| **Escalista** | Pessoa responsável por alocar médicos em plantões |
| **Vaga/Plantão** | Oportunidade de trabalho (turno em hospital) |
| **Campanha** | Batch de mensagens proativas para segmento |
| **Handoff** | Passagem de conversa de IA para humano |
| **Chips** | Múltiplos números WhatsApp (instâncias) |
| **Warmer** | Processo de aquecimento de número novo |
| **RAG** | Retrieval-Augmented Generation (memória + embeddings) |
| **Pipeline** | Processamento modular (pré/core/pós) |
| **Business Event** | Evento registrado para auditoria/automação |
| **Policy Engine** | Automação condicional (se X então Y) |
| **Circuit Breaker** | Padrão de resiliência (falha rápido) |
| **Rate Limiting** | Controle de throughput (msgs/hora) |
| **Bot Detection** | Identificação de conversa com bot (37 padrões) |
| **Detecção de Objeção** | Identificação de objeção (10 tipos) |
| **Detecção de Perfil** | Identificação de tipo de médico (7 perfis) |
| **Distributed Lock** | Sincronização distribuída via Redis |
| **pgvector** | Extensão PostgreSQL para embeddings |
| **Voyage AI** | Provider de embeddings (1536 dims) |

---

**Documento:** visao-geral.md
**Versão:** 2.0
**Data:** 09/02/2026
**Próxima Review:** 30/03/2026
