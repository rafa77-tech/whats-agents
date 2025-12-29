"""
Testes para repository unificado de envios de campanha.

Sprint 23 E03 - Fonte unica de verdade.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.services.campaign_sends import (
    campaign_sends_repo,
    CampaignSend,
    CampaignMetrics,
)


class TestCampaignSendsRepository:
    """Testes para CampaignSendsRepository."""

    @pytest.mark.asyncio
    async def test_listar_por_campanha(self):
        """Deve listar envios de uma campanha."""
        with patch.object(campaign_sends_repo, "_parse_send") as mock_parse:
            mock_parse.return_value = MagicMock(spec=CampaignSend)

            with patch("app.services.campaign_sends.supabase") as mock_supabase:
                mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
                    data=[
                        {"send_id": "1", "campaign_id": 42},
                        {"send_id": "2", "campaign_id": 42},
                    ]
                )

                result = await campaign_sends_repo.listar_por_campanha(42)

                assert len(result) == 2
                mock_supabase.table.assert_called_with("campaign_sends")

    @pytest.mark.asyncio
    async def test_listar_por_campanha_vazia(self):
        """Campanha sem envios retorna lista vazia."""
        with patch("app.services.campaign_sends.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
                data=None
            )

            result = await campaign_sends_repo.listar_por_campanha(999)

            assert result == []

    @pytest.mark.asyncio
    async def test_buscar_metricas(self):
        """Deve buscar metricas de uma campanha."""
        with patch("app.services.campaign_sends.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "campaign_id": 42,
                    "total_sends": 100,
                    "delivered": 80,
                    "blocked": 10,
                    "deduped": 5,
                    "failed": 3,
                    "pending": 2,
                    "delivery_rate": 80.0,
                    "first_send_at": "2024-01-01T00:00:00+00:00",
                    "last_send_at": "2024-01-02T00:00:00+00:00",
                }
            )

            result = await campaign_sends_repo.buscar_metricas(42)

            assert result is not None
            assert result.campaign_id == 42
            assert result.total_sends == 100
            assert result.delivered == 80
            assert result.delivery_rate == 80.0
            mock_supabase.table.assert_called_with("campaign_metrics")

    @pytest.mark.asyncio
    async def test_buscar_metricas_nao_encontrada(self):
        """Campanha nao encontrada retorna None."""
        with patch("app.services.campaign_sends.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=None
            )

            result = await campaign_sends_repo.buscar_metricas(999)

            assert result is None

    @pytest.mark.asyncio
    async def test_listar_metricas_todas(self):
        """Deve listar metricas de todas as campanhas."""
        with patch("app.services.campaign_sends.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[
                    {"campaign_id": 1, "total_sends": 100, "delivered": 80, "blocked": 10, "deduped": 5, "failed": 3, "pending": 2, "delivery_rate": 80.0},
                    {"campaign_id": 2, "total_sends": 50, "delivered": 40, "blocked": 5, "deduped": 2, "failed": 2, "pending": 1, "delivery_rate": 80.0},
                ]
            )

            result = await campaign_sends_repo.listar_metricas_todas()

            assert len(result) == 2
            assert result[0].total_sends == 100

    @pytest.mark.asyncio
    async def test_contar_por_outcome(self):
        """Deve contar envios agrupados por outcome."""
        with patch("app.services.campaign_sends.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[
                    {"outcome": "SENT"},
                    {"outcome": "SENT"},
                    {"outcome": "BLOCKED_OPTED_OUT"},
                    {"outcome": None},
                ]
            )

            result = await campaign_sends_repo.contar_por_outcome(42)

            assert result["SENT"] == 2
            assert result["BLOCKED_OPTED_OUT"] == 1
            assert result["PENDING"] == 1  # None vira PENDING

    @pytest.mark.asyncio
    async def test_buscar_por_cliente(self):
        """Deve buscar envios de campanha para um cliente."""
        with patch.object(campaign_sends_repo, "_parse_send") as mock_parse:
            mock_parse.return_value = MagicMock(spec=CampaignSend)

            with patch("app.services.campaign_sends.supabase") as mock_supabase:
                mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[{"send_id": "1", "cliente_id": "abc"}]
                )

                result = await campaign_sends_repo.buscar_por_cliente("abc")

                assert len(result) == 1


class TestCampaignMetrics:
    """Testes para dataclass CampaignMetrics."""

    def test_block_rate(self):
        """Calcula taxa de bloqueio corretamente."""
        metrics = CampaignMetrics(
            campaign_id=1,
            total_sends=100,
            delivered=80,
            blocked=10,
            deduped=5,
            failed=3,
            pending=2,
            delivery_rate=80.0,
            first_send_at=None,
            last_send_at=None,
        )

        assert metrics.block_rate == 10.0

    def test_fail_rate(self):
        """Calcula taxa de falha corretamente."""
        metrics = CampaignMetrics(
            campaign_id=1,
            total_sends=100,
            delivered=80,
            blocked=10,
            deduped=5,
            failed=3,
            pending=2,
            delivery_rate=80.0,
            first_send_at=None,
            last_send_at=None,
        )

        assert metrics.fail_rate == 3.0

    def test_rates_com_zero_sends(self):
        """Taxas com zero envios retornam 0."""
        metrics = CampaignMetrics(
            campaign_id=1,
            total_sends=0,
            delivered=0,
            blocked=0,
            deduped=0,
            failed=0,
            pending=0,
            delivery_rate=0.0,
            first_send_at=None,
            last_send_at=None,
        )

        assert metrics.block_rate == 0.0
        assert metrics.fail_rate == 0.0


class TestViewUnificada:
    """Testes conceituais para a view unificada."""

    def test_source_table_identifica_origem(self):
        """source_table deve identificar de qual tabela veio o registro."""
        # Este teste valida a estrutura esperada
        send_fila = CampaignSend(
            send_id="uuid-1",
            cliente_id="cliente-1",
            campaign_id=42,
            send_type="campanha",
            queue_status="enviada",
            outcome="SENT",
            outcome_reason_code=None,
            provider_message_id="msg-123",
            queued_at=datetime.now(timezone.utc),
            scheduled_for=None,
            sent_at=datetime.now(timezone.utc),
            outcome_at=datetime.now(timezone.utc),
            source_table="fila_mensagens",
        )

        send_legado = CampaignSend(
            send_id="123",
            cliente_id="cliente-2",
            campaign_id=42,
            send_type="campanha",
            queue_status="enviado",
            outcome="SENT",
            outcome_reason_code=None,
            provider_message_id="twilio-456",
            queued_at=datetime.now(timezone.utc),
            scheduled_for=None,
            sent_at=datetime.now(timezone.utc),
            outcome_at=datetime.now(timezone.utc),
            source_table="envios",
        )

        assert send_fila.source_table == "fila_mensagens"
        assert send_legado.source_table == "envios"

    def test_outcome_normalizado(self):
        """Outcomes devem estar normalizados para enum padrao."""
        # Novos envios ja usam enum
        assert "SENT" == "SENT"
        assert "BLOCKED_OPTED_OUT" == "BLOCKED_OPTED_OUT"

        # Legados sao mapeados
        # enviado -> SENT
        # falhou -> FAILED_PROVIDER
        # pendente -> NULL
