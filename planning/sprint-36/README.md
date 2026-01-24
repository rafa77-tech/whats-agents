# Sprint 36 - Resiliência e Observabilidade

**Início:** 2026-01-24
**Duração estimada:** 3 semanas
**Prioridade:** Alta
**Trigger:** Incidente 2026-01-23 (campanha sem envio + restrição WhatsApp)

---

## Objetivo

Fortalecer os sistemas de resiliência e observabilidade para:
1. Prevenir falhas silenciosas (como o worker não rodando)
2. Detectar e reagir a problemas mais rapidamente
3. Reduzir impacto de falhas em cascata
4. Ter visibilidade completa do estado do sistema
5. **Garantir ciclo de vida completo e robusto dos chips**

---

## Contexto

O incidente de 2026-01-23 revelou múltiplos gaps:
- Worker não executava por falta de entrypoint
- Circuit breaker com reset muito rápido (15s → 300s)
- Nenhum alerta de fila acumulando
- Sem health check do worker

**Análise adicional (2026-01-24):** Revisão completa do ciclo de vida dos chips revelou gaps adicionais:
- Métricas dos chips nunca alimentadas (Trust Score com dados vazios)
- Health Monitor não demove chips automaticamente
- Sync Evolution não está no scheduler
- Sem alerta proativo de pool baixo
- Circuit breaker é global, não per-chip

**Documento de referência:** `docs/auditorias/incidente-2026-01-23-campanha-sem-envio.md`

---

## Épicos

| ID | Épico | Tasks | Prioridade | Status |
|----|-------|-------|------------|--------|
| E01 | Fila de Mensagens | 6 | Alta | Pendente |
| E02 | Circuit Breaker | 5 | Alta | Pendente |
| E03 | Observabilidade | 7 | Alta | Pendente |
| E04 | Rate Limiting | 4 | Média | Pendente |
| E05 | Chips & Multi-Chip | 8 | **Crítica** | Parcial |
| E06 | Guardrails | 3 | Baixa | Pendente |
| E07 | Trust Score System | 4 | **Crítica** | ✅ T07.1 done |
| E08 | **Alimentação de Métricas** | 5 | **🔴 CRÍTICA** | Novo |
| E09 | **Circuit Breaker per-Chip** | 2 | **Crítica** | Novo |
| E10 | **Auditoria de Chips** | 3 | Média | Novo |
| E11 | **Lifecycle Automation** | 6 | **🔴 CRÍTICA** | Novo |

**Total:** 11 épicos, ~53 tasks

---

## Visão do Ciclo de Vida do Chip

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CICLO COMPLETO DO CHIP                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────┐   ┌─────────┐   ┌───────────┐   ┌────────┐   ┌────────┐         │
│  │PROVISION │──►│ WARMING │──►│   READY   │──►│ ACTIVE │──►│DEGRADED│         │
│  │ (Salvy)  │   │ (21 dias)│   │  (pool)   │   │ (prod) │   │        │         │
│  └──────────┘   └─────────┘   └───────────┘   └────────┘   └───┬────┘         │
│       │              │              ▲              │  ▲         │              │
│       ▼              ▼              │              ▼  │         ▼              │
│  ┌──────────┐   ┌─────────┐        │         ┌───────┴──┐  ┌────────┐         │
│  │ PENDING  │   │ Trust   │────────┘         │ Cooldown │  │ BANNED │         │
│  │  (QR)    │   │ >= 85   │                  │ Recovery │  │(final) │         │
│  └──────────┘   └─────────┘                  └──────────┘  └────────┘         │
│                                                                                 │
│  GAPS ENDEREÇADOS NESTA SPRINT:                                                │
│  ✅ E07/E08: Trust Score + Métricas alimentadas                                │
│  ✅ E09: Circuit breaker per-chip                                              │
│  ✅ E05: Retry com fallback + Cooldown + Threshold emergencial                 │
│  ✅ E11: Auto-demove + Sync Evolution + Alertas de pool                        │
│  ✅ E10: Auditoria de seleção + Dashboard + Ramp-up                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

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

### Análise Atual (Investigação Incidente 2026-01-23)

| Componente | Status | Problema |
|------------|--------|----------|
| `MULTI_CHIP_ENABLED` | ❌ | **Provavelmente `false` em produção** |
| ChipSelector | ⚠️ | Funciona, mas sem retry com chip alternativo |
| Trust Score threshold | ⚠️ | Requer >= 80 para prospecção (muito restritivo) |
| Fallback | ❌ | Não existe "retry com outro chip" em caso de falha |

**Descoberta crítica:** Durante o incidente, havia 4 chips cadastrados:
- Revoluna (trust=85) → foi restrito pelo WhatsApp
- Revoluna-01 (trust=75) → NÃO foi usado (75 < 80 threshold)
- Revoluna-02 (trust=70) → NÃO elegível
- zapi-revoluna (trust=70) → NÃO elegível

**Por que não houve fallback:** O sistema não tem lógica de "tentar próximo chip se atual falhar".

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

#### T05.5: Ativar MULTI_CHIP_ENABLED em produção
**Prioridade:** Crítica
**Arquivo:** Railway Environment Variables

Verificar e ativar `MULTI_CHIP_ENABLED=true` em produção para habilitar seleção inteligente de chips.

**Critério de aceite:**
- [ ] Verificar valor atual no Railway
- [ ] Setar `MULTI_CHIP_ENABLED=true` se necessário
- [ ] Validar que seleção está funcionando via logs
- [ ] Monitorar primeira campanha com multi-chip

---

#### T05.6: Retry com chip alternativo em caso de falha
**Prioridade:** Crítica
**Arquivo:** `app/services/outbound.py`, `app/services/chips/selector.py`

Implementar lógica de retry com próximo chip elegível quando envio falha.

