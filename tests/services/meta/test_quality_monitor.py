"""
Testes para o MetaQualityMonitor.

Sprint 67 (Epic 67.1, Chunk 5) — 18 testes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


def _mock_supabase_chain(data=None, count=None):
    """Helper para criar mock de cadeia Supabase."""
    mock = MagicMock()
    mock_resp = MagicMock()
    mock_resp.data = data or []
    mock_resp.count = count

    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.upsert.return_value = mock
    mock.eq.return_value = mock
    mock.in_.return_value = mock
    mock.not_.is_.return_value = mock
    mock.gte.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.execute.return_value = mock_resp
    return mock


SAMPLE_CHIP = {
    "id": "chip-001",
    "telefone": "5511999990001",
    "meta_phone_number_id": "phone-123",
    "meta_waba_id": "waba-456",
    "meta_access_token": "token-xyz",
    "meta_quality_rating": "GREEN",
    "trust_score": 50,
    "status": "active",
}


class TestMetaQualityMonitor:
    """Testes do MetaQualityMonitor."""

    @pytest.mark.asyncio
    async def test_verificar_quality_chips_sem_chips(self):
        """Deve retornar 0 verificados quando não há chips Meta."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb:
            mock_sb.table.return_value = _mock_supabase_chain(data=[])

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            result = await monitor.verificar_quality_chips()

            assert result["total"] == 0
            assert result["verificados"] == 0

    @pytest.mark.asyncio
    async def test_verificar_quality_chips_com_chips(self):
        """Deve verificar chips ativos."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb, \
             patch("app.services.meta.quality_monitor.get_http_client") as mock_http:

            # Mock Supabase
            chain = _mock_supabase_chain(data=[SAMPLE_CHIP])
            mock_sb.table.return_value = chain

            # Mock HTTP (Graph API)
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "quality_rating": "GREEN",
                "messaging_limit_tier": "TIER_1K",
            }
            mock_client.get.return_value = mock_resp
            mock_http.return_value = mock_client

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            result = await monitor.verificar_quality_chips()

            assert result["total"] == 1
            assert result["verificados"] == 1

    @pytest.mark.asyncio
    async def test_consultar_quality_api_sucesso(self):
        """Deve retornar quality e tier da API."""
        with patch("app.services.meta.quality_monitor.get_http_client") as mock_http:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "quality_rating": "YELLOW",
                "messaging_limit_tier": "TIER_250",
            }
            mock_client.get.return_value = mock_resp
            mock_http.return_value = mock_client

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            result = await monitor._consultar_quality_api(SAMPLE_CHIP)

            assert result["quality_rating"] == "YELLOW"
            assert result["messaging_tier"] == "TIER_250"

    @pytest.mark.asyncio
    async def test_consultar_quality_api_sem_token(self):
        """Deve retornar None sem token."""
        from app.services.meta.quality_monitor import MetaQualityMonitor

        monitor = MetaQualityMonitor()
        chip = {**SAMPLE_CHIP, "meta_access_token": None}
        result = await monitor._consultar_quality_api(chip)
        assert result is None

    @pytest.mark.asyncio
    async def test_consultar_quality_api_erro_http(self):
        """Deve retornar None em erro HTTP."""
        with patch("app.services.meta.quality_monitor.get_http_client") as mock_http:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            mock_client.get.return_value = mock_resp
            mock_http.return_value = mock_client

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            result = await monitor._consultar_quality_api(SAMPLE_CHIP)
            assert result is None

    @pytest.mark.asyncio
    async def test_registrar_quality(self):
        """Deve inserir no histórico."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb:
            chain = _mock_supabase_chain()
            mock_sb.table.return_value = chain

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            await monitor._registrar_quality(
                chip_id="chip-001",
                waba_id="waba-456",
                quality_rating="GREEN",
                previous_rating="YELLOW",
            )

            chain.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_degradar_chip(self):
        """Deve colocar chip em cooldown."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb:
            chain = _mock_supabase_chain()
            mock_sb.table.return_value = chain

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            await monitor._auto_degradar_chip(SAMPLE_CHIP, "RED", "GREEN")

            chain.update.assert_called_once()
            update_data = chain.update.call_args[0][0]
            assert update_data["status"] == "cooldown"
            assert update_data["trust_score"] == 0

    @pytest.mark.asyncio
    async def test_auto_recovery_chip_sem_antiflap(self):
        """Deve reativar chip quando não está em anti-flap."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb, \
             patch("app.services.meta.quality_monitor.verificar_anti_flap", return_value=False):

            chain = _mock_supabase_chain()
            mock_sb.table.return_value = chain

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            await monitor._auto_recovery_chip(SAMPLE_CHIP, "GREEN", "RED")

            chain.update.assert_called_once()
            update_data = chain.update.call_args[0][0]
            assert update_data["status"] == "active"
            assert update_data["trust_score"] == 30  # RED→GREEN = 30

    @pytest.mark.asyncio
    async def test_auto_recovery_chip_com_antiflap(self):
        """Deve NÃO reativar chip em anti-flap."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb, \
             patch("app.services.meta.quality_monitor.verificar_anti_flap", return_value=True):

            chain = _mock_supabase_chain()
            mock_sb.table.return_value = chain

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            await monitor._auto_recovery_chip(SAMPLE_CHIP, "GREEN", "RED")

            # Não deve chamar update
            chain.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_alertar_slack_quality_change(self):
        """Deve enviar notificação Slack."""
        mock_slack = AsyncMock()
        with patch.dict(
            "sys.modules",
            {"app.services.slack": MagicMock(enviar_notificacao_slack=mock_slack)},
        ):
            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            await monitor._alertar_slack(SAMPLE_CHIP, "GREEN", "RED")

            mock_slack.assert_called_once()
            call_text = mock_slack.call_args[0][0]
            assert "Quality Change" in call_text
            assert "RED" in call_text

    @pytest.mark.asyncio
    async def test_kill_switch_waba(self):
        """Deve desativar todos os chips de um WABA."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb:
            chain = _mock_supabase_chain(data=[{"id": "chip-001"}, {"id": "chip-002"}])
            mock_sb.table.return_value = chain

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            result = await monitor.kill_switch_waba("waba-456")

            assert result["waba_id"] == "waba-456"
            assert result["chips_desativados"] == 2

    @pytest.mark.asyncio
    async def test_obter_historico(self):
        """Deve retornar histórico de qualidade."""
        history_data = [
            {"chip_id": "chip-001", "quality_rating": "GREEN", "checked_at": "2026-01-01T00:00:00Z"},
        ]
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb:
            chain = _mock_supabase_chain(data=history_data)
            mock_sb.table.return_value = chain

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            result = await monitor.obter_historico(chip_id="chip-001")

            assert len(result) == 1
            assert result[0]["quality_rating"] == "GREEN"

    @pytest.mark.asyncio
    async def test_obter_historico_por_waba(self):
        """Deve filtrar histórico por WABA."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb:
            chain = _mock_supabase_chain(data=[])
            mock_sb.table.return_value = chain

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            result = await monitor.obter_historico(waba_id="waba-456")

            assert result == []
            chain.eq.assert_called()

    @pytest.mark.asyncio
    async def test_obter_ultimo_rating(self):
        """Deve retornar último rating de um chip."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb:
            chain = _mock_supabase_chain(data=[{"quality_rating": "YELLOW"}])
            mock_sb.table.return_value = chain

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            result = await monitor._obter_ultimo_rating("chip-001")

            assert result == "YELLOW"

    @pytest.mark.asyncio
    async def test_obter_ultimo_rating_sem_historico(self):
        """Deve retornar None sem histórico."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb:
            chain = _mock_supabase_chain(data=[])
            mock_sb.table.return_value = chain

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            result = await monitor._obter_ultimo_rating("chip-001")

            assert result is None

    @pytest.mark.asyncio
    async def test_detectar_padrao_degradacao(self):
        """Deve detectar padrão com 3+ degradações em 7 dias."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb:
            chain = _mock_supabase_chain(data=[], count=5)
            mock_sb.table.return_value = chain

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            # Should not raise
            await monitor._detectar_padrao_degradacao(SAMPLE_CHIP)

    @pytest.mark.asyncio
    async def test_verificar_chip_quality_change_triggers_degrade(self):
        """Quando qualidade cai, deve degradar chip."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb, \
             patch("app.services.meta.quality_monitor.get_http_client") as mock_http:

            chain = _mock_supabase_chain()
            mock_sb.table.return_value = chain

            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "quality_rating": "RED",
                "messaging_limit_tier": "TIER_50",
            }
            mock_client.get.return_value = mock_resp
            mock_http.return_value = mock_client

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()

            # Patch the alertar_slack and detectar_padrao to avoid side effects
            monitor._alertar_slack = AsyncMock()
            monitor._detectar_padrao_degradacao = AsyncMock()

            resultado = {"degradados": 0, "recuperados": 0, "erros": 0, "verificados": 0}
            await monitor._verificar_chip(SAMPLE_CHIP, resultado)

            assert resultado["degradados"] == 1

    @pytest.mark.asyncio
    async def test_verificar_chip_quality_no_change(self):
        """Quando qualidade não muda, não degrada nem recupera."""
        with patch("app.services.meta.quality_monitor.supabase") as mock_sb, \
             patch("app.services.meta.quality_monitor.get_http_client") as mock_http:

            chain = _mock_supabase_chain()
            mock_sb.table.return_value = chain

            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "quality_rating": "GREEN",
                "messaging_limit_tier": "TIER_1K",
            }
            mock_client.get.return_value = mock_resp
            mock_http.return_value = mock_client

            from app.services.meta.quality_monitor import MetaQualityMonitor

            monitor = MetaQualityMonitor()
            resultado = {"degradados": 0, "recuperados": 0, "erros": 0, "verificados": 0}
            await monitor._verificar_chip(SAMPLE_CHIP, resultado)

            assert resultado["degradados"] == 0
            assert resultado["recuperados"] == 0
