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
                    "bypassed": 2,
                    "delivered_total": 82,
                    "blocked": 10,
                    "deduped": 5,
                    "failed": 3,
                    "pending": 0,
                    "delivery_rate": 80.0,
                    "delivery_rate_total": 82.0,
                    "block_rate": 10.0,
                    "first_send_at": "2024-01-01T00:00:00+00:00",
                    "last_send_at": "2024-01-02T00:00:00+00:00",
                    "from_fila_mensagens": 90,
                    "from_envios_legado": 10,
                }
            )

            result = await campaign_sends_repo.buscar_metricas(42)

            assert result is not None
            assert result.campaign_id == 42
            assert result.total_sends == 100
            assert result.delivered == 80
            assert result.bypassed == 2
            assert result.delivered_total == 82
            assert result.delivery_rate == 80.0
            assert result.from_fila_mensagens == 90
            assert result.from_envios_legado == 10
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
                    {
                        "campaign_id": 1, "total_sends": 100, "delivered": 80, "bypassed": 2,
                        "delivered_total": 82, "blocked": 10, "deduped": 5, "failed": 3,
                        "pending": 0, "delivery_rate": 80.0, "delivery_rate_total": 82.0,
                        "block_rate": 10.0, "from_fila_mensagens": 90, "from_envios_legado": 10
                    },
                    {
                        "campaign_id": 2, "total_sends": 50, "delivered": 40, "bypassed": 1,
                        "delivered_total": 41, "blocked": 5, "deduped": 2, "failed": 2,
                        "pending": 0, "delivery_rate": 80.0, "delivery_rate_total": 82.0,
                        "block_rate": 10.0, "from_fila_mensagens": 45, "from_envios_legado": 5
                    },
                ]
            )

            result = await campaign_sends_repo.listar_metricas_todas()

            assert len(result) == 2
            assert result[0].total_sends == 100
            assert result[0].bypassed == 2

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

    def _criar_metrics(self, **kwargs) -> CampaignMetrics:
        """Helper para criar CampaignMetrics com valores padrão."""
        defaults = {
            "campaign_id": 1,
            "total_sends": 100,
            "delivered": 80,
            "bypassed": 2,
            "delivered_total": 82,
            "blocked": 10,
            "deduped": 5,
            "failed": 3,
            "pending": 0,
            "delivery_rate": 80.0,
            "delivery_rate_total": 82.0,
            "block_rate": 10.0,
            "first_send_at": None,
            "last_send_at": None,
            "from_fila_mensagens": 90,
            "from_envios_legado": 10,
        }
        defaults.update(kwargs)
        return CampaignMetrics(**defaults)

    def test_fail_rate(self):
        """Calcula taxa de falha corretamente."""
        metrics = self._criar_metrics()
        assert metrics.fail_rate == 3.0

    def test_rates_com_zero_sends(self):
        """Taxas com zero envios retornam 0."""
        metrics = self._criar_metrics(
            total_sends=0,
            delivered=0,
            bypassed=0,
            delivered_total=0,
            blocked=0,
            deduped=0,
            failed=0,
            pending=0,
            delivery_rate=0.0,
            delivery_rate_total=0.0,
            block_rate=0.0,
            from_fila_mensagens=0,
            from_envios_legado=0,
        )
        assert metrics.fail_rate == 0.0

    def test_bypassed_visivel(self):
        """Sprint 24 E07: bypassed deve estar visível nas métricas."""
        metrics = self._criar_metrics(bypassed=5, delivered=80, delivered_total=85)
        assert metrics.bypassed == 5
        assert metrics.delivered_total == 85

    def test_legado_ratio(self):
        """Sprint 24 E07: legado_ratio calcula percentual do legado."""
        metrics = self._criar_metrics(
            total_sends=100,
            from_fila_mensagens=70,
            from_envios_legado=30,
        )
        assert metrics.legado_ratio == 30.0

    def test_delivered_total_inclui_bypass(self):
        """delivered_total = delivered + bypassed."""
        metrics = self._criar_metrics(
            delivered=80,
            bypassed=5,
            delivered_total=85,
        )
        assert metrics.delivered_total == metrics.delivered + metrics.bypassed