```python
async def _enviar_com_fallback(telefone: str, texto: str, ctx: OutboundContext) -> OutboundResult:
    """Tenta enviar com chip selecionado, fallback para próximo se falhar."""
    chips_tentados = []
    max_tentativas = 3

    for tentativa in range(max_tentativas):
        chip = await chip_selector.selecionar_chip(
            tipo_mensagem=_determinar_tipo_mensagem(ctx),
            conversa_id=ctx.conversation_id,
            telefone_destino=telefone,
            excluir_chips=chips_tentados,  # NOVO: excluir já tentados
        )

        if not chip:
            break

        result = await enviar_via_chip(chip, telefone, texto)

        if result.success:
            return result

        chips_tentados.append(chip["id"])
        logger.warning(f"Chip {chip['telefone']} falhou, tentando próximo...")

    # Todos falharam
    return OutboundResult(
        success=False,
        outcome=SendOutcome.FAILED_ALL_CHIPS,
        error=f"Todos os {len(chips_tentados)} chips falharam",
    )
```

**Critério de aceite:**
- [ ] Parâmetro `excluir_chips` no selector
- [ ] Até 3 tentativas com chips diferentes
- [ ] Novo outcome `FAILED_ALL_CHIPS`
- [ ] Log de cada tentativa
- [ ] Testes de integração

---

#### T05.7: Threshold de trust emergencial para fallback
**Prioridade:** Alta
**Arquivo:** `app/services/chips/selector.py`

Quando não há chip com trust >= 80, aceitar chips com trust >= 60 como fallback.

```python
async def _buscar_chips_elegiveis(
    self,
    tipo_mensagem: TipoMensagem,
    fallback_mode: bool = False,
) -> List[Dict]:
    """
    Busca chips elegíveis com threshold normal ou fallback.

    Normal: prospeccao >= 80, followup >= 60, resposta >= 40
    Fallback: prospeccao >= 60, followup >= 40, resposta >= 20
    """
    if tipo_mensagem == "prospeccao":
        min_trust = 60 if fallback_mode else 80
        query = query.eq("pode_prospectar", True).gte("trust_score", min_trust)
    # ...

async def selecionar_chip(...) -> Optional[Dict]:
    # Tentar com threshold normal
    chips = await self._buscar_chips_elegiveis(tipo_mensagem, fallback_mode=False)

    if not chips:
        # Tentar com threshold reduzido
        logger.warning(f"[ChipSelector] Sem chips com trust alto, usando fallback mode")
        chips = await self._buscar_chips_elegiveis(tipo_mensagem, fallback_mode=True)

    # ...
```

**Critério de aceite:**
- [ ] Modo fallback implementado
- [ ] Log quando fallback é usado
- [ ] Métricas de uso do fallback
- [ ] Testes unitários

---

#### T05.8: Marcar chip como "cooling_off" após erro WhatsApp
**Prioridade:** Alta
**Arquivo:** `app/services/chips/health_monitor.py`

Quando chip recebe erro 400/403 do WhatsApp, colocar em cooldown temporário.

```python
async def registrar_erro_whatsapp(chip_id: str, error_code: int, error_message: str):
    """Registra erro do WhatsApp e aplica cooldown se necessário."""

    # Erros que indicam restrição
    RESTRICTION_CODES = [400, 403, 429]

    if error_code in RESTRICTION_CODES:
        cooldown_minutes = {
            429: 5,     # Rate limit: 5 min
            400: 30,    # Bad request (possível restrição): 30 min
            403: 60,    # Forbidden (restrição): 1 hora
        }.get(error_code, 15)

        await aplicar_cooldown(chip_id, cooldown_minutes)
        logger.warning(f"Chip {chip_id} em cooldown por {cooldown_minutes}min após erro {error_code}")
```

**Critério de aceite:**
- [ ] Cooldown automático por tipo de erro
- [ ] Chip ignorado na seleção durante cooldown
- [ ] Log de cooldowns aplicados
- [ ] Métrica de chips em cooldown

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

## E07: Trust Score System

### Análise Atual (Investigação Incidente 2026-01-23)

| Componente | Status | Problema |
|------------|--------|----------|
| Engine de cálculo | ✅ | `trust_score.py` implementado |
| Fatores dinâmicos | ✅ | 8 fatores configurados |
| Níveis e permissões | ✅ | 5 níveis (Verde a Crítico) |
| Job de atualização | ❌ | **NÃO está no scheduler!** |
| Resultado | ❌ | **Scores são FIXOS desde criação** |

**Descoberta crítica:** O Trust Score possui implementação completa mas o job `atualizar_todos_trust_scores` **nunca foi adicionado ao scheduler**. Isso significa que os scores dos chips nunca são recalculados!

**Arquivos relacionados:**
- `app/services/warmer/trust_score.py` - Engine de cálculo (implementado)
- `app/workers/scheduler.py` - Scheduler (falta o job!)

### Tasks

#### T07.1: Adicionar job de Trust Score ao scheduler
**Prioridade:** Crítica
**Arquivo:** `app/workers/scheduler.py`, `app/api/routes/jobs.py`

Adicionar job que recalcula trust scores de todos os chips ativos.

```python
# scheduler.py - Adicionar ao JOBS:
{
    "name": "atualizar_trust_scores",
    "endpoint": "/jobs/atualizar-trust-scores",
    "schedule": "*/15 * * * *",  # A cada 15 minutos
}

# jobs.py - Implementar endpoint:
@router.post("/jobs/atualizar-trust-scores")
async def job_atualizar_trust_scores():
    """Recalcula Trust Score de todos os chips ativos."""
    from app.services.warmer.trust_score import calcular_trust_score

    chips = supabase.table("chips").select("id").in_(
        "status", ["active", "warming", "ready"]
    ).execute()

    atualizados = 0
    erros = 0

    for chip in chips.data:
        try:
            await calcular_trust_score(chip["id"])
            atualizados += 1
        except Exception as e:
            logger.error(f"Erro ao atualizar trust score de {chip['id']}: {e}")
            erros += 1

    return {"atualizados": atualizados, "erros": erros}
```

