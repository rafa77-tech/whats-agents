# Arquitetura do Sistema

> Visao geral da arquitetura tecnica do Agente Julia

---

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MEDICOS (WhatsApp)                          │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EVOLUTION API (Docker)                          │
│                      Porta: 8080                                     │
│   • Multi-device WhatsApp                                           │
│   • Webhook para mensagens recebidas                                │
│   • API para envio de mensagens                                     │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ POST /webhook/evolution
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI APP (Python)                           │
│                      Porta: 8000                                     │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    WEBHOOK HANDLER                              │ │
│  │  app/api/routes/webhook.py                                      │ │
│  │                                                                  │ │
│  │  1. Recebe mensagem                                              │ │
│  │  2. Parseia payload                                              │ │
│  │  3. Marca como lida + "online"                                   │ │
│  │  4. Detecta opt-out                                              │ │
│  │  5. Detecta trigger de handoff                                   │ │
│  │  6. Verifica rate limit                                          │ │
│  │  7. Chama LLM (com tools)                                        │ │
│  │  8. Calcula delay humanizado                                     │ │
│  │  9. Mostra "digitando..."                                        │ │
│  │  10. Envia resposta                                              │ │
│  │  11. Salva interacao                                             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   AGENTE    │  │    LLM      │  │   TOOLS     │  │  HANDOFF    │ │
│  │  Orquestra  │  │   Claude    │  │  buscar_    │  │  Escala p/  │ │
│  │  pipeline   │  │   API       │  │  vagas      │  │  humano     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ RATE LIMIT  │  │  CIRCUIT    │  │  TIMING     │  │  DETECCAO   │ │
│  │  Redis      │  │  BREAKER    │  │  Humaniza   │  │  BOT/OPTOUT │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    SUPABASE     │  │     REDIS       │  │    CHATWOOT     │
│   PostgreSQL    │  │   Cache/Filas   │  │   Supervisao    │
│   + pgvector    │  │                 │  │   Humana        │
│                 │  │  • Rate limits  │  │                 │
│  • 32 tabelas   │  │  • Filas msg    │  │  • Handoff      │
│  • RLS ativo    │  │  • Contexto     │  │  • Historico    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │
          ▼
┌─────────────────┐
│     SLACK       │
│  Notificacoes   │
│                 │
│  • Alertas      │
│  • Reports      │
│  • Handoffs     │
└─────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      WORKERS (Processos Separados)                   │
│                                                                      │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐   │
│  │     SCHEDULER               │  │     FILA WORKER             │   │
│  │  app/workers/scheduler.py   │  │  app/workers/fila_worker.py │   │
│  │                             │  │                             │   │
│  │  Cron jobs:                 │  │  Processa:                  │   │
│  │  • Reports periodicos       │  │  • Mensagens agendadas      │   │
│  │  • Alertas (15min)          │  │  • Follow-ups               │   │
│  │  • Followups (10h)          │  │  • Lembretes                │   │
│  │  • Briefing sync (1h)       │  │                             │   │
│  └─────────────────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Componentes Principais

### 1. FastAPI App (`app/main.py`)

Aplicacao principal que recebe webhooks e expoe endpoints.

```python
# Routers registrados
app.include_router(health.router)      # /health
app.include_router(webhook.router)     # /webhook
app.include_router(jobs.router)        # /jobs
app.include_router(admin.router)       # /admin
app.include_router(metricas.router)    # /metricas
app.include_router(campanhas.router)   # /campanhas
app.include_router(piloto.router)      # /piloto
app.include_router(chatwoot.router)    # /chatwoot
```

### 2. Pipeline de Processamento

