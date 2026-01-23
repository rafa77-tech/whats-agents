# Sprint 36 - Resiliência e Observabilidade

**Início:** 2026-01-24
**Duração estimada:** 2 semanas
**Prioridade:** Alta
**Trigger:** Incidente 2026-01-23 (campanha sem envio + restrição WhatsApp)

---

## Objetivo

Fortalecer os sistemas de resiliência e observabilidade para:
1. Prevenir falhas silenciosas (como o worker não rodando)
2. Detectar e reagir a problemas mais rapidamente
3. Reduzir impacto de falhas em cascata
4. Ter visibilidade completa do estado do sistema

---

## Contexto

O incidente de 2026-01-23 revelou múltiplos gaps:
- Worker não executava por falta de entrypoint
- Circuit breaker com reset muito rápido (15s → 300s)
- Nenhum alerta de fila acumulando
- Sem health check do worker

**Documento de referência:** `docs/auditorias/incidente-2026-01-23-campanha-sem-envio.md`

---

## Épicos

| ID | Épico | Tasks | Prioridade |
|----|-------|-------|------------|
| E01 | Fila de Mensagens | 6 | Alta |
| E02 | Circuit Breaker | 5 | Alta |
| E03 | Observabilidade | 7 | Alta |
| E04 | Rate Limiting | 4 | Média |
| E05 | Chips & Multi-Chip | 4 | Média |
| E06 | Guardrails | 3 | Baixa |

---

## E01: Fila de Mensagens

### Análise Atual

| Componente | Status | Problema |
|------------|--------|----------|
| `fila.py` | ⚠️ | Supabase como storage (lento) |
| `fila_worker.py` | ✅ | Entrypoint corrigido |
| Retry | ⚠️ | Backoff existe mas sem observabilidade |
| Mensagens travadas | ❌ | Sem timeout para status "processando" |

### Tasks

#### T01.1: Timeout para mensagens em "processando"
**Prioridade:** Alta
**Arquivo:** `app/services/fila.py`

Se uma mensagem está em `processando` por mais de 1 hora, resetar para `pendente` (com incremento de tentativas).

```python
async def resetar_mensagens_travadas(timeout_minutos: int = 60) -> int:
    """Reseta mensagens travadas em processando."""
    # UPDATE fila_mensagens SET status='pendente', tentativas=tentativas+1
    # WHERE status='processando' AND processando_desde < NOW() - INTERVAL '60 minutes'
```

**Critério de aceite:**
- [ ] Job `/jobs/resetar-fila-travada` criado
- [ ] Executar a cada 15 minutos no scheduler
- [ ] Log de mensagens resetadas
- [ ] Teste unitário

---

#### T01.2: Cancelar mensagens antigas
**Prioridade:** Média
**Arquivo:** `app/services/fila.py`

Mensagens pendentes há mais de 24 horas devem ser canceladas automaticamente.

```python
async def cancelar_mensagens_antigas(max_idade_horas: int = 24) -> int:
    """Cancela mensagens muito antigas."""
    # UPDATE fila_mensagens SET status='cancelada', outcome='FAILED_EXPIRED'
    # WHERE status='pendente' AND created_at < NOW() - INTERVAL '24 hours'
```

**Critério de aceite:**
- [ ] Job `/jobs/limpar-fila-antiga` criado
- [ ] Executar diariamente às 3h
- [ ] Outcome `FAILED_EXPIRED` adicionado ao enum
- [ ] Teste unitário

---

#### T01.3: Circuit breaker no fila_worker
**Prioridade:** Alta
**Arquivo:** `app/workers/fila_worker.py`

Envolver `send_outbound_message` com circuit breaker para evitar tentativas quando Evolution está fora.

```python
from app.services.circuit_breaker import circuit_evolution, CircuitOpenError

try:
    result = await circuit_evolution.executar(
        send_outbound_message,
        telefone=telefone,
        texto=mensagem["conteudo"],
        ctx=ctx,
    )
except CircuitOpenError:
    # Registrar outcome e reagendar
    await fila_service.registrar_outcome(
        mensagem_id=mensagem["id"],
        outcome=SendOutcome.FAILED_CIRCUIT_OPEN,
        outcome_reason_code="circuit_open:evolution",
    )
    await asyncio.sleep(30)  # Aguardar antes de próxima
    continue
```

**Critério de aceite:**
- [ ] Worker usa circuit breaker
- [ ] Não faz requisições quando circuit está OPEN
- [ ] Outcome FAILED_CIRCUIT_OPEN registrado
- [ ] Teste de integração

---

#### T01.4: Métricas de processamento da fila
**Prioridade:** Média
**Arquivo:** `app/services/fila.py`

Adicionar métricas de throughput e latência da fila.