**Critério de aceite:**
- [ ] Job adicionado ao scheduler
- [ ] Endpoint `/jobs/atualizar-trust-scores` criado
- [ ] Executa a cada 15 minutos
- [ ] Log de chips atualizados
- [ ] Alerta se mais de 50% dos chips falharem

---

#### T07.2: Atualizar fatores do chip após cada envio
**Prioridade:** Alta
**Arquivo:** `app/services/chips/sender.py`

Atualizar métricas de envio que alimentam o Trust Score.

```python
async def _atualizar_metricas_envio(chip_id: str, sucesso: bool) -> None:
    """Atualiza métricas de envio do chip."""
    try:
        # Incrementar contador de envios
        supabase.rpc(
            "incrementar_msgs_enviadas",
            {"p_chip_id": chip_id},
        ).execute()

        # Atualizar erros se falhou
        if not sucesso:
            supabase.rpc(
                "incrementar_erros_24h",
                {"p_chip_id": chip_id},
            ).execute()

        # Atualizar taxa de delivery
        await _recalcular_taxa_delivery(chip_id)

    except Exception as e:
        logger.warning(f"[ChipSender] Erro ao atualizar métricas: {e}")
```

**Critério de aceite:**
- [ ] Métricas atualizadas após cada envio
- [ ] Taxa de delivery recalculada
- [ ] Erros nas últimas 24h incrementados
- [ ] RPC functions criadas no Supabase

---

#### T07.3: Atualizar fatores após resposta recebida
**Prioridade:** Alta
**Arquivo:** `app/services/chips/selector.py`

Atualizar taxa de resposta e conversas bidirecionais.

```python
async def registrar_resposta_recebida(chip_id: str, telefone_remetente: str):
    """Registra resposta recebida para métricas de trust."""

    # Incrementar contador de respostas
    supabase.rpc(
        "incrementar_msgs_recebidas",
        {"p_chip_id": chip_id},
    ).execute()

    # Marcar interação anterior como "obteve_resposta"
    supabase.table("chip_interactions").update({
        "obteve_resposta": True,
    }).eq(
        "chip_id", chip_id
    ).eq(
        "destinatario", telefone_remetente
    ).eq(
        "tipo", "msg_enviada"
    ).is_(
        "obteve_resposta", None
    ).execute()

    # Recalcular taxa de resposta
    await _recalcular_taxa_resposta(chip_id)
```

**Critério de aceite:**
- [ ] Webhook chama `registrar_resposta_recebida`
- [ ] Taxa de resposta atualizada em tempo real
- [ ] Conversas bidirecionais contabilizadas
- [ ] Testes de integração

---

#### T07.4: Recalcular Trust Score após mudança significativa
**Prioridade:** Média
**Arquivo:** `app/services/warmer/trust_score.py`

Trigger para recálculo imediato após eventos significativos (erro grave, ban, etc).

```python
async def recalcular_trust_urgente(chip_id: str, motivo: str):
    """Recalcula Trust Score imediatamente após evento crítico."""
    logger.warning(f"[TrustScore] Recálculo urgente para {chip_id}: {motivo}")

    result = await calcular_trust_score(chip_id)

    # Se caiu para vermelho/crítico, notificar
    if result["nivel"] in ["vermelho", "critico"]:
        await notificar_slack(
            f":warning: Chip `{chip_id[:8]}...` caiu para nível *{result['nivel']}* "
            f"(score: {result['score']}) após {motivo}",
            canal="alertas"
        )

    return result

# Chamar após eventos críticos:
# - Erro 400/403 do WhatsApp
# - Bloqueio por spam detectado
# - Taxa de block > 2%
```

**Critério de aceite:**
- [ ] Função `recalcular_trust_urgente` criada
- [ ] Chamada após erros críticos
- [ ] Notificação no Slack se chip cair para vermelho/crítico
- [ ] Log de recálculos urgentes

---

## E08: Alimentação de Métricas de Chips (CRÍTICO - Novo)

### Análise (Descoberta 2026-01-23 19:35)

**Problema crítico:** O Trust Score está calculando com dados **vazios**!

Query de diagnóstico revelou:
```
| Chip | taxa_resposta | conversas_bi | diversidade_midia | erros_24h |
|------|---------------|--------------|-------------------|-----------|
| Todos| 0.00          | 0            | 0                 | 0         |
```

O score de 85 vem apenas de: base(50) + idade(~5) + delivery_default(15) + fase_bonus.

**Causa raiz:** Nenhum componente do sistema atualiza as métricas dos chips!

### Tasks

#### T08.1: Incrementar contadores após envio de mensagem
**Prioridade:** Crítica
**Arquivo:** `app/services/chips/sender.py`

Após cada envio via chip, atualizar:
- `msgs_enviadas_total += 1`
- `erros_ultimas_24h += 1` (se falhou)
- `ultimo_envio_em = now()`

```python
async def _registrar_envio(chip_id: str, sucesso: bool):
    """Registra envio para métricas do chip."""
    if sucesso:
        supabase.rpc("chip_registrar_envio_sucesso", {"p_chip_id": chip_id}).execute()
    else:
        supabase.rpc("chip_registrar_envio_erro", {"p_chip_id": chip_id}).execute()
```

**Critério de aceite:**
- [ ] RPC `chip_registrar_envio_sucesso` criada
- [ ] RPC `chip_registrar_envio_erro` criada
- [ ] Chamada no ChipSender após envio
- [ ] Teste de integração

---

#### T08.2: Registrar resposta recebida por chip
**Prioridade:** Crítica
**Arquivo:** `app/api/routes/webhook.py`

Quando mensagem inbound chega, identificar o chip que recebeu e atualizar:
- `msgs_recebidas_total += 1`
- Verificar se é resposta a mensagem enviada → `taxa_resposta`

