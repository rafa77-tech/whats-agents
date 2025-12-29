# Epic 02: Tabela business_events

## Objetivo

Criar tabela dedicada para eventos de negócio, separada da `policy_events` que é para auditoria técnica.

## Contexto

### Por que tabela separada?

| Aspecto | policy_events | business_events |
|---------|---------------|-----------------|
| Propósito | Auditoria técnica | Métricas de negócio |
| Granularidade | Toda decisão/efeito | Apenas eventos de funil |
| Volume | Alto (~1000/dia) | Moderado (~100/dia) |
| Consumidor | Devs, replay | Gestores, dashboards |
| Retenção | 90 dias | Indefinida |

**Separar permite:**
- Queries de funil rápidas (tabela menor)
- Schema otimizado para business
- Retenção diferente
- Sem poluir auditoria técnica

---

## Story 2.1: Schema da Tabela

### Objetivo
Criar tabela `business_events` com schema limpo e semântico.

### Tarefas

1. **Criar migration** `create_business_events`:

```sql
-- Migration: create_business_events
-- Sprint 17 - E02
-- Schema revisado conforme recomendação do professor

CREATE TABLE IF NOT EXISTS public.business_events (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Origem do evento (com CHECK constraint)
    source TEXT NOT NULL CHECK (source IN ('pipeline', 'backend', 'db', 'heuristic', 'ops')),

    -- Entidades relacionadas (todas opcionais para flexibilidade)
    cliente_id UUID REFERENCES public.clientes(id) ON DELETE SET NULL,
    vaga_id UUID REFERENCES public.vagas(id) ON DELETE SET NULL,
    hospital_id UUID REFERENCES public.hospitais(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE SET NULL,
    interaction_id BIGINT REFERENCES public.interacoes(id) ON DELETE SET NULL,

    -- Link com policy (quando aplicável)
    policy_decision_id UUID,

    -- Evento
    event_type TEXT NOT NULL,
    event_props JSONB NOT NULL DEFAULT '{}'
);

-- Índices compostos otimizados para queries de funil (sempre com ts DESC)
CREATE INDEX IF NOT EXISTS idx_be_ts
ON public.business_events(ts DESC);

CREATE INDEX IF NOT EXISTS idx_be_type_ts
ON public.business_events(event_type, ts DESC);

CREATE INDEX IF NOT EXISTS idx_be_cliente_ts
ON public.business_events(cliente_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_be_vaga_ts
ON public.business_events(vaga_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_be_hospital_ts
ON public.business_events(hospital_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_be_policy
ON public.business_events(policy_decision_id);

-- Comentários
COMMENT ON TABLE business_events IS 'Eventos de negócio para funil e métricas - Sprint 17';
COMMENT ON COLUMN business_events.source IS 'Origem: pipeline (processamento), backend (código), db (trigger), heuristic (detector), ops (manual)';
COMMENT ON COLUMN business_events.event_type IS 'Tipo: doctor_inbound, doctor_outbound, offer_teaser_sent, offer_made, offer_accepted, offer_declined, handoff_created, shift_completed';
COMMENT ON COLUMN business_events.event_props IS 'Propriedades específicas do evento (JSON)';
```

### Valores de `source`

| Valor | Descrição |
|-------|-----------|
| `pipeline` | Emitido pelo pipeline de processamento de mensagens |
| `backend` | Emitido por código de aplicação genérico |
| `db` | Emitido por trigger do banco de dados |
| `heuristic` | Emitido por detector heurístico (ex: recusa) |
| `ops` | Emitido manualmente por operações |

### DoD

- [ ] Migration aplicada com sucesso
- [ ] Tabela `business_events` criada
- [ ] Todos os índices criados
- [ ] Foreign keys funcionando (com SET NULL)
- [ ] Comentários de documentação adicionados

---

## Story 2.2: Repository de Eventos

### Objetivo
Criar repository Python para persistir e consultar eventos de negócio.

### Tarefas

1. **Criar** `app/services/business_events/__init__.py`:

```python
"""Módulo de eventos de negócio."""
from .repository import (
    emit_event,
    get_events_by_type,
    get_events_for_cliente,
    get_events_for_vaga,
    get_funnel_counts,
)
from .types import BusinessEvent, EventType, EventSource

__all__ = [
    "emit_event",
    "get_events_by_type",
    "get_events_for_cliente",
    "get_events_for_vaga",
    "get_funnel_counts",
    "BusinessEvent",
    "EventType",
    "EventSource",
]
```