```python
async def obter_metricas_fila() -> dict:
    return {
        "pendentes": count_by_status("pendente"),
        "processando": count_by_status("processando"),
        "enviadas_ultima_hora": count_sent_last_hour(),
        "erros_ultima_hora": count_errors_last_hour(),
        "tempo_medio_processamento_ms": avg_processing_time(),
        "mensagem_mais_antiga_minutos": oldest_pending_age(),
    }
```

**Critério de aceite:**
- [ ] Endpoint `/health/fila` criado
- [ ] Métricas expostas
- [ ] Incluir no `/health/deep`
- [ ] Teste unitário

---

#### T01.5: Alerta de fila acumulando
**Prioridade:** Alta
**Arquivo:** `app/services/alertas.py`

Se fila tem mais de 50 mensagens pendentes por mais de 30 minutos, alertar no Slack.

**Critério de aceite:**
- [ ] Job `/jobs/verificar-fila-acumulada` criado
- [ ] Executar a cada 10 minutos
- [ ] Alerta no Slack com detalhes
- [ ] Cooldown de 1 hora entre alertas

---

#### T01.6: Health check do worker
**Prioridade:** Alta
**Arquivo:** `app/workers/fila_worker.py`

Worker deve atualizar um heartbeat no Redis/Supabase a cada ciclo.

```python
async def registrar_heartbeat():
    """Registra que worker está vivo."""
    await redis.set("worker:fila:heartbeat", datetime.now().isoformat(), ex=120)
```

**Critério de aceite:**
- [ ] Worker atualiza heartbeat a cada ciclo
- [ ] `/health/worker` verifica heartbeat
- [ ] Alerta se heartbeat > 2 minutos sem atualização

---

## E02: Circuit Breaker

### Análise Atual

| Componente | Status | Problema |
|------------|--------|----------|
| `circuit_breaker.py` | ✅ | Básico funciona |
| Configuração Evolution | ✅ | Corrigido (300s reset) |
| Fallbacks | ❌ | Não implementados |
| Observabilidade | ❌ | Sem log de transições |

### Tasks

#### T02.1: Log de transições de estado
**Prioridade:** Alta
**Arquivo:** `app/services/circuit_breaker.py`

Registrar todas as transições em tabela para auditoria.

```python
async def _registrar_transicao(self, de: CircuitState, para: CircuitState, motivo: str):
    """Registra transição no banco."""
    supabase.table("circuit_transitions").insert({
        "circuit_name": self.nome,
        "from_state": de.value,
        "to_state": para.value,
        "reason": motivo,
        "falhas_consecutivas": self.falhas_consecutivas,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
```

**Critério de aceite:**
- [ ] Tabela `circuit_transitions` criada
- [ ] Todas transições registradas
- [ ] Endpoint `/health/circuits/history` para consulta

---

#### T02.2: Backoff exponencial no reset
**Prioridade:** Média
**Arquivo:** `app/services/circuit_breaker.py`

Em vez de tempo fixo para half-open, usar backoff exponencial.

```python
@dataclass
class CircuitBreaker:
    tempo_reset_inicial: int = 60        # Primeiro reset
    tempo_reset_max: int = 600           # Máximo 10 minutos
    multiplicador_backoff: float = 2.0   # Dobra a cada falha

    tentativas_half_open: int = field(default=0)

    def _calcular_tempo_reset(self) -> int:
        tempo = self.tempo_reset_inicial * (self.multiplicador_backoff ** self.tentativas_half_open)
        return min(tempo, self.tempo_reset_max)
```

**Critério de aceite:**
- [ ] Backoff implementado
- [ ] Reset após sucesso no half-open
- [ ] Testes unitários

---

#### T02.3: Diferenciar tipos de erro
**Prioridade:** Alta
**Arquivo:** `app/services/circuit_breaker.py`

Timeout não deve contar como falha (pode ser rede lenta).

```python
class ErrorType(Enum):
    TIMEOUT = "timeout"           # Não conta para abrir
    CLIENT_ERROR = "client_4xx"   # Conta
    SERVER_ERROR = "server_5xx"   # Conta
    NETWORK = "network"           # Conta

def _registrar_falha(self, erro: Exception, tipo: ErrorType):
    if tipo == ErrorType.TIMEOUT:
        # Log mas não incrementa contador
        logger.warning(f"Circuit {self.nome}: timeout (não conta como falha)")
        return
    # ... resto da lógica
```

**Critério de aceite:**
- [ ] Enum ErrorType criado
- [ ] Classificação de erros implementada
- [ ] Timeout não abre circuit
- [ ] Testes unitários

---

#### T02.4: Fallback para Evolution
**Prioridade:** Média
**Arquivo:** `app/services/outbound.py`

