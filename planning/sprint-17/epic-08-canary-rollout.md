# Epic 08: Canary Rollout

## Objetivo

Implementar rollout gradual dos business events para minimizar riscos.

## Contexto

### Estratégia de Rollout

| Fase | % Tráfego | Duração | Critério de Sucesso |
|------|-----------|---------|---------------------|
| 1 | 2% | 2 dias | Sem erros, eventos chegando |
| 2 | 10% | 3 dias | Funil calculando corretamente |
| 3 | 50% | 2 dias | Alertas funcionando |
| 4 | 100% | - | Produção completa |

### Princípios

1. **Rollback rápido:** Flag para desabilitar em segundos
2. **Observabilidade:** Métricas de cada fase
3. **Sem impacto:** Business events são adicionais, não bloqueiam

---

## Story 8.1: Flag de Rollout (via feature_flags)

### Objetivo
Usar feature_flags existentes para controlar rollout (não código hardcoded).

### Estrutura da Flag (Recomendação do Professor)

```json
{
  "canary_rollout": {
    "enabled": true,
    "percentage": 2,
    "force_on": ["uuid1", "uuid2"]  // allowlist para debug
  }
}
```

### Tarefas

1. **Adicionar flag no banco**:

```sql
-- Usar tabela feature_flags existente
INSERT INTO feature_flags (flag_key, value, description)
VALUES (
    'business_events_canary',
    '{"enabled": true, "percentage": 2, "force_on": []}',
    'Canary rollout para business_events: enabled, percentage (0-100), force_on (UUIDs para debug)'
)
ON CONFLICT (flag_key) DO UPDATE SET value = EXCLUDED.value;
```

2. **Criar helper de verificação com allowlist**:

```python
# app/services/business_events/rollout.py

import hashlib
import json
import logging
from typing import Optional, List

from app.services.feature_flags import get_flag

logger = logging.getLogger(__name__)

# Cache local para evitar queries repetidas
_canary_cache: dict = {}
_cache_ttl = 60  # segundos


async def get_canary_config() -> dict:
    """Obtém configuração do canary (com cache)."""
    import time

    cache_key = "business_events_canary"
    now = time.time()

    # Verificar cache
    if cache_key in _canary_cache:
        cached = _canary_cache[cache_key]
        if now - cached["ts"] < _cache_ttl:
            return cached["config"]

    # Buscar do banco
    try:
        flag_value = await get_flag("business_events_canary", default='{"enabled": false}')
        config = json.loads(flag_value) if isinstance(flag_value, str) else flag_value
    except Exception as e:
        logger.error(f"Erro ao obter canary config: {e}")
        config = {"enabled": False, "percentage": 0, "force_on": []}

    # Atualizar cache
    _canary_cache[cache_key] = {"ts": now, "config": config}

    return config


async def should_emit_event(
    cliente_id: str,
    event_type: str,
) -> bool:
    """
    Verifica se deve emitir evento baseado no rollout.

    Args:
        cliente_id: UUID do cliente (usado para consistência)
        event_type: Tipo do evento

    Returns:
        True se deve emitir
    """
    config = await get_canary_config()

    # Master switch
    if not config.get("enabled", False):
        return False

    # Allowlist para debug (force_on)
    force_on = config.get("force_on", [])
    if cliente_id in force_on:
        logger.debug(f"Cliente {cliente_id[:8]} está na allowlist, emitindo evento")
        return True

    # Percentual de rollout
    percentage = config.get("percentage", 0)

    if percentage >= 100:
        return True

    if percentage <= 0:
        return False

    # Hash do cliente_id para consistência
    # Mesmo cliente sempre na mesma cohort
    hash_val = int(hashlib.md5(cliente_id.encode()).hexdigest()[:8], 16)
    bucket = hash_val % 100

    return bucket < percentage


async def get_rollout_status() -> dict:
    """Retorna status atual do rollout."""
    config = await get_canary_config()

    return {
        "enabled": config.get("enabled", False),
        "percentage": config.get("percentage", 0),
        "force_on_count": len(config.get("force_on", [])),
        "phase": _get_phase_name(config.get("percentage", 0)),
    }


async def add_to_allowlist(cliente_id: str) -> bool:
    """
    Adiciona cliente à allowlist para debug.

    Args:
        cliente_id: UUID do cliente

    Returns:
        True se adicionado com sucesso
    """
    try:
        config = await get_canary_config()
        force_on = config.get("force_on", [])

        if cliente_id not in force_on:
            force_on.append(cliente_id)
            config["force_on"] = force_on

            # Atualizar no banco
            from app.services.supabase import supabase
            supabase.table("feature_flags").update({
                "value": json.dumps(config)
            }).eq("flag_key", "business_events_canary").execute()

            # Limpar cache
            _canary_cache.clear()

            logger.info(f"Cliente {cliente_id[:8]} adicionado à allowlist")
            return True

        return False

    except Exception as e:
        logger.error(f"Erro ao adicionar à allowlist: {e}")
        return False


def _get_phase_name(pct: int) -> str:
    """Retorna nome da fase baseado no percentual."""
    if pct <= 0:
        return "disabled"
    elif pct <= 5:
        return "canary_2pct"
    elif pct <= 15:
        return "canary_10pct"
    elif pct <= 60:
        return "canary_50pct"
    else:
        return "full_rollout"
```