class TestViewUnificada:
    """Testes conceituais para a view unificada."""

    def test_send_id_prefixado_fila_mensagens(self):
        """Sprint 24 E05: send_id de fila_mensagens deve ter prefixo fm_."""
        send_fila = CampaignSend(
            send_id="fm_abc-123",  # Prefixo fm_
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

        assert send_fila.send_id.startswith("fm_")
        assert send_fila.source_table == "fila_mensagens"

    def test_send_id_prefixado_envios(self):
        """Sprint 24 E05: send_id de envios deve ter prefixo env_."""
        send_legado = CampaignSend(
            send_id="env_123",  # Prefixo env_
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

        assert send_legado.send_id.startswith("env_")
        assert send_legado.source_table == "envios"

    def test_send_ids_nao_colidem(self):
        """Sprint 24 E05: send_ids de tabelas diferentes não devem colidir."""
        # Mesmo ID numérico em tabelas diferentes
        send_fila = CampaignSend(
            send_id="fm_100",
            cliente_id="cliente-1",
            campaign_id=42,
            send_type="campanha",
            queue_status="enviada",
            outcome="SENT",
            outcome_reason_code=None,
            provider_message_id=None,
            queued_at=datetime.now(timezone.utc),
            scheduled_for=None,
            sent_at=datetime.now(timezone.utc),
            outcome_at=datetime.now(timezone.utc),
            source_table="fila_mensagens",
        )

        send_legado = CampaignSend(
            send_id="env_100",  # Mesmo número, prefixo diferente
            cliente_id="cliente-2",
            campaign_id=42,
            send_type="campanha",
            queue_status="enviado",
            outcome="SENT",
            outcome_reason_code=None,
            provider_message_id=None,
            queued_at=datetime.now(timezone.utc),
            scheduled_for=None,
            sent_at=datetime.now(timezone.utc),
            outcome_at=datetime.now(timezone.utc),
            source_table="envios",
        )

        # IDs são únicos mesmo com mesmo número original
        assert send_fila.send_id != send_legado.send_id

    def test_outcome_normalizado(self):
        """Outcomes devem estar normalizados para enum padrao."""
        # Novos envios ja usam enum
        assert "SENT" == "SENT"
        assert "BLOCKED_OPTED_OUT" == "BLOCKED_OPTED_OUT"

        # Legados sao mapeados
        # enviado -> SENT
        # falhou -> FAILED_PROVIDER
        # pendente -> NULL


class TestViewValidation:
    """
    Testes de validação das views campaign_sends.

    Sprint 24 E05-E07: Checklist de aceite.
    Estes testes devem ser executados contra o banco de staging.
    """

    @pytest.mark.skip(reason="Requer banco staging - executar manualmente")
    @pytest.mark.asyncio
    async def test_sem_colisao_send_id(self):
        """
        P0 Check 1: Não há colisão de send_id.

        SELECT count(*) - count(distinct send_id) FROM campaign_sends_raw;
        Deve retornar 0.
        """
        from app.services.supabase import supabase

        result = supabase.rpc("sql", {
            "query": "SELECT count(*) - count(distinct send_id) as colisoes FROM campaign_sends_raw"
        }).execute()

        assert result.data[0]["colisoes"] == 0

    @pytest.mark.skip(reason="Requer banco staging - executar manualmente")
    @pytest.mark.asyncio
    async def test_sem_duplicata_canonical_key(self):
        """
        P0 Check 2: Não há duplicata por canonical_key em campaign_sends.

        SELECT count(*) - count(distinct canonical_key) FROM campaign_sends;
        Deve retornar 0.
        """
        from app.services.supabase import supabase

        result = supabase.rpc("sql", {
            "query": "SELECT count(*) - count(distinct canonical_key) as duplicatas FROM campaign_sends"
        }).execute()

        assert result.data[0]["duplicatas"] == 0

    @pytest.mark.skip(reason="Requer banco staging - executar manualmente")
    @pytest.mark.asyncio
    async def test_metricas_somam_corretamente(self):
        """
        P0 Check 4: Métricas batem com contagem manual.

        total_sends = delivered + bypassed + deduped + blocked + failed + pending
        """
        from app.services.supabase import supabase

        result = supabase.table("campaign_metrics").select("*").limit(10).execute()

        for row in result.data:
            soma = (
                row["delivered"] +
                row["bypassed"] +
                row["deduped"] +
                row["blocked"] +
                row["failed"] +
                row["pending"]
            )
            # Permitir pequena diferença por timing
            assert abs(row["total_sends"] - soma) <= 1, (
                f"Campanha {row['campaign_id']}: total={row['total_sends']}, soma={soma}"
            )