```python
async def _registrar_resposta_chip(instance_name: str, telefone_remetente: str):
    """Registra resposta recebida para métricas do chip."""
    # Buscar chip pela instance
    chip = await buscar_chip_por_instance(instance_name)
    if not chip:
        return

    # Incrementar msgs recebidas
    supabase.rpc("chip_registrar_resposta", {
        "p_chip_id": chip["id"],
        "p_telefone_remetente": telefone_remetente
    }).execute()
```

**Critério de aceite:**
- [ ] RPC `chip_registrar_resposta` criada
- [ ] Webhook identifica chip que recebeu
- [ ] Taxa de resposta calculada corretamente
- [ ] Teste de integração

---

#### T08.3: Calcular taxa de delivery real
**Prioridade:** Alta
**Arquivo:** `app/services/chips/health_monitor.py`

Taxa de delivery = mensagens entregues / mensagens enviadas (últimos 7 dias)

```python
async def recalcular_taxa_delivery(chip_id: str) -> float:
    """Recalcula taxa de delivery do chip."""
    result = supabase.rpc("chip_calcular_taxa_delivery", {
        "p_chip_id": chip_id,
        "p_dias": 7
    }).execute()

    return result.data or 1.0  # Default 100% se sem dados
```

**Critério de aceite:**
- [ ] RPC que calcula delivery dos últimos 7 dias
- [ ] Considera `fila_mensagens.outcome` como fonte
- [ ] Atualiza `chips.taxa_delivery`

---

#### T08.4: Resetar erros_24h automaticamente
**Prioridade:** Média
**Arquivo:** `app/workers/scheduler.py`

Job diário para limpar erros antigos e recalcular `erros_ultimas_24h`.

```python
# Novo job no scheduler
{
    "name": "resetar_erros_chips",
    "endpoint": "/jobs/resetar-erros-chips",
    "schedule": "0 0 * * *",  # Meia-noite
}
```

**Critério de aceite:**
- [ ] Job criado
- [ ] Recalcula erros das últimas 24h reais
- [ ] Atualiza `dias_sem_erro` se 0 erros

---

#### T08.5: Registrar conversas bidirecionais
**Prioridade:** Alta
**Arquivo:** `app/services/chips/selector.py`

Conversa bidirecional = chip enviou E recebeu resposta do mesmo número.

```sql
-- Incrementar quando:
-- 1. Chip enviou mensagem para número X
-- 2. Chip recebeu mensagem de número X (dentro de 24h)
CREATE OR REPLACE FUNCTION chip_verificar_conversa_bidirecional(
    p_chip_id UUID,
    p_telefone TEXT
) RETURNS BOOLEAN AS $$
    -- Verificar se já enviamos para esse número nas últimas 24h
    -- Se sim, incrementar conversas_bidirecionais
$$;
```

**Critério de aceite:**
- [ ] Lógica de detecção implementada
- [ ] Contador incrementado corretamente
- [ ] Evita duplicatas (mesma conversa conta 1x)

---

## E09: Circuit Breaker por Chip (Novo)

### Análise

O circuit breaker atual é **global** para o serviço Evolution. Mas:
- Se Revoluna está restrito, Revoluna-01 deveria funcionar
- Não devemos parar de enviar por TODOS os chips se UM falhar

### Tasks

#### T09.1: Circuit breaker per-chip
**Prioridade:** Alta
**Arquivo:** `app/services/chips/circuit_breaker.py` (novo)

Cada chip tem seu próprio circuit breaker.

```python
class ChipCircuitBreaker:
    """Circuit breaker específico por chip."""

    _circuits: Dict[str, CircuitBreaker] = {}

    @classmethod
    def get_circuit(cls, chip_id: str) -> CircuitBreaker:
        if chip_id not in cls._circuits:
            cls._circuits[chip_id] = CircuitBreaker(
                nome=f"chip_{chip_id[:8]}",
                falhas_para_abrir=3,  # Menos tolerante por chip
                tempo_reset_segundos=300,
            )
        return cls._circuits[chip_id]
```

**Critério de aceite:**
- [ ] Circuit breaker por chip implementado
- [ ] Integrado com ChipSender
- [ ] ChipSelector ignora chips com circuit aberto

---

#### T09.2: Integrar circuit breaker na seleção
**Prioridade:** Alta
**Arquivo:** `app/services/chips/selector.py`

Não selecionar chip se seu circuit breaker está OPEN.

```python
async def selecionar_chip(...) -> Optional[Dict]:
    chips = await self._buscar_chips_elegiveis(...)

    # Filtrar chips com circuit aberto
    chips_disponiveis = [
        c for c in chips
        if ChipCircuitBreaker.get_circuit(c["id"]).estado != CircuitState.OPEN
    ]

    if not chips_disponiveis:
        logger.warning("[ChipSelector] Todos os chips com circuit aberto!")
        return None

    # ... continuar seleção
```

---

## E10: Auditoria e Observabilidade de Chips (Novo)

### Tasks

#### T10.1: Log de decisão do ChipSelector
**Prioridade:** Média
**Arquivo:** `app/services/chips/selector.py`

Registrar por que um chip foi selecionado (ou não).

```python
async def _log_selecao(
    chips_elegiveis: List[Dict],
    chip_selecionado: Optional[Dict],
    motivo: str,
    conversa_id: Optional[str] = None,
):
    """Registra decisão de seleção para auditoria."""
    supabase.table("chip_selection_log").insert({
        "conversa_id": conversa_id,
        "chips_elegiveis": [c["id"] for c in chips_elegiveis],
        "chip_selecionado": chip_selecionado["id"] if chip_selecionado else None,
        "motivo": motivo,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
```

---

#### T10.2: Dashboard de saúde dos chips
**Prioridade:** Média
**Arquivo:** `app/api/routes/health.py`

Endpoint `/health/chips` com status de todos os chips.

