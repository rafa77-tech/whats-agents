"""
Testes de integração do cost_optimizer no chip sender.

Sprint 70 — Epic 70.2: Verifica que _enviar_meta_smart consulta
cost_optimizer e roteia para o método correto.
"""

import pytest
from unittest.mock import AsyncMock, patch
from dataclasses import dataclass

from app.services.whatsapp_providers.base import MessageResult


@dataclass
class FakeSendDecision:
    method: str
    template_name: str = None
    estimated_cost: float = 0.0
    reason: str = ""


@pytest.fixture
def mock_provider():
    """Provider mock com todos os métodos de envio."""
    p = AsyncMock()
    p.send_text.return_value = MessageResult(
        success=True, message_id="wamid.free", provider="meta"
    )
    p.send_text_mm_lite.return_value = MessageResult(
        success=True, message_id="wamid.mmlite", provider="meta"
    )
    p.send_template.return_value = MessageResult(
        success=True, message_id="wamid.tmpl", provider="meta"
    )
    return p


@pytest.fixture
def mock_chip():
    return {
        "id": "chip-meta-1",
        "telefone": "5511999990001",
        "provider": "meta",
        "meta_waba_id": "waba123",
        "meta_phone_number_id": "pn123",
        "meta_access_token": "tok",
    }


@pytest.fixture
def template_info():
    return {
        "name": "oferta_plantao_v2",
        "language": "pt_BR",
        "components": [
            {"type": "body", "parameters": [{"type": "text", "text": "Dr. Silva"}]}
        ],
    }


class TestEnviarMetaComCostOptimizer:
    """Testa _enviar_meta_com_cost_optimizer diretamente."""

    @pytest.mark.asyncio
    async def test_free_window_envia_send_text(self, mock_provider, mock_chip):
        """Quando cost_optimizer retorna free_window, usa send_text."""
        decision = FakeSendDecision(method="free_window", reason="Na janela")
        mock_optimizer = AsyncMock()
        mock_optimizer.decidir_tipo_envio = AsyncMock(return_value=decision)

        with (
            patch(
                "app.services.meta.cost_optimizer.cost_optimizer",
                mock_optimizer,
            ),
            patch(
                "app.services.meta.conversation_analytics.conversation_analytics"
            ) as mock_analytics,
        ):
            mock_analytics.registrar_custo_mensagem = AsyncMock()

            from app.services.chips.sender import _enviar_meta_com_cost_optimizer

            result = await _enviar_meta_com_cost_optimizer(
                mock_provider, mock_chip, "5511999998888", "Oi Dr!"
            )

            assert result.success
            assert result.message_id == "wamid.free"
            mock_provider.send_text.assert_called_once_with("5511999998888", "Oi Dr!")
            mock_provider.send_template.assert_not_called()

    @pytest.mark.asyncio
    async def test_mm_lite_envia_send_text_mm_lite(self, mock_provider, mock_chip):
        """Quando cost_optimizer retorna mm_lite, usa send_text_mm_lite."""
        decision = FakeSendDecision(method="mm_lite", reason="MM Lite habilitado")
        mock_optimizer = AsyncMock()
        mock_optimizer.decidir_tipo_envio = AsyncMock(return_value=decision)

        with (
            patch(
                "app.services.meta.cost_optimizer.cost_optimizer",
                mock_optimizer,
            ),
            patch(
                "app.services.meta.mm_lite.mm_lite_service"
            ) as mock_mm_lite,
            patch(
                "app.services.meta.conversation_analytics.conversation_analytics"
            ) as mock_analytics,
        ):
            mock_mm_lite.registrar_envio_mm_lite = AsyncMock(return_value={"id": "1"})
            mock_analytics.registrar_custo_mensagem = AsyncMock()

            from app.services.chips.sender import _enviar_meta_com_cost_optimizer

            result = await _enviar_meta_com_cost_optimizer(
                mock_provider, mock_chip, "5511999998888", "Oi Dr!"
            )

            assert result.success
            assert result.message_id == "wamid.mmlite"
            mock_provider.send_text_mm_lite.assert_called_once_with(
                "5511999998888", "Oi Dr!", mm_lite=True
            )
            mock_mm_lite.registrar_envio_mm_lite.assert_called_once()

    @pytest.mark.asyncio
    async def test_marketing_template_envia_send_template(
        self, mock_provider, mock_chip, template_info
    ):
        """Quando cost_optimizer retorna marketing_template, usa send_template."""
        decision = FakeSendDecision(
            method="marketing_template", reason="Template marketing"
        )
        mock_optimizer = AsyncMock()
        mock_optimizer.decidir_tipo_envio = AsyncMock(return_value=decision)

        with (
            patch(
                "app.services.meta.cost_optimizer.cost_optimizer",
                mock_optimizer,
            ),
            patch(
                "app.services.meta.conversation_analytics.conversation_analytics"
            ) as mock_analytics,
        ):
            mock_analytics.registrar_custo_mensagem = AsyncMock()

            from app.services.chips.sender import _enviar_meta_com_cost_optimizer

            result = await _enviar_meta_com_cost_optimizer(
                mock_provider,
                mock_chip,
                "5511999998888",
                "Oi Dr!",
                template_info=template_info,
            )

            assert result.success
            assert result.message_id == "wamid.tmpl"
            mock_provider.send_template.assert_called_once_with(
                "5511999998888",
                "oferta_plantao_v2",
                "pt_BR",
                template_info["components"],
            )

    @pytest.mark.asyncio
    async def test_template_requerido_sem_template_info_retorna_erro(
        self, mock_provider, mock_chip
    ):
        """Quando cost_optimizer pede template mas não há template_info, retorna erro."""
        decision = FakeSendDecision(
            method="utility_template", reason="Template utility"
        )
        mock_optimizer = AsyncMock()
        mock_optimizer.decidir_tipo_envio = AsyncMock(return_value=decision)

        with patch(
            "app.services.meta.cost_optimizer.cost_optimizer",
            mock_optimizer,
        ):
            from app.services.chips.sender import _enviar_meta_com_cost_optimizer

            result = await _enviar_meta_com_cost_optimizer(
                mock_provider, mock_chip, "5511999998888", "Oi Dr!"
            )

            assert not result.success
            assert result.error == "meta_fora_janela_sem_template"