### DoD

- [ ] Flag `business_events_canary` criada com estrutura JSON
- [ ] `get_canary_config()` com cache de 60s
- [ ] `should_emit_event()` verifica allowlist (force_on) primeiro
- [ ] `add_to_allowlist()` para debug facilitado
- [ ] Função `should_emit_event` implementada
- [ ] Hash consistente por cliente_id
- [ ] Função `get_rollout_status` para monitoramento

---

## Story 8.2: Integração com Emissores

### Objetivo
Integrar verificação de rollout nos emissores.

### Tarefas

1. **Wrapper para emit_event**:

```python
# app/services/business_events/repository.py (modificar)

from .rollout import should_emit_event

async def emit_event(event: BusinessEvent) -> str:
    """
    Emite um evento de negócio (respeitando rollout).

    Args:
        event: Evento a emitir

    Returns:
        event_id do evento criado ou "" se não emitiu
    """
    # Verificar rollout
    if event.cliente_id:
        should_emit = await should_emit_event(
            cliente_id=event.cliente_id,
            event_type=event.event_type.value,
        )

        if not should_emit:
            logger.debug(
                f"Evento {event.event_type.value} ignorado (rollout): "
                f"cliente={event.cliente_id}"
            )
            return ""

    # Emitir normalmente
    return await _do_emit_event(event)


async def _do_emit_event(event: BusinessEvent) -> str:
    """Emite evento (implementação real)."""
    try:
        response = (
            supabase.table("business_events")
            .insert(event.to_dict())
            .execute()
        )

        if response.data:
            event_id = response.data[0]["event_id"]
            logger.info(
                f"BusinessEvent emitido: {event.event_type.value} "
                f"[{event_id[:8]}] cliente={event.cliente_id}"
            )
            return event_id

        return ""

    except Exception as e:
        logger.error(f"Erro ao emitir business_event: {e}")
        return ""
```

2. **Trigger DB também respeita flag**:

```sql
-- Modificar triggers para verificar flag
-- Opção: verificar via RPC no trigger (mais complexo)
-- Alternativa: manter triggers sempre ativos, rollout só no backend

-- Para V1, triggers são 100% ativos
-- Rollout controla apenas emissores backend
```

### DoD

- [ ] `emit_event` verifica rollout antes de emitir
- [ ] Log de debug quando ignorado
- [ ] Triggers DB ativos (não afetados pelo rollout)

---

## Story 8.3: Métricas de Rollout

### Objetivo
Monitorar saúde do rollout em cada fase.

### Tarefas

1. **Criar endpoint de status**:

```python
# app/api/routes/admin.py (adição)

from app.services.business_events.rollout import get_rollout_status

@router.get("/rollout/business-events")
async def business_events_rollout_status():
    """Retorna status do rollout de business events."""
    status = await get_rollout_status()

    # Adicionar métricas
    desde_1h = (datetime.utcnow() - timedelta(hours=1)).isoformat()

    try:
        response = (
            supabase.table("business_events")
            .select("event_type", count="exact")
            .gte("ts", desde_1h)
            .execute()
        )

        status["events_last_hour"] = response.count or 0
    except:
        status["events_last_hour"] = -1

    return status
```