```python
@router.get("/health/chips")
async def health_chips():
    return {
        "chips": [
            {
                "telefone": c["telefone"][-4:],
                "trust_score": c["trust_score"],
                "trust_level": c["trust_level"],
                "circuit_state": ChipCircuitBreaker.get_circuit(c["id"]).estado.value,
                "pode_prospectar": c["pode_prospectar"],
                "msgs_24h": c["msgs_enviadas_24h"],
                "erros_24h": c["erros_ultimas_24h"],
            }
            for c in chips
        ],
        "chips_disponiveis": count_disponiveis,
        "chips_com_circuit_aberto": count_circuit_open,
    }
```

---

#### T10.3: Ramp-up gradual pós-restrição
**Prioridade:** Baixa
**Arquivo:** `app/services/chips/recovery.py` (novo)

Quando chip sai de restrição, não voltar a 100% imediatamente.

```python
async def iniciar_recuperacao(chip_id: str):
    """Inicia recuperação gradual de chip pós-restrição."""
    # Fase 1: 10% do limite normal (1 dia)
    # Fase 2: 25% do limite normal (2 dias)
    # Fase 3: 50% do limite normal (3 dias)
    # Fase 4: 100% do limite normal

    supabase.table("chips").update({
        "recovery_phase": 1,
        "recovery_started_at": datetime.now(timezone.utc).isoformat(),
        "limite_hora": limite_base * 0.1,
        "limite_dia": limite_dia_base * 0.1,
    }).eq("id", chip_id).execute()
```

---

## E11: Lifecycle Automation (CRÍTICO - Novo)

### Análise (Descoberta 2026-01-24)

**Problema:** Várias automações críticas do ciclo de vida não estão funcionando:

| Componente | Status | Problema |
|------------|--------|----------|
| Health Monitor | ⚠️ | Cria alertas mas **não demove** chips |
| Sync Evolution | ⚠️ | Existe mas **não está no scheduler** |
| Alertas de pool | ❌ | Não existe alerta proativo |
| Migração de conversas | ⚠️ | Básica, sem contexto |
| Registro de afinidade | ❌ | Interações chip-médico não registradas |
| Verificação conexão | ⚠️ | Não integrada na seleção |

### Tasks

#### T11.1: Health Monitor com auto-demove
**Prioridade:** Crítica
**Arquivo:** `app/services/chips/health_monitor.py`

Quando chip atinge critérios de degradação, demover automaticamente (não apenas criar alerta).

```python
async def verificar_e_demover_chip(chip_id: str) -> bool:
    """Verifica saúde do chip e demove se necessário."""
    chip = await buscar_chip(chip_id)

    deve_demover = False
    motivo = ""

    # Critérios de demoção automática
    if chip["trust_score"] < 40:
        deve_demover = True
        motivo = f"trust_score_critico:{chip['trust_score']}"

    elif chip["erros_ultimas_24h"] > 10:
        deve_demover = True
        motivo = f"muitos_erros:{chip['erros_ultimas_24h']}"

    elif not chip["evolution_connected"]:
        # Só demove se desconectado por mais de 30 minutos
        if chip["desconectado_desde"] and (now() - chip["desconectado_desde"]).minutes > 30:
            deve_demover = True
            motivo = "desconectado_prolongado"

    elif chip["taxa_block"] > 0.02:  # > 2% de blocks
        deve_demover = True
        motivo = f"taxa_block_alta:{chip['taxa_block']}"

    if deve_demover and chip["status"] == "active":
        await demover_chip(chip_id, motivo)
        await notificar_slack(
            f":warning: Chip `{chip['telefone'][-4:]}` demovido automaticamente. "
            f"Motivo: *{motivo}*",
            canal="alertas"
        )
        return True

    return False

async def demover_chip(chip_id: str, motivo: str):
    """Demove chip de active para degraded."""
    supabase.table("chips").update({
        "status": "degraded",
        "demovido_em": datetime.now(timezone.utc).isoformat(),
        "demovido_motivo": motivo,
    }).eq("id", chip_id).execute()

    # Registrar transição
    await registrar_transicao_chip(chip_id, "active", "degraded", motivo)

    # Triggar auto-replace no orchestrator
    await orchestrator.verificar_deficits()
```

**Critério de aceite:**
- [ ] Função `verificar_e_demover_chip` criada
- [ ] Critérios de demoção configuráveis
- [ ] Demoção automática quando critérios atingidos
- [ ] Notificação no Slack
- [ ] Auto-replace triggerado
- [ ] Teste de integração

---

#### T11.2: Sync Evolution no scheduler
**Prioridade:** Crítica
**Arquivo:** `app/workers/scheduler.py`, `app/api/routes/jobs.py`

Garantir que sync com Evolution está rodando periodicamente.

```python
# scheduler.py - Adicionar ao JOBS:
{
    "name": "sync_evolution_instances",
    "endpoint": "/jobs/sync-evolution",
    "schedule": "*/2 * * * *",  # A cada 2 minutos
}

# jobs.py - Implementar endpoint:
@router.post("/jobs/sync-evolution")
async def job_sync_evolution():
    """Sincroniza estado de todas as instâncias Evolution."""
    from app.services.chips.sync_evolution import sincronizar_todas_instancias

    result = await sincronizar_todas_instancias()

    # Alertar se muitas desconectadas
    if result["desconectadas"] > result["total"] * 0.3:
        await notificar_slack(
            f":rotating_light: {result['desconectadas']}/{result['total']} "
            f"instâncias Evolution desconectadas!",
            canal="alertas"
        )

    return result
```

**Critério de aceite:**
- [ ] Job adicionado ao scheduler
- [ ] Executa a cada 2 minutos
- [ ] Atualiza `evolution_connected` de todos os chips
- [ ] Alerta se > 30% desconectadas
- [ ] Log de sincronização

---

#### T11.3: Alerta proativo de pool baixo
**Prioridade:** Alta
**Arquivo:** `app/services/chips/orchestrator.py`, `app/services/alertas.py`