class TestEnviarMetaFallback:
    """Testa _enviar_meta_fallback diretamente."""

    @pytest.mark.asyncio
    async def test_fallback_na_janela_envia_texto(self, mock_provider, mock_chip):
        """Na janela, envia texto direto."""
        with (
            patch(
                "app.services.meta.window_tracker.window_tracker"
            ) as mock_tracker,
            patch(
                "app.services.meta.conversation_analytics.conversation_analytics"
            ) as mock_analytics,
        ):
            mock_tracker.esta_na_janela = AsyncMock(return_value=True)
            mock_analytics.registrar_custo_mensagem = AsyncMock()

            from app.services.chips.sender import _enviar_meta_fallback

            result = await _enviar_meta_fallback(
                mock_provider, mock_chip, "5511999998888", "Oi Dr!"
            )

            assert result.success
            mock_provider.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_fora_janela_sem_template_erro(
        self, mock_provider, mock_chip
    ):
        """Fora da janela e sem template, retorna erro."""
        with patch(
            "app.services.meta.window_tracker.window_tracker"
        ) as mock_tracker:
            mock_tracker.esta_na_janela = AsyncMock(return_value=False)

            from app.services.chips.sender import _enviar_meta_fallback

            result = await _enviar_meta_fallback(
                mock_provider, mock_chip, "5511999998888", "Oi Dr!"
            )

            assert not result.success
            assert result.error == "meta_fora_janela_sem_template"

    @pytest.mark.asyncio
    async def test_fallback_fora_janela_com_template_envia(
        self, mock_provider, mock_chip, template_info
    ):
        """Fora da janela com template, envia via send_template."""
        with (
            patch(
                "app.services.meta.window_tracker.window_tracker"
            ) as mock_tracker,
            patch(
                "app.services.meta.conversation_analytics.conversation_analytics"
            ) as mock_analytics,
        ):
            mock_tracker.esta_na_janela = AsyncMock(return_value=False)
            mock_analytics.registrar_custo_mensagem = AsyncMock()

            from app.services.chips.sender import _enviar_meta_fallback

            result = await _enviar_meta_fallback(
                mock_provider,
                mock_chip,
                "5511999998888",
                "Oi Dr!",
                template_info=template_info,
            )

            assert result.success
            mock_provider.send_template.assert_called_once()


class TestEnviarMetaSmartRouting:
    """Testa que _enviar_meta_smart roteia para optimizer ou fallback."""

    @pytest.mark.asyncio
    async def test_com_optimizer_habilitado_chama_cost_optimizer(
        self, mock_provider, mock_chip
    ):
        """Com flag ligada, chama _enviar_meta_com_cost_optimizer."""
        decision = FakeSendDecision(method="free_window", reason="test")
        mock_optimizer = AsyncMock()
        mock_optimizer.decidir_tipo_envio = AsyncMock(return_value=decision)

        with (
            patch(
                "app.core.config.settings.META_COST_OPTIMIZER_ENABLED",
                True,
            ),
            patch(
                "app.services.meta.cost_optimizer.cost_optimizer",
                mock_optimizer,
            ),
            patch(
                "app.services.meta.conversation_analytics.conversation_analytics"
            ) as mock_analytics,
        ):
            mock_analytics.registrar_custo_mensagem = AsyncMock()

            from app.services.chips.sender import _enviar_meta_smart

            result = await _enviar_meta_smart(
                mock_provider, mock_chip, "5511999998888", "Oi Dr!"
            )

            assert result.success
            mock_optimizer.decidir_tipo_envio.assert_called_once()

    @pytest.mark.asyncio
    async def test_com_optimizer_desabilitado_usa_fallback(
        self, mock_provider, mock_chip
    ):
        """Com flag desligada, usa fallback com window_tracker."""
        with (
            patch(
                "app.core.config.settings.META_COST_OPTIMIZER_ENABLED",
                False,
            ),
            patch(
                "app.services.meta.window_tracker.window_tracker"
            ) as mock_tracker,
            patch(
                "app.services.meta.conversation_analytics.conversation_analytics"
            ) as mock_analytics,
        ):
            mock_tracker.esta_na_janela = AsyncMock(return_value=True)
            mock_analytics.registrar_custo_mensagem = AsyncMock()

            from app.services.chips.sender import _enviar_meta_smart

            result = await _enviar_meta_smart(
                mock_provider, mock_chip, "5511999998888", "Oi Dr!"
            )

            assert result.success
            mock_tracker.esta_na_janela.assert_called_once()