Quando circuit Evolution está aberto, tentar chip alternativo ou enfileirar.

```python
async def _fallback_evolution(*args, **kwargs):
    """Fallback quando Evolution está indisponível."""
    # Tentar outro chip via Z-API se disponível
    # Ou enfileirar para retry posterior
    return OutboundResult(
        success=False,
        outcome=SendOutcome.FAILED_CIRCUIT_OPEN,
        outcome_reason_code="evolution_circuit_open:queued_for_retry",
    )
```

**Critério de aceite:**
- [ ] Fallback implementado
- [ ] Tenta chip alternativo (Z-API)
- [ ] Se nenhum disponível, enfileira para retry

---

#### T02.5: Dashboard de circuits
**Prioridade:** Baixa
**Arquivo:** `app/api/routes/health.py`

Endpoint rico com estado atual + histórico recente.

```python
@router.get("/circuits/dashboard")
async def circuits_dashboard():
    return {
        "current": obter_status_circuits(),
        "last_24h": {
            "evolution": await get_transitions("evolution", hours=24),
            "claude": await get_transitions("claude", hours=24),
            "supabase": await get_transitions("supabase", hours=24),
        },
        "health_score": calculate_overall_health(),
    }
```

---

## E03: Observabilidade

### Análise Atual

| Componente | Status | Problema |
|------------|--------|----------|
| `/health` | ✅ | Básico funciona |
| `/health/ready` | ⚠️ | Não verifica Supabase |
| `/health/deep` | ✅ | Completo |
| Métricas | ⚠️ | Em memória, perde ao restart |
| Alertas | ⚠️ | Alguns gaps |

### Tasks

#### T03.1: Corrigir /health/ready
**Prioridade:** Alta
**Arquivo:** `app/api/routes/health.py`

Verificar Redis E Supabase no readiness check.

```python
@router.get("/health/ready")
async def health_ready():
    checks = {}

    # Redis
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Supabase
    try:
        supabase.table("app_settings").select("key").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as e:
        checks["supabase"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ready" if all_ok else "not_ready", "checks": checks}
    )
```

**Critério de aceite:**
- [ ] Supabase verificado
- [ ] Retorna 503 se qualquer check falhar
- [ ] Teste de integração

---

#### T03.2: Persistir métricas no Supabase
**Prioridade:** Média
**Arquivo:** `app/core/metrics.py`

Criar tabela para métricas e persistir periodicamente.

```sql
CREATE TABLE metrics_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name TEXT NOT NULL,
    value NUMERIC NOT NULL,
    labels JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metrics_name_time ON metrics_snapshots(metric_name, created_at DESC);
```

**Critério de aceite:**
- [ ] Tabela criada
- [ ] Snapshot a cada 5 minutos
- [ ] Retenção de 7 dias
- [ ] Endpoint `/metrics/history`

---

#### T03.3: Alerta de erros acumulados
**Prioridade:** Alta
**Arquivo:** `app/services/alertas.py`

Se mais de 10 erros em 5 minutos, alertar.

**Critério de aceite:**
- [ ] Job verifica erros recentes
- [ ] Alerta no Slack com breakdown por tipo
- [ ] Cooldown de 30 minutos

---

#### T03.4: Health check consolidado
**Prioridade:** Média
**Arquivo:** `app/api/routes/health.py`

Endpoint único que retorna score de saúde geral.

```python
@router.get("/health/score")
async def health_score():
    scores = {
        "redis": await check_redis(),           # 0-100
        "supabase": await check_supabase(),     # 0-100
        "evolution": await check_evolution(),   # 0-100
        "circuits": await check_circuits(),     # 0-100
        "fila": await check_fila(),             # 0-100
        "worker": await check_worker(),         # 0-100
    }

    overall = sum(scores.values()) / len(scores)

    return {
        "overall_score": overall,
        "status": "healthy" if overall >= 80 else "degraded" if overall >= 50 else "unhealthy",
        "components": scores,
    }
```

---

#### T03.5: Trace de requisição end-to-end
**Prioridade:** Baixa
**Arquivo:** `app/core/tracing.py`

Adicionar correlation_id em todas as operações.

```python
import uuid
from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

def get_correlation_id() -> str:
    cid = correlation_id.get()
    if not cid:
        cid = str(uuid.uuid4())[:8]
        correlation_id.set(cid)
    return cid
```

---

#### T03.6: Alerta de job atrasado
**Prioridade:** Alta
**Arquivo:** `app/services/alertas.py`

Se job não executa dentro do SLA, alertar.

**Critério de aceite:**
- [ ] Verificar `job_executions` vs SLA
- [ ] Alerta se job atrasado > 2x intervalo
- [ ] Incluir heartbeat no alerta