Alertar quando pool está abaixo do mínimo e provisioning é necessário.

```python
async def verificar_e_alertar_pool():
    """Verifica estado do pool e alerta se necessário."""
    status = await obter_status_pool()
    deficits = await verificar_deficits()

    alertas = []

    # Pool de produção crítico
    if status["producao"] < config["producao_min"]:
        alertas.append({
            "tipo": "pool_producao_critico",
            "severidade": "critical",
            "mensagem": f"Pool de produção crítico: {status['producao']}/{config['producao_min']} chips ativos",
        })

    # Reserve (ready) baixo
    if status["ready"] < config["ready_min"]:
        alertas.append({
            "tipo": "pool_ready_baixo",
            "severidade": "warning",
            "mensagem": f"Reserve baixo: {status['ready']}/{config['ready_min']} chips ready",
        })

    # Warming insuficiente
    if status["warming"] < config["warmup_buffer"]:
        alertas.append({
            "tipo": "warming_insuficiente",
            "severidade": "warning",
            "mensagem": f"Warming insuficiente: {status['warming']}/{config['warmup_buffer']} chips em aquecimento",
        })

    # Nenhum chip pode prospectar
    if status["podem_prospectar"] == 0:
        alertas.append({
            "tipo": "nenhum_chip_prospeccao",
            "severidade": "critical",
            "mensagem": "CRÍTICO: Nenhum chip disponível para prospecção!",
        })

    # Enviar alertas
    for alerta in alertas:
        await criar_alerta_pool(alerta)
        emoji = ":rotating_light:" if alerta["severidade"] == "critical" else ":warning:"
        await notificar_slack(f"{emoji} {alerta['mensagem']}", canal="alertas")

    return alertas
```

**Critério de aceite:**
- [ ] Verificação a cada 5 minutos
- [ ] Alerta crítico se producao < min
- [ ] Alerta warning se ready ou warming baixos
- [ ] Alerta crítico se nenhum chip para prospecção
- [ ] Cooldown de 30 minutos entre alertas do mesmo tipo

---

#### T11.4: Migração de conversas com contexto
**Prioridade:** Média
**Arquivo:** `app/services/chips/migration.py`

Ao migrar conversas de um chip degradado, preservar contexto completo.

```python
async def migrar_conversas_com_contexto(
    chip_origem_id: str,
    chip_destino_id: str,
) -> MigrationResult:
    """Migra conversas preservando contexto completo."""

    # Buscar conversas ativas do chip origem
    conversas = supabase.table("conversations").select(
        "*, interacoes(*), doctor_context(*)"
    ).eq(
        "chip_id", chip_origem_id
    ).eq(
        "status", "active"
    ).execute()

    migradas = 0
    erros = 0

    for conversa in conversas.data:
        try:
            # 1. Atualizar chip_id da conversa
            supabase.table("conversations").update({
                "chip_id": chip_destino_id,
                "chip_migrado_de": chip_origem_id,
                "chip_migrado_em": datetime.now(timezone.utc).isoformat(),
            }).eq("id", conversa["id"]).execute()

            # 2. Preservar afinidade médico-chip
            await atualizar_afinidade(
                medico_id=conversa["cliente_id"],
                chip_antigo=chip_origem_id,
                chip_novo=chip_destino_id,
            )

            # 3. Registrar migração para auditoria
            supabase.table("chip_migrations").insert({
                "conversa_id": conversa["id"],
                "chip_origem": chip_origem_id,
                "chip_destino": chip_destino_id,
                "interacoes_count": len(conversa.get("interacoes", [])),
                "motivo": "chip_degradado",
            }).execute()

            # 4. Se conversa tinha interação recente, agendar continuidade
            ultima_interacao = conversa.get("interacoes", [{}])[-1]
            if ultima_interacao and _foi_recente(ultima_interacao.get("created_at")):
                await agendar_mensagem_continuidade(
                    conversa_id=conversa["id"],
                    chip_id=chip_destino_id,
                    delay_horas=24,
                )

            migradas += 1

        except Exception as e:
            logger.error(f"Erro ao migrar conversa {conversa['id']}: {e}")
            erros += 1

    return MigrationResult(migradas=migradas, erros=erros)
```

**Critério de aceite:**
- [ ] Contexto completo preservado na migração
- [ ] Afinidade médico-chip atualizada
- [ ] Auditoria de migrações
- [ ] Continuidade agendada para conversas recentes
- [ ] Teste de integração

---

#### T11.5: Registro de interações chip-médico (afinidade)
**Prioridade:** Alta
**Arquivo:** `app/services/chips/affinity.py` (novo)

Registrar interações chip-médico para que afinidade funcione corretamente.

```python
async def registrar_interacao_chip_medico(
    chip_id: str,
    medico_id: str,
    tipo: str,  # "msg_enviada", "msg_recebida", "resposta_obtida"
) -> None:
    """Registra interação para cálculo de afinidade."""

    # Buscar ou criar registro de afinidade
    afinidade = supabase.table("medico_chip_affinity").select("*").eq(
        "medico_id", medico_id
    ).eq(
        "chip_id", chip_id
    ).single().execute()

    if afinidade.data:
        # Atualizar existente
        updates = {
            "ultima_interacao": datetime.now(timezone.utc).isoformat(),
            "total_interacoes": afinidade.data["total_interacoes"] + 1,
        }

        if tipo == "msg_enviada":
            updates["msgs_enviadas"] = afinidade.data.get("msgs_enviadas", 0) + 1
        elif tipo == "msg_recebida":
            updates["msgs_recebidas"] = afinidade.data.get("msgs_recebidas", 0) + 1
        elif tipo == "resposta_obtida":
            updates["respostas_obtidas"] = afinidade.data.get("respostas_obtidas", 0) + 1

        supabase.table("medico_chip_affinity").update(
            updates
        ).eq("id", afinidade.data["id"]).execute()
    else:
        # Criar novo
        supabase.table("medico_chip_affinity").insert({
            "medico_id": medico_id,
            "chip_id": chip_id,
            "primeira_interacao": datetime.now(timezone.utc).isoformat(),
            "ultima_interacao": datetime.now(timezone.utc).isoformat(),
            "total_interacoes": 1,
            "msgs_enviadas": 1 if tipo == "msg_enviada" else 0,
            "msgs_recebidas": 1 if tipo == "msg_recebida" else 0,
            "respostas_obtidas": 1 if tipo == "resposta_obtida" else 0,
        }).execute()

async def buscar_chip_com_afinidade(medico_id: str) -> Optional[str]:
    """Busca chip com maior afinidade para o médico."""
    result = supabase.table("medico_chip_affinity").select(
        "chip_id, total_interacoes, respostas_obtidas"
    ).eq(
        "medico_id", medico_id
    ).order(
        "respostas_obtidas", desc=True
    ).order(
        "total_interacoes", desc=True
    ).limit(1).execute()

    if result.data:
        return result.data[0]["chip_id"]
    return None
```