Quando uma mensagem chega via webhook:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   RECEBER    │────▶│    PARSE     │────▶│   VALIDAR    │
│   Webhook    │     │   Payload    │     │   Mensagem   │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   OPT-OUT?   │◀────│   MEDICO     │◀────│   BUSCAR     │
│   Verificar  │     │   Contexto   │     │   Conversa   │
└──────────────┘     └──────────────┘     └──────────────┘
       │
       ▼ Nao
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   HANDOFF?   │────▶│  RATE LIMIT  │────▶│     LLM      │
│   Verificar  │     │   Verificar  │     │   + Tools    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   QUEBRAR    │◀────│   HUMANIZAR  │◀────│   RESPOSTA   │
│   Mensagem   │     │   Delay      │     │   Gerada     │
└──────────────┘     └──────────────┘     └──────────────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│    ENVIAR    │────▶│    SALVAR    │
│   WhatsApp   │     │   Interacao  │
└──────────────┘     └──────────────┘
```

### 3. Sistema de Tools (Agente)

Julia pode usar ferramentas durante a conversa:

| Tool | Descricao | Arquivo |
|------|-----------|---------|
| `buscar_vagas` | Busca plantoes compativeis | `app/tools/vagas.py` |
| `reservar_plantao` | Reserva vaga para medico | `app/tools/vagas.py` |
| `agendar_lembrete` | Agenda lembrete futuro | `app/tools/lembrete.py` |

Fluxo de uso de tools:

```
1. LLM recebe mensagem + definicoes de tools
2. LLM decide usar tool (retorna tool_use)
3. Sistema executa tool
4. Resultado enviado de volta ao LLM
5. LLM gera resposta final
```

### 4. Circuit Breaker

Protege contra falhas em cascata:

```python
# Estados
CLOSED   → Normal, chamadas passam
OPEN     → Falhas demais, bloqueia por X segundos
HALF_OPEN → Teste de recuperacao

# Circuitos implementados
circuit_claude    → API Anthropic
circuit_evolution → Evolution API
circuit_supabase  → Banco de dados
```

### 5. Rate Limiting

Implementado via Redis para distribuicao:

```python
# Limites configurados
MAX_MSGS_POR_HORA = 20
MAX_MSGS_POR_DIA = 100
INTERVALO_MIN = 45   # segundos
INTERVALO_MAX = 180  # segundos

# Horario comercial
HORARIO_INICIO = "08:00"
HORARIO_FIM = "20:00"
DIAS_PERMITIDOS = [0, 1, 2, 3, 4]  # Seg-Sex
```

---

## Fluxos de Dados

### Fluxo: Mensagem Recebida

```
1. Evolution API recebe msg WhatsApp
2. Evolution envia webhook POST /webhook/evolution
3. Webhook handler processa em background
4. Resposta retorna ao Evolution
5. Evolution envia para WhatsApp
6. Medico recebe resposta
```

### Fluxo: Handoff para Humano

```
1. Julia detecta trigger de handoff
2. Atualiza conversations.controlled_by = 'human'
3. Envia notificacao Slack
4. Sincroniza com Chatwoot
5. Julia para de responder
6. Humano assume via Chatwoot
7. Ao resolver, controlled_by volta para 'ai'
```

### Fluxo: Job Agendado

```
1. Scheduler verifica cron expressions
2. Quando match, faz POST para /jobs/<endpoint>
3. Job executa logica de negocio
4. Resultados salvos/notificados
```

---

## Seguranca

### RLS (Row Level Security)

Todas as tabelas tem RLS ativado no Supabase:

```sql
-- Exemplo de politica
CREATE POLICY "Acesso via service key"
ON public.clientes
FOR ALL
USING (auth.role() = 'service_role');
```

### Variaveis Sensiveis

Nunca commitadas, apenas em `.env`:

- `SUPABASE_SERVICE_KEY`
- `ANTHROPIC_API_KEY`
- `EVOLUTION_API_KEY`
- `CHATWOOT_API_KEY`
- `SLACK_WEBHOOK_URL`

### Rate Limiting por IP

FastAPI middleware pode limitar requests por IP (nao implementado ainda).

---

## Escalabilidade

### Horizontal

- Workers podem rodar em multiplas instancias
- Redis permite rate limiting distribuido
- Supabase escala automaticamente

### Vertical

- LLM calls sao o gargalo principal
- Cache de contexto reduz chamadas
- Haiku (80%) vs Sonnet (20%) otimiza custo

---

## Monitoramento

### Health Checks

```bash
GET /health           # Liveness
GET /health/ready     # Readiness (dependencias)
GET /health/rate      # Status rate limiting
GET /health/circuit   # Status circuit breakers
```

### Logs

```python
# Formato estruturado (JSON em producao)
{
    "timestamp": "2025-12-07T10:30:00Z",
    "level": "INFO",
    "message": "Mensagem processada",
    "medico_id": "uuid",
    "conversa_id": "uuid",
    "latencia_ms": 1234
}
```

### Metricas

- Tempo de resposta
- Taxa de sucesso
- Contagem de handoffs
- Taxa de deteccao como bot
- Uso de tokens LLM

---

## Proximos Passos (Roadmap)

1. **Observabilidade**
   - OpenTelemetry
   - Grafana dashboards
   - Alertas automaticos

2. **Performance**
   - Cache de embeddings
   - Batch processing
   - Connection pooling

3. **Resiliencia**
   - Retry com backoff
   - Dead letter queue
   - Graceful degradation