---

#### T03.7: Monitor de conexão WhatsApp
**Prioridade:** Alta
**Arquivo:** `app/services/monitor_whatsapp.py`

Corrigir monitor para funcionar no Railway (sem subprocess).

```python
# Em vez de subprocess para logs Docker:
async def verificar_conexao():
    """Verifica conexão via API Evolution."""
    for instance in instances:
        status = await evolution.get_instance_status(instance)
        if status != "connected":
            await criar_alerta(...)
```

**Critério de aceite:**
- [ ] Não usar subprocess
- [ ] Verificar via API Evolution
- [ ] Funcionar no Railway

---

## E04: Rate Limiting

### Tasks

#### T04.1: Limite por cliente_id
**Prioridade:** Alta
**Arquivo:** `app/services/rate_limiter.py`

Máximo 3 mensagens por médico por dia (evitar spam percebido).

---

#### T04.2: Diferenciação por tipo
**Prioridade:** Média
**Arquivo:** `app/services/rate_limiter.py`

Campanhas contam 2x no rate limit (mais agressivas).

---

#### T04.3: Jitter para evitar thundering herd
**Prioridade:** Baixa
**Arquivo:** `app/services/rate_limiter.py`

Adicionar variação aleatória nos delays.

---

#### T04.4: Persistência de backup
**Prioridade:** Baixa
**Arquivo:** `app/services/rate_limiter.py`

Se Redis cai, usar Supabase como fallback.

---

## E05: Chips & Multi-Chip

### Tasks

#### T05.1: Cache de chips elegíveis
**Prioridade:** Média
**Arquivo:** `app/services/chips/selector.py`

Cache de 1 minuto para evitar N+1.

---

#### T05.2: Verificar status Evolution na seleção
**Prioridade:** Alta
**Arquivo:** `app/services/chips/selector.py`

Não selecionar chip se instância Evolution desconectada.

---

#### T05.3: Circuit breaker na seleção
**Prioridade:** Média
**Arquivo:** `app/services/chips/selector.py`

Se seleção falha, usar fallback (chip padrão).

---

#### T05.4: Métricas de uso por chip
**Prioridade:** Baixa
**Arquivo:** `app/services/chips/health_monitor.py`

Dashboard de uso e saúde por chip.

---

## E06: Guardrails

### Tasks

#### T06.1: Feature flag para contact_cap
**Prioridade:** Média
**Arquivo:** `app/services/guardrails/check.py`

Tornar `contact_cap_7d` configurável.

---

#### T06.2: Audit trail de bypasses
**Prioridade:** Alta
**Arquivo:** `app/services/guardrails/check.py`

Tabela `guardrail_bypasses` com quem, quando, motivo.

---

#### T06.3: Endpoint de unblock manual
**Prioridade:** Baixa
**Arquivo:** `app/api/routes/admin.py`

Admin pode desbloquear médico com motivo auditado.

---

## Priorização Sugerida

### Semana 1 (Crítico)
- T01.3: Circuit breaker no fila_worker
- T01.5: Alerta de fila acumulando
- T01.6: Health check do worker
- T03.1: Corrigir /health/ready
- T03.7: Monitor WhatsApp para Railway

### Semana 2 (Importante)
- T01.1: Timeout para mensagens travadas
- T01.4: Métricas de processamento
- T02.1: Log de transições
- T02.3: Diferenciar tipos de erro
- T03.3: Alerta de erros acumulados
- T04.1: Limite por cliente_id

### Backlog (Nice to have)
- T01.2: Cancelar mensagens antigas
- T02.2: Backoff exponencial
- T02.4: Fallback Evolution
- T03.2: Persistir métricas
- T03.4: Health score consolidado
- Restante

---

## Métricas de Sucesso

| Métrica | Antes | Meta |
|---------|-------|------|
| MTTR (tempo para detectar problema) | ~3h | < 15min |
| Mensagens perdidas silenciosamente | Desconhecido | 0 |
| Cobertura de health checks | 60% | 95% |
| Alertas falsos positivos | N/A | < 5% |

---

## Dependências

- Redis funcionando em produção
- Acesso ao Slack para alertas
- Supabase para novas tabelas

---

## Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Health checks muito agressivos | Média | Falsos positivos | Thresholds conservadores |
| Overhead de métricas | Baixa | Performance | Sampling se necessário |
| Migração de circuit breaker | Baixa | Breaking change | Feature flag |

---

## Referências

- Incidente: `docs/auditorias/incidente-2026-01-23-campanha-sem-envio.md`
- Circuit Breaker: `app/services/circuit_breaker.py`
- Fila: `app/services/fila.py`, `app/workers/fila_worker.py`
- Health: `app/api/routes/health.py`