**Critério de aceite:**
- [ ] Interações registradas no envio
- [ ] Interações registradas no recebimento
- [ ] ChipSelector usa afinidade na seleção
- [ ] Afinidade considera respostas obtidas (peso maior)
- [ ] Teste unitário

---

#### T11.6: Verificar conexão Evolution na seleção
**Prioridade:** Alta
**Arquivo:** `app/services/chips/selector.py`

Não selecionar chip se instância Evolution não está conectada.

```python
async def _filtrar_chips_conectados(self, chips: List[Dict]) -> List[Dict]:
    """Filtra apenas chips com Evolution conectada."""
    chips_conectados = []

    for chip in chips:
        # Verificar flag de conexão (atualizado pelo sync)
        if not chip.get("evolution_connected", False):
            logger.debug(f"[ChipSelector] Chip {chip['id'][:8]} descartado: Evolution desconectada")
            continue

        # Verificar se não está em cooldown de conexão
        if chip.get("connection_cooldown_until"):
            cooldown_until = datetime.fromisoformat(chip["connection_cooldown_until"])
            if cooldown_until > datetime.now(timezone.utc):
                logger.debug(f"[ChipSelector] Chip {chip['id'][:8]} descartado: em cooldown de conexão")
                continue

        chips_conectados.append(chip)

    return chips_conectados

async def selecionar_chip(self, ...) -> Optional[Dict]:
    """Seleciona chip com todas as verificações."""
    chips = await self._buscar_chips_elegiveis(tipo_mensagem)

    # Filtrar por conexão Evolution
    chips = await self._filtrar_chips_conectados(chips)

    # Filtrar por circuit breaker
    chips = self._filtrar_chips_circuit_ok(chips)

    # Filtrar por cooldown
    chips = self._filtrar_chips_sem_cooldown(chips)

    if not chips:
        logger.warning("[ChipSelector] Nenhum chip disponível após todos os filtros")
        return None

    # Aplicar preferência de afinidade
    if conversa_id:
        medico_id = await buscar_medico_por_conversa(conversa_id)
        chip_afinidade = await buscar_chip_com_afinidade(medico_id)
        if chip_afinidade and chip_afinidade in [c["id"] for c in chips]:
            return next(c for c in chips if c["id"] == chip_afinidade)

    # Balanceamento de carga
    return self._selecionar_menos_usado(chips)
```

**Critério de aceite:**
- [ ] Chips desconectados não são selecionados
- [ ] Verificação usa flag `evolution_connected` (do sync)
- [ ] Log de chips descartados por conexão
- [ ] Métrica de chips descartados por conexão
- [ ] Teste unitário

---

## Priorização Sugerida (Atualizada)

### Concluído ✅
- **T05.5: MULTI_CHIP_ENABLED** - Já estava true
- **T07.1: Job de Trust Score** - Implementado e deployado

### Semana 1 (Crítico - Fundação de Métricas)

**Objetivo:** Alimentar o Trust Score com dados reais e garantir visibilidade.

| Task | Épico | Descrição | Esforço |
|------|-------|-----------|---------|
| **T08.1** | E08 | Incrementar contadores após envio | Médio |
| **T08.2** | E08 | Registrar resposta recebida por chip | Médio |
| **T11.2** | E11 | Sync Evolution no scheduler | Baixo |
| **T11.6** | E11 | Verificar conexão na seleção | Baixo |
| T01.3 | E01 | Circuit breaker no fila_worker | Médio |
| T01.5 | E01 | Alerta de fila acumulando | Baixo |
| T01.6 | E01 | Health check do worker | Baixo |

**Entregas Semana 1:**
- Trust Score começa a receber dados reais
- Sync Evolution rodando periodicamente
- Worker com circuit breaker e health check

---

### Semana 2 (Crítico - Resiliência de Chips)

**Objetivo:** Garantir failover automático e isolamento de falhas por chip.

| Task | Épico | Descrição | Esforço |
|------|-------|-----------|---------|
| **T05.6** | E05 | Retry com chip alternativo | Alto |
| **T05.8** | E05 | Cooldown após erro WhatsApp | Médio |
| **T09.1** | E09 | Circuit breaker per-chip | Alto |
| **T09.2** | E09 | Integrar circuit na seleção | Médio |
| **T11.1** | E11 | Health Monitor auto-demove | Alto |
| **T11.3** | E11 | Alerta proativo de pool baixo | Médio |
| T05.7 | E05 | Threshold emergencial | Baixo |

**Entregas Semana 2:**
- Falha em um chip não afeta outros
- Retry automático com próximo chip
- Chips problemáticos demovidos automaticamente
- Alertas quando pool está baixo

---

### Semana 3 (Importante - Métricas e Auditoria)

**Objetivo:** Completar métricas do Trust Score e auditoria.

