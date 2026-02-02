"""
Testes para repository de business_events.

Sprint 17 - E02.3
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.business_events import (
    emit_event,
    get_events_by_type,
    get_events_for_cliente,
    get_funnel_counts,
    BusinessEvent,
    EventType,
    EventSource,
)


class TestEmitEvent:
    """Testes para emissao de eventos."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_emit_event_success(self, mock_supabase):
        """Emite evento com sucesso."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-uuid-123"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        event = BusinessEvent(
            event_type=EventType.OFFER_MADE,
            source=EventSource.BACKEND,
            cliente_id="cliente-123",
            vaga_id="vaga-456",
            event_props={"valor": 1800},
        )

        event_id = await emit_event(event)

        assert event_id == "test-uuid-123"
        mock_supabase.table.assert_called_with("business_events")

        # Verificar dados enviados
        insert_call = mock_supabase.table.return_value.insert.call_args[0][0]
        assert insert_call["event_type"] == "offer_made"
        assert insert_call["source"] == "backend"
        assert insert_call["cliente_id"] == "cliente-123"
        assert insert_call["vaga_id"] == "vaga-456"
        assert insert_call["event_props"]["valor"] == 1800

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_emit_event_error(self, mock_supabase):
        """Retorna string vazia em caso de erro."""
        mock_supabase.table.side_effect = Exception("DB error")

        event = BusinessEvent(
            event_type=EventType.DOCTOR_INBOUND,
            source=EventSource.PIPELINE,
        )

        event_id = await emit_event(event)

        assert event_id == ""

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_emit_event_no_data(self, mock_supabase):
        """Retorna string vazia quando nao ha data no response."""
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        event = BusinessEvent(
            event_type=EventType.HANDOFF_CREATED,
            source=EventSource.BACKEND,
        )

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
            {"id": "1", "event_type": "offer_made"},
            {"id": "2", "event_type": "offer_made"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        events = await get_events_by_type(EventType.OFFER_MADE, hours=24)

        assert len(events) == 2
        assert events[0]["event_type"] == "offer_made"

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_get_events_by_type_empty(self, mock_supabase):
        """Retorna lista vazia quando nao ha eventos."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        events = await get_events_by_type(EventType.SHIFT_COMPLETED, hours=24)

        assert events == []

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_get_events_by_type_error(self, mock_supabase):
        """Retorna lista vazia em caso de erro."""
        mock_supabase.table.side_effect = Exception("DB error")

        events = await get_events_by_type(EventType.OFFER_DECLINED, hours=24)

        assert events == []


class TestGetEventsForCliente:
    """Testes para busca por cliente."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_get_events_for_cliente(self, mock_supabase):
        """Busca eventos de um cliente."""
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "1", "event_type": "doctor_inbound", "cliente_id": "cliente-123"},
            {"id": "2", "event_type": "doctor_outbound", "cliente_id": "cliente-123"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = mock_response

        events = await get_events_for_cliente("cliente-123", hours=168)

        assert len(events) == 2


class TestGetFunnelCounts:
    """Testes para contagem de funil."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_get_funnel_counts(self, mock_supabase):
        """Conta eventos agrupados por tipo."""
        # Sprint 44 T04.7: Mocka RPC para falhar (cai no fallback)
        mock_supabase.rpc.side_effect = Exception("RPC not available")

        mock_response = MagicMock()
        mock_response.data = [
            {"event_type": "doctor_outbound"},
            {"event_type": "doctor_outbound"},
            {"event_type": "offer_made"},
            {"event_type": "offer_accepted"},
        ]
        mock_supabase.table.return_value.select.return_value.gte.return_value.limit.return_value.execute.return_value = mock_response

        counts = await get_funnel_counts(hours=24)

        assert counts["doctor_outbound"] == 2
        assert counts["offer_made"] == 1
        assert counts["offer_accepted"] == 1

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_get_funnel_counts_with_hospital(self, mock_supabase):
        """Filtra por hospital."""
        # Sprint 44 T04.7: Mocka RPC para falhar (cai no fallback)
        mock_supabase.rpc.side_effect = Exception("RPC not available")

        mock_response = MagicMock()
        mock_response.data = [{"event_type": "offer_made"}]
        mock_supabase.table.return_value.select.return_value.gte.return_value.limit.return_value.eq.return_value.execute.return_value = mock_response

        counts = await get_funnel_counts(hours=24, hospital_id="hospital-123")

        assert counts["offer_made"] == 1

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_get_funnel_counts_empty(self, mock_supabase):
        """Retorna dict vazio quando nao ha eventos."""
        # Sprint 44 T04.7: Mocka RPC para falhar (cai no fallback)
        mock_supabase.rpc.side_effect = Exception("RPC not available")

        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.gte.return_value.limit.return_value.execute.return_value = mock_response

        counts = await get_funnel_counts(hours=24)

        assert counts == {}

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_get_funnel_counts_error(self, mock_supabase):
        """Retorna dict vazio em caso de erro."""
        mock_supabase.table.side_effect = Exception("DB error")

        counts = await get_funnel_counts(hours=24)

        assert counts == {}


class TestBusinessEvent:
    """Testes para dataclass BusinessEvent."""

    def test_to_dict(self):
        """Serializa evento para dict."""
        event = BusinessEvent(
            event_type=EventType.OFFER_MADE,
            source=EventSource.BACKEND,
            cliente_id="cliente-123",
            vaga_id="vaga-456",
            hospital_id="hospital-789",
            event_props={"valor": 2000, "especialidade": "cardiologia"},
        )

        result = event.to_dict()

        assert result["event_type"] == "offer_made"
        assert result["source"] == "backend"
        assert result["cliente_id"] == "cliente-123"
        assert result["vaga_id"] == "vaga-456"
        assert result["hospital_id"] == "hospital-789"
        assert result["event_props"]["valor"] == 2000

    def test_to_dict_minimal(self):
        """Serializa evento minimo."""
        event = BusinessEvent(
            event_type=EventType.DOCTOR_INBOUND,
            source=EventSource.PIPELINE,
        )

        result = event.to_dict()

        assert result["event_type"] == "doctor_inbound"
        assert result["source"] == "pipeline"
        assert result["cliente_id"] is None
        assert result["event_props"] == {}


class TestEventType:
    """Testes para enum EventType."""

    def test_all_event_types_exist(self):
        """Todos os tipos esperados existem."""
        expected_types = [
            "doctor_inbound",
            "doctor_outbound",
            "offer_teaser_sent",
            "offer_made",
            "offer_accepted",
            "offer_declined",
            "handoff_created",
            "shift_completed",
        ]

        for expected in expected_types:
            assert any(e.value == expected for e in EventType)


class TestEventSource:
    """Testes para enum EventSource."""

    def test_all_sources_exist(self):
        """Todas as fontes esperadas existem."""
        expected_sources = ["pipeline", "backend", "db", "heuristic", "ops"]

        for expected in expected_sources:
            assert any(s.value == expected for s in EventSource)
