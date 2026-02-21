"""
Testes para MetaConversationAnalytics.

Sprint 67 (Epic 67.4, Chunk 6b) — 10 testes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_chain(data=None):
    mock = MagicMock()
    mock_resp = MagicMock()
    mock_resp.data = data or []

    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.eq.return_value = mock
    mock.gte.return_value = mock
    mock.lte.return_value = mock
    mock.execute.return_value = mock_resp
    return mock


class TestDeterminarCategoria:
    """Testes para detecção de categoria."""

    def test_dentro_janela_sem_template_eh_service(self):
        from app.services.meta.conversation_analytics import MetaConversationAnalytics

        ca = MetaConversationAnalytics()
        assert ca._determinar_categoria(template_name=None, is_within_window=True) == "service"

    def test_template_auth_eh_authentication(self):
        from app.services.meta.conversation_analytics import MetaConversationAnalytics

        ca = MetaConversationAnalytics()
        assert ca._determinar_categoria(template_name="otp_verification_code") == "authentication"

    def test_template_utility_eh_utility(self):
        from app.services.meta.conversation_analytics import MetaConversationAnalytics

        ca = MetaConversationAnalytics()
        assert ca._determinar_categoria(template_name="order_confirmation") == "utility"

    def test_template_generico_eh_marketing(self):
        from app.services.meta.conversation_analytics import MetaConversationAnalytics

        ca = MetaConversationAnalytics()
        assert ca._determinar_categoria(template_name="promo_natal") == "marketing"

    def test_sem_janela_sem_template_eh_marketing(self):
        from app.services.meta.conversation_analytics import MetaConversationAnalytics

        ca = MetaConversationAnalytics()
        assert ca._determinar_categoria(template_name=None, is_within_window=False) == "marketing"


class TestRegistrarCusto:
    """Testes para registro de custo."""

    @pytest.mark.asyncio
    async def test_registrar_custo_service_gratis(self):
        """Mensagem service deve ter custo 0."""
        with patch("app.services.meta.conversation_analytics.supabase") as mock_sb:
            mock_sb.table.return_value = _mock_chain()

            from app.services.meta.conversation_analytics import MetaConversationAnalytics

            ca = MetaConversationAnalytics()
            result = await ca.registrar_custo_mensagem(
                chip_id="chip-1",
                waba_id="waba-1",
                telefone="5511999990001",
                is_within_window=True,
            )

            assert result["category"] == "service"
            assert result["cost_usd"] == 0.0
            assert result["is_free"] is True

    @pytest.mark.asyncio
    async def test_registrar_custo_marketing(self):
        """Template marketing deve ter custo configurado."""
        with patch("app.services.meta.conversation_analytics.supabase") as mock_sb:
            mock_sb.table.return_value = _mock_chain()

            from app.services.meta.conversation_analytics import MetaConversationAnalytics

            ca = MetaConversationAnalytics()
            result = await ca.registrar_custo_mensagem(
                chip_id="chip-1",
                waba_id="waba-1",
                telefone="5511999990001",
                template_name="campanha_vagas",
            )

            assert result["category"] == "marketing"
            assert result["cost_usd"] == 0.0625
            assert result["is_free"] is False


class TestVerificarBudget:
    """Testes para verificação de budget."""

    @pytest.mark.asyncio
    async def test_verificar_budget_dentro_limite(self):
        """Deve indicar sem alerta quando dentro do budget."""
        cost_data = [
            {"message_category": "marketing", "cost_usd": "1.0", "is_free": False},
        ]
        with patch("app.services.meta.conversation_analytics.supabase") as mock_sb:
            mock_sb.table.return_value = _mock_chain(data=cost_data)

            from app.services.meta.conversation_analytics import MetaConversationAnalytics

            ca = MetaConversationAnalytics()
            result = await ca.verificar_budget()

            assert result["alerta"] is False
            assert result["excedido"] is False

    @pytest.mark.asyncio
    async def test_verificar_budget_excedido(self):
        """Deve indicar excedido quando acima do budget."""
        # Gerar dados que excedem o budget (50 USD padrão)
        cost_data = [
            {"message_category": "marketing", "cost_usd": "51.0", "is_free": False},
        ]
        with patch("app.services.meta.conversation_analytics.supabase") as mock_sb:
            mock_sb.table.return_value = _mock_chain(data=cost_data)

            from app.services.meta.conversation_analytics import MetaConversationAnalytics

            ca = MetaConversationAnalytics()
            result = await ca.verificar_budget()

            assert result["alerta"] is True
            assert result["excedido"] is True

    @pytest.mark.asyncio
    async def test_alertar_budget_sem_alerta(self):
        """Deve retornar None quando budget OK."""
        with patch("app.services.meta.conversation_analytics.supabase") as mock_sb:
            mock_sb.table.return_value = _mock_chain(data=[])

            from app.services.meta.conversation_analytics import MetaConversationAnalytics

            ca = MetaConversationAnalytics()
            result = await ca.alertar_budget_excedido()

            assert result is None
