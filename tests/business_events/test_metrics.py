"""
Testes para métricas de funil.

Sprint 17 - E06
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.business_events.metrics import (
    get_funnel_metrics,
    get_funnel_by_hospital,
    get_funnel_trend,
    get_top_doctors,
    get_conversion_time,
    FunnelMetrics,
)


class TestFunnelMetrics:
    """Testes para FunnelMetrics dataclass."""

    def test_to_dict_completo(self):
        """Serializa corretamente para dict."""
        metrics = FunnelMetrics(
            period_hours=24,
            hospital_id="hospital-123",
            doctor_outbound=100,
            doctor_inbound=30,
            offer_made=20,
            offer_accepted=10,
            shift_completed=8,
            response_rate=30.0,
            conversion_rate=50.0,
            completion_rate=80.0,
            overall_success=8.0,
        )

        result = metrics.to_dict()

        assert result["period_hours"] == 24
        assert result["hospital_id"] == "hospital-123"
        assert result["counts"]["doctor_outbound"] == 100
        assert result["counts"]["doctor_inbound"] == 30
        assert result["rates"]["response_rate"] == 30.0
        assert result["rates"]["conversion_rate"] == 50.0

    def test_to_dict_valores_default(self):
        """Serializa com valores default."""
        metrics = FunnelMetrics(period_hours=24)

        result = metrics.to_dict()

        assert result["period_hours"] == 24
        assert result["hospital_id"] is None
        assert result["counts"]["doctor_outbound"] == 0
        assert result["rates"]["response_rate"] == 0.0


class TestGetFunnelMetrics:
    """Testes para get_funnel_metrics."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_calcula_taxas_corretamente(self, mock_supabase):
        """Calcula taxas de conversão corretamente."""
        mock_response = MagicMock()
        mock_response.data = [
            {"event_type": "doctor_outbound", "count": 100},
            {"event_type": "doctor_inbound", "count": 30},
            {"event_type": "offer_made", "count": 20},
            {"event_type": "offer_accepted", "count": 10},
            {"event_type": "shift_completed", "count": 8},
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        metrics = await get_funnel_metrics(hours=24)

        assert metrics.doctor_outbound == 100
        assert metrics.doctor_inbound == 30
        assert metrics.response_rate == 30.0  # 30/100 * 100
        assert metrics.conversion_rate == 50.0  # 10/20 * 100
        assert metrics.completion_rate == 80.0  # 8/10 * 100
        assert metrics.overall_success == 8.0  # 8/100 * 100

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_trata_divisao_por_zero(self, mock_supabase):
        """Não divide por zero."""
        mock_response = MagicMock()
        mock_response.data = []  # Sem eventos
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        metrics = await get_funnel_metrics(hours=24)

        assert metrics.response_rate == 0.0
        assert metrics.conversion_rate == 0.0
        assert metrics.completion_rate == 0.0
        assert metrics.overall_success == 0.0

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_filtra_por_hospital(self, mock_supabase):
        """Passa hospital_id para a função SQL."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        await get_funnel_metrics(hours=24, hospital_id="hospital-123")

        mock_supabase.rpc.assert_called_with(
            "count_business_events",
            {"p_hours": 24, "p_hospital_id": "hospital-123"}
        )

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_trata_erro(self, mock_supabase):
        """Retorna métricas vazias em caso de erro."""
        mock_supabase.rpc.side_effect = Exception("DB Error")

        metrics = await get_funnel_metrics(hours=24)

        assert metrics.doctor_outbound == 0
        assert metrics.response_rate == 0.0

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_preenche_todos_tipos_evento(self, mock_supabase):
        """Preenche todos os tipos de evento corretamente."""
        mock_response = MagicMock()
        mock_response.data = [
            {"event_type": "doctor_outbound", "count": 100},
            {"event_type": "doctor_inbound", "count": 50},
            {"event_type": "offer_teaser_sent", "count": 30},
            {"event_type": "offer_made", "count": 20},
            {"event_type": "offer_declined", "count": 5},
            {"event_type": "offer_accepted", "count": 15},
            {"event_type": "handoff_created", "count": 3},
            {"event_type": "shift_completed", "count": 12},
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        metrics = await get_funnel_metrics(hours=24)

        assert metrics.doctor_outbound == 100
        assert metrics.doctor_inbound == 50
        assert metrics.offer_teaser_sent == 30
        assert metrics.offer_made == 20
        assert metrics.offer_declined == 5
        assert metrics.offer_accepted == 15
        assert metrics.handoff_created == 3
        assert metrics.shift_completed == 12


class TestGetFunnelByHospital:
    """Testes para get_funnel_by_hospital."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.get_funnel_metrics")
    @patch("app.services.business_events.metrics.supabase")
    async def test_retorna_lista_por_hospital(self, mock_supabase, mock_get_metrics):
        """Retorna métricas por hospital."""
        # Mock da query de hospitais
        mock_response = MagicMock()
        mock_response.data = [
            {"hospital_id": "hosp-1"},
            {"hospital_id": "hosp-2"},
            {"hospital_id": "hosp-1"},  # Duplicado
        ]
        mock_supabase.table.return_value.select.return_value.gte.return_value.not_.is_.return_value.execute.return_value = mock_response

        # Mock das métricas
        mock_get_metrics.return_value = FunnelMetrics(
            period_hours=24,
            hospital_id="hosp-1",
            overall_success=10.0,
        )

        result = await get_funnel_by_hospital(hours=24)

        # Deve ter 2 hospitais (dedupe)
        assert len(result) == 2

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_trata_erro(self, mock_supabase):
        """Retorna lista vazia em caso de erro."""
        mock_supabase.table.side_effect = Exception("DB Error")

        result = await get_funnel_by_hospital(hours=24)

        assert result == []