2. **Criar** `app/services/business_events/types.py`:

```python
"""Tipos para eventos de negócio."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class EventType(Enum):
    """Tipos de eventos de negócio."""
    DOCTOR_INBOUND = "doctor_inbound"
    DOCTOR_OUTBOUND = "doctor_outbound"
    OFFER_TEASER_SENT = "offer_teaser_sent"
    OFFER_MADE = "offer_made"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    HANDOFF_CREATED = "handoff_created"
    SHIFT_COMPLETED = "shift_completed"


class EventSource(Enum):
    """Origens válidas de eventos."""
    PIPELINE = "pipeline"    # Pipeline de processamento
    BACKEND = "backend"      # Código de aplicação
    DB = "db"                # Trigger de banco
    HEURISTIC = "heuristic"  # Detector heurístico
    OPS = "ops"              # Manual por operações


@dataclass
class BusinessEvent:
    """Evento de negócio."""
    event_type: EventType
    source: EventSource  # Obrigatório (CHECK constraint no DB)
    event_props: dict = field(default_factory=dict)

    # Entidades (opcionais)
    cliente_id: Optional[str] = None
    vaga_id: Optional[str] = None
    hospital_id: Optional[str] = None
    conversation_id: Optional[str] = None
    interaction_id: Optional[int] = None

    # Link com policy
    policy_decision_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Serializa para inserção no banco."""
        return {
            "event_type": self.event_type.value,
            "source": self.source.value,
            "event_props": self.event_props,
            "cliente_id": self.cliente_id,
            "vaga_id": self.vaga_id,
            "hospital_id": self.hospital_id,
            "conversation_id": self.conversation_id,
            "interaction_id": self.interaction_id,
            "policy_decision_id": self.policy_decision_id,
        }
```

3. **Criar** `app/services/business_events/repository.py`:

```python
"""Repository para eventos de negócio."""
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.services.supabase import supabase
from .types import BusinessEvent, EventType

logger = logging.getLogger(__name__)


async def emit_event(event: BusinessEvent) -> str:
    """
    Emite um evento de negócio.

    Args:
        event: Evento a emitir

    Returns:
        id do evento criado (UUID)
    """
    try:
        response = (
            supabase.table("business_events")
            .insert(event.to_dict())
            .execute()
        )

        if response.data:
            event_id = response.data[0]["id"]
            logger.info(
                f"BusinessEvent emitido: {event.event_type.value} "
                f"[{event_id[:8]}] source={event.source.value} cliente={event.cliente_id}"
            )
            return event_id

        logger.error("Falha ao emitir evento: sem data retornado")
        return ""

    except Exception as e:
        logger.error(f"Erro ao emitir business_event: {e}")
        return ""


async def get_events_by_type(
    event_type: EventType,
    hours: int = 24,
    limit: int = 100,
) -> list[dict]:
    """
    Busca eventos por tipo nas últimas N horas.

    Args:
        event_type: Tipo do evento
        hours: Janela de tempo
        limit: Máximo de resultados

    Returns:
        Lista de eventos
    """
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    try:
        response = (
            supabase.table("business_events")
            .select("*")
            .eq("event_type", event_type.value)
            .gte("ts", since)
            .order("ts", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar eventos por tipo: {e}")
        return []


async def get_events_for_cliente(
    cliente_id: str,
    hours: int = 168,  # 7 dias
) -> list[dict]:
    """
    Busca eventos de um cliente.

    Args:
        cliente_id: UUID do cliente
        hours: Janela de tempo

    Returns:
        Lista de eventos ordenados por tempo
    """
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    try:
        response = (
            supabase.table("business_events")
            .select("*")
            .eq("cliente_id", cliente_id)
            .gte("ts", since)
            .order("ts", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar eventos do cliente: {e}")
        return []


async def get_events_for_vaga(vaga_id: str) -> list[dict]:
    """
    Busca todos os eventos de uma vaga.

    Args:
        vaga_id: UUID da vaga

    Returns:
        Lista de eventos ordenados por tempo
    """
    try:
        response = (
            supabase.table("business_events")
            .select("*")
            .eq("vaga_id", vaga_id)
            .order("ts", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar eventos da vaga: {e}")
        return []


async def get_funnel_counts(
    hours: int = 24,
    hospital_id: Optional[str] = None,
) -> dict:
    """
    Conta eventos para o funil.

    Args:
        hours: Janela de tempo
        hospital_id: Filtrar por hospital (opcional)

    Returns:
        Dict com contagens por tipo de evento
    """
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    try:
        query = (
            supabase.table("business_events")
            .select("event_type")
            .gte("ts", since)
        )

        if hospital_id:
            query = query.eq("hospital_id", hospital_id)

        response = query.execute()

        # Contar por tipo
        counts = {}
        for row in response.data or []:
            event_type = row["event_type"]
            counts[event_type] = counts.get(event_type, 0) + 1

        return counts

    except Exception as e:
        logger.error(f"Erro ao contar eventos do funil: {e}")
        return {}
```