2. **Dashboard de monitoramento** (via Slack):

```python
# app/services/business_events/monitoring.py

async def generate_rollout_report() -> str:
    """Gera relatório de rollout para Slack."""
    status = await get_rollout_status()

    # Contar eventos por tipo
    desde_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat()

    response = (
        supabase.table("business_events")
        .select("event_type")
        .gte("ts", desde_24h)
        .execute()
    )

    counts = {}
    for row in response.data or []:
        et = row["event_type"]
        counts[et] = counts.get(et, 0) + 1

    # Formatar
    lines = [
        f"*📊 Business Events Rollout Status*",
        f"",
        f"*Fase:* {status['phase']}",
        f"*Rollout:* {status['rollout_pct']}%",
        f"*Habilitado:* {'✅' if status['enabled'] else '❌'}",
        f"",
        f"*Eventos (últimas 24h):*",
    ]

    for event_type, count in sorted(counts.items()):
        lines.append(f"  • {event_type}: {count}")

    if not counts:
        lines.append("  • Nenhum evento registrado")

    return "\n".join(lines)
```

### DoD

- [ ] Endpoint `/rollout/business-events` funcionando
- [ ] Relatório de rollout para Slack
- [ ] Contagem de eventos por tipo

---

## Story 8.4: Procedimento de Rollout

### Objetivo
Documentar procedimento para cada fase.

### Procedimento

#### Fase 1: Canary 2%

```bash
# Ativar 2%
UPDATE feature_flags SET value = '2' WHERE flag_key = 'business_events_rollout_pct';

# Monitorar por 2 dias:
# 1. Logs de erro
# 2. Eventos chegando (SELECT COUNT(*) FROM business_events WHERE ts > NOW() - INTERVAL '1 hour')
# 3. Sem impacto em latência de mensagens

# Se OK, avançar para Fase 2
```

#### Fase 2: Canary 10%

```bash
# Aumentar para 10%
UPDATE feature_flags SET value = '10' WHERE flag_key = 'business_events_rollout_pct';

# Monitorar por 3 dias:
# 1. Funil calculando (GET /metricas/funil)
# 2. Taxas fazem sentido (response_rate ~ 20-40%)
# 3. Sem degradação de performance

# Se OK, avançar para Fase 3
```

#### Fase 3: Canary 50%

```bash
# Aumentar para 50%
UPDATE feature_flags SET value = '50' WHERE flag_key = 'business_events_rollout_pct';

# Monitorar por 2 dias:
# 1. Alertas disparando corretamente
# 2. Volume de dados aceitável
# 3. Queries de funil performáticas

# Se OK, avançar para Fase 4
```

#### Fase 4: Full Rollout

```bash
# Liberar 100%
UPDATE feature_flags SET value = '100' WHERE flag_key = 'business_events_rollout_pct';

# Monitorar continuamente
# Remover código de rollout após 2 semanas de estabilidade
```

#### Rollback de Emergência

```bash
# Desabilitar imediatamente
UPDATE feature_flags SET value = 'false' WHERE flag_key = 'business_events_enabled';

# Investigar problema
# Quando corrigido, reabilitar e continuar rollout
UPDATE feature_flags SET value = 'true' WHERE flag_key = 'business_events_enabled';
```

### DoD

- [ ] Procedimento documentado para cada fase
- [ ] Critérios de sucesso definidos
- [ ] Procedimento de rollback documentado
- [ ] Comandos SQL prontos para uso

---

## Checklist do Épico

- [ ] **S17.E08.1** - Flag de rollout
- [ ] **S17.E08.2** - Integração com emissores
- [ ] **S17.E08.3** - Métricas de rollout
- [ ] **S17.E08.4** - Procedimento documentado
- [ ] Rollout iniciado em 2%
- [ ] Monitoramento funcionando
- [ ] Rollback testado