class TestGetFunnelTrend:
    """Testes para get_funnel_trend."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_retorna_tendencia_diaria(self, mock_supabase):
        """Retorna contagens por dia."""
        mock_response = MagicMock()
        mock_response.data = [
            {"event_type": "doctor_outbound"},
            {"event_type": "doctor_inbound"},
            {"event_type": "doctor_outbound"},
        ]
        mock_supabase.table.return_value.select.return_value.gte.return_value.lt.return_value.execute.return_value = mock_response

        result = await get_funnel_trend(days=3)

        assert len(result) == 3
        for day_data in result:
            assert "date" in day_data
            assert "counts" in day_data

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_ordena_cronologicamente(self, mock_supabase):
        """Retorna em ordem cronológica."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.gte.return_value.lt.return_value.execute.return_value = mock_response

        result = await get_funnel_trend(days=3)

        # A lista deve estar em ordem cronológica (do mais antigo para o mais recente)
        if len(result) >= 2:
            assert result[0]["date"] < result[-1]["date"]


class TestGetTopDoctors:
    """Testes para get_top_doctors."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_retorna_top_medicos(self, mock_supabase):
        """Retorna médicos ordenados por atividade."""
        mock_response = MagicMock()
        mock_response.data = [
            {"cliente_id": "doc-1"},
            {"cliente_id": "doc-1"},
            {"cliente_id": "doc-1"},
            {"cliente_id": "doc-2"},
            {"cliente_id": "doc-2"},
            {"cliente_id": "doc-3"},
        ]
        mock_supabase.table.return_value.select.return_value.gte.return_value.not_.is_.return_value.execute.return_value = mock_response

        result = await get_top_doctors(hours=168, limit=50)

        assert len(result) == 3
        assert result[0]["cliente_id"] == "doc-1"
        assert result[0]["events"] == 3
        assert result[1]["cliente_id"] == "doc-2"
        assert result[1]["events"] == 2

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_respeita_limite(self, mock_supabase):
        """Respeita o limite de resultados."""
        mock_response = MagicMock()
        mock_response.data = [
            {"cliente_id": f"doc-{i}"} for i in range(100)
        ]
        mock_supabase.table.return_value.select.return_value.gte.return_value.not_.is_.return_value.execute.return_value = mock_response

        result = await get_top_doctors(hours=168, limit=10)

        assert len(result) == 10


class TestGetConversionTime:
    """Testes para get_conversion_time."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_calcula_tempo_medio(self, mock_supabase):
        """Calcula tempo médio de conversão."""
        mock_response = MagicMock()
        mock_response.data = [
            {"vaga_id": "vaga-1", "event_type": "offer_made", "ts": "2025-01-10T10:00:00Z"},
            {"vaga_id": "vaga-1", "event_type": "offer_accepted", "ts": "2025-01-10T12:00:00Z"},
            {"vaga_id": "vaga-1", "event_type": "shift_completed", "ts": "2025-01-11T08:00:00Z"},
        ]
        mock_supabase.table.return_value.select.return_value.gte.return_value.not_.is_.return_value.in_.return_value.execute.return_value = mock_response

        result = await get_conversion_time(hours=720)

        assert result["avg_hours_made_to_accepted"] == 2.0  # 2 horas
        assert result["avg_hours_accepted_to_completed"] == 20.0  # 20 horas
        assert result["sample_size_made_to_accepted"] == 1
        assert result["sample_size_accepted_to_completed"] == 1

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_sem_dados(self, mock_supabase):
        """Retorna None quando não há dados."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.gte.return_value.not_.is_.return_value.in_.return_value.execute.return_value = mock_response

        result = await get_conversion_time(hours=720)

        assert result["avg_hours_made_to_accepted"] is None
        assert result["avg_hours_accepted_to_completed"] is None
        assert result["sample_size_made_to_accepted"] == 0