| Task | Épico | Descrição | Esforço |
|------|-------|-----------|---------|
| **T08.3** | E08 | Calcular taxa de delivery real | Médio |
| **T08.5** | E08 | Registrar conversas bidirecionais | Médio |
| **T11.5** | E11 | Registro de afinidade chip-médico | Médio |
| T07.2 | E07 | Atualizar fatores após envio | Baixo |
| T07.3 | E07 | Atualizar fatores após resposta | Baixo |
| T10.1 | E10 | Log de decisão ChipSelector | Baixo |
| T10.2 | E10 | Dashboard de saúde dos chips | Médio |

**Entregas Semana 3:**
- Trust Score 100% alimentado
- Afinidade médico-chip funcionando
- Dashboard de chips completo

---

### Backlog (Pós-Sprint ou Baixa Prioridade)

| Task | Épico | Descrição | Motivo |
|------|-------|-----------|--------|
| T11.4 | E11 | Migração com contexto | Melhoria, não crítico |
| T10.3 | E10 | Ramp-up gradual pós-restrição | Nice-to-have |
| T08.4 | E08 | Resetar erros_24h automaticamente | Pode ser feito via RPC |
| T01.1 | E01 | Timeout mensagens travadas | Menor impacto |
| T01.2 | E01 | Cancelar mensagens antigas | Menor impacto |
| T02.1 | E02 | Log transições circuit breaker | Observabilidade |
| T02.2 | E02 | Backoff exponencial | Refinamento |
| T03.1 | E03 | Corrigir /health/ready | Pode adiar |
| T04.* | E04 | Rate Limiting | Já funciona básico |
| T06.* | E06 | Guardrails | Baixa prioridade |

---

## Matriz de Dependências

```
T08.1 (envio) ──────┬──► T07.2 (fatores envio)
                    │
T08.2 (resposta) ───┼──► T07.3 (fatores resposta)
                    │
                    └──► T08.3 (taxa delivery)
                         T08.5 (conversas bi)

T11.2 (sync evol) ──────► T11.6 (verificar conexão)
                              │
                              ▼
T09.1 (circuit/chip) ───► T09.2 (integrar seleção) ◄─── T05.6 (retry fallback)
                              │
                              ▼
                         T11.1 (auto-demove)

T11.5 (afinidade) ──────► ChipSelector usa afinidade
```

---

## Métricas de Sucesso

### Métricas Gerais

| Métrica | Antes | Meta |
|---------|-------|------|
| MTTR (tempo para detectar problema) | ~3h | < 15min |
| Mensagens perdidas silenciosamente | Desconhecido | 0 |
| Cobertura de health checks | 60% | 95% |
| Alertas falsos positivos | N/A | < 5% |

### Métricas de Chips (NOVO)

| Métrica | Antes | Meta |
|---------|-------|------|
| Trust Scores com dados reais | 0% | 100% |
| Chips com métricas alimentadas | 0 | Todos |
| Tempo para demover chip problemático | Manual | < 5min (auto) |
| Retry automático em falha | Não existe | 100% dos casos |
| Chips desconectados selecionados | Possível | 0 |
| Downtime por chip único restrito | Total | Isolado |
| Alertas de pool baixo | Não existe | < 5min após déficit |

### KPIs por Fase do Ciclo de Vida

| Fase | KPI | Meta |
|------|-----|------|
| Provisioning | Tempo até pending | < 2min |
| Pending | Tempo até warming | < 24h (QR scan) |
| Warming | Graduação em 21 dias | > 80% |
| Ready → Active | Tempo de promoção | < 1min |
| Active → Degraded | Demoção automática | 100% quando critérios atingidos |
| Degraded → Replace | Auto-replace | < 2min |

---

## Dependências

- Redis funcionando em produção
- Acesso ao Slack para alertas
- Supabase para novas tabelas
- **Evolution API acessível para sync**
- **Salvy API para provisioning**

---

## Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Health checks muito agressivos | Média | Falsos positivos | Thresholds conservadores |
| Overhead de métricas | Baixa | Performance | Sampling se necessário |
| Migração de circuit breaker | Baixa | Breaking change | Feature flag |
| **Auto-demove muito sensível** | Média | Chips demovidos desnecessariamente | Cooldown + múltiplos critérios |
| **Sync Evolution sobrecarrega API** | Baixa | Rate limit | Intervalo de 2min |
| **Pool esvazia durante warmup** | Média | Sem chips para prospecção | Buffer de 5 chips + alerta proativo |

---

## Tabelas de Banco Necessárias

| Tabela | Épico | Descrição |
|--------|-------|-----------|
| `chip_selection_log` | E10 | Auditoria de seleções |
| `chip_migrations` | E11 | Histórico de migrações |
| `pool_alerts` | E11 | Alertas de saúde do pool |

### RPCs Necessárias

| RPC | Épico | Descrição |
|-----|-------|-----------|
| `chip_registrar_envio_sucesso` | E08 | Incrementa contadores de sucesso |
| `chip_registrar_envio_erro` | E08 | Incrementa contadores de erro |
| `chip_registrar_resposta` | E08 | Registra resposta recebida |
| `chip_calcular_taxa_delivery` | E08 | Calcula taxa de delivery |
| `chip_verificar_conversa_bidirecional` | E08 | Detecta conversa bidirecional |

---

## Referências

- Incidente: `docs/auditorias/incidente-2026-01-23-campanha-sem-envio.md`
- Circuit Breaker: `app/services/circuit_breaker.py`
- Fila: `app/services/fila.py`, `app/workers/fila_worker.py`
- Health: `app/api/routes/health.py`
- **Chips:**
  - Orchestrator: `app/services/chips/orchestrator.py`
  - Selector: `app/services/chips/selector.py`
  - Sender: `app/services/chips/sender.py`
  - Health Monitor: `app/services/chips/health_monitor.py`
  - Sync Evolution: `app/services/chips/sync_evolution.py`
  - Trust Score: `app/services/warmer/trust_score.py`