### DoD

- [ ] Módulo `business_events/` criado
- [ ] `types.py` com EventType e BusinessEvent
- [ ] `repository.py` com funções de persistência e consulta
- [ ] `emit_event` funciona e retorna event_id
- [ ] Queries de busca funcionam
- [ ] `get_funnel_counts` agrupa corretamente
- [ ] Logs informativos em todas operações

---

## Story 2.3: Testes do Repository

### Objetivo
Garantir que o repository funciona corretamente.

### Testes

```python
# tests/business_events/test_repository.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.services.business_events import (
    emit_event,
    get_events_by_type,
    get_events_for_cliente,
    get_funnel_counts,
    BusinessEvent,
    EventType,
)


class TestEmitEvent:
    """Testes para emissão de eventos."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_emit_event_success(self, mock_supabase):
        """Emite evento com sucesso."""
        mock_response = MagicMock()
        mock_response.data = [{"event_id": "test-uuid-123"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        event = BusinessEvent(
            event_type=EventType.OFFER_MADE,
            cliente_id="cliente-123",
            vaga_id="vaga-456",
            event_props={"valor": 1800},
        )

        event_id = await emit_event(event)

        assert event_id == "test-uuid-123"
        mock_supabase.table.assert_called_with("business_events")

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_emit_event_error(self, mock_supabase):
        """Retorna string vazia em caso de erro."""
        mock_supabase.table.side_effect = Exception("DB error")

        event = BusinessEvent(event_type=EventType.DOCTOR_INBOUND)

        event_id = await emit_event(event)

        assert event_id == ""


class TestGetEventsByType:
    """Testes para busca por tipo."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_get_events_by_type(self, mock_supabase):
        """Busca eventos por tipo."""
        mock_response = MagicMock()
        mock_response.data = [
            {"event_id": "1", "event_type": "offer_made"},
            {"event_id": "2", "event_type": "offer_made"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        events = await get_events_by_type(EventType.OFFER_MADE, hours=24)

        assert len(events) == 2


class TestGetFunnelCounts:
    """Testes para contagem de funil."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_get_funnel_counts(self, mock_supabase):
        """Conta eventos agrupados por tipo."""
        mock_response = MagicMock()
        mock_response.data = [
            {"event_type": "doctor_outbound"},
            {"event_type": "doctor_outbound"},
            {"event_type": "offer_made"},
            {"event_type": "offer_accepted"},
        ]
        mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = mock_response

        counts = await get_funnel_counts(hours=24)

        assert counts["doctor_outbound"] == 2
        assert counts["offer_made"] == 1
        assert counts["offer_accepted"] == 1

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_get_funnel_counts_with_hospital(self, mock_supabase):
        """Filtra por hospital."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.gte.return_value.eq.return_value.execute.return_value = mock_response

        counts = await get_funnel_counts(hours=24, hospital_id="hospital-123")

        # Verifica que filtrou por hospital
        mock_supabase.table.return_value.select.return_value.gte.return_value.eq.assert_called_with("hospital_id", "hospital-123")
```

### DoD

- [ ] Testes para emit_event (sucesso e erro)
- [ ] Testes para get_events_by_type
- [ ] Testes para get_events_for_cliente
- [ ] Testes para get_funnel_counts (com e sem filtro)
- [ ] Cobertura > 80% do repository

---

## Checklist do Épico

- [ ] **S17.E02.1** - Schema criado
- [ ] **S17.E02.2** - Repository implementado
- [ ] **S17.E02.3** - Testes passando
- [ ] Tabela no Supabase funcionando
- [ ] emit_event retorna event_id
- [ ] Queries de funil funcionando
