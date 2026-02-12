"""
Testes para FAILED_NO_CAPACITY no outbound.

Issue #85: Fallback para Evolution desperdiça retries quando chips estão no limite.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.services.outbound import send_outbound_message, OutboundResult
from app.services.guardrails import (
    OutboundContext,
    OutboundChannel,
    OutboundMethod,
    ActorType,
    SendOutcome,
)


@pytest.fixture
def ctx_campanha():
    """Contexto de campanha para testes."""
    return OutboundContext(
        cliente_id="cliente-abc",
        actor_type=ActorType.SYSTEM,
        channel=OutboundChannel.JOB,
        method=OutboundMethod.CAMPAIGN,
        is_proactive=True,
        campaign_id="42",
        conversation_id="conv-xyz",
    )


class TestMultiChipNoCapacity:
    """Testes de no-capacity quando multi-chip está habilitado."""

    @pytest.mark.asyncio
    @patch("app.services.outbound._finalizar_envio", new_callable=AsyncMock)
    @patch("app.services.outbound.marcar_falha", new_callable=AsyncMock)
    @patch("app.services.outbound.marcar_enviado", new_callable=AsyncMock)
    @patch("app.services.outbound.verificar_e_reservar", new_callable=AsyncMock)
    @patch("app.services.outbound.check_outbound_guardrails")
    @patch("app.services.outbound._verificar_dev_allowlist")
    @patch("app.services.outbound._enviar_via_multi_chip", new_callable=AsyncMock)
    @patch("app.services.outbound._is_multi_chip_enabled")
    async def test_multi_chip_no_capacity_nao_faz_fallback_evolution(
        self,
        mock_multi_enabled,
        mock_enviar_multi,
        mock_dev_allowlist,
        mock_guardrails,
        mock_dedupe,
        mock_marcar_enviado,
        mock_marcar_falha,
        mock_finalizar,
        ctx_campanha,
    ):
        """Quando chip selector retorna None, não faz fallback para Evolution e retorna FAILED_NO_CAPACITY."""
        mock_multi_enabled.return_value = True
        mock_dev_allowlist.return_value = (True, None)
        mock_dedupe.return_value = (True, "dedupe-key-123", None)

        guardrail_result = MagicMock()
        guardrail_result.is_blocked = False
        guardrail_result.human_bypass = False
        mock_guardrails.return_value = guardrail_result

        # Multi-chip retorna fallback=True (sem chip disponível)
        mock_enviar_multi.return_value = {"fallback": True}

        result = await send_outbound_message(
            telefone="5511999999999",
            texto="Oi Dr!",
            ctx=ctx_campanha,
        )

        assert not result.success
        assert result.outcome == SendOutcome.FAILED_NO_CAPACITY
        assert result.outcome_reason_code == "no_capacity:chips_no_limite"
        mock_marcar_falha.assert_called_once_with("dedupe-key-123", "no_capacity")

    @pytest.mark.asyncio
    @patch("app.services.outbound._finalizar_envio", new_callable=AsyncMock)
    @patch("app.services.outbound.marcar_falha", new_callable=AsyncMock)
    @patch("app.services.outbound.marcar_enviado", new_callable=AsyncMock)
    @patch("app.services.outbound.verificar_e_reservar", new_callable=AsyncMock)
    @patch("app.services.outbound.check_outbound_guardrails")
    @patch("app.services.outbound._verificar_dev_allowlist")
    @patch("app.services.outbound.evolution")
    @patch("app.services.outbound._is_multi_chip_enabled")
    async def test_multi_chip_desabilitado_faz_fallback_normal(
        self,
        mock_multi_enabled,
        mock_evolution,
        mock_dev_allowlist,
        mock_guardrails,
        mock_dedupe,
        mock_marcar_enviado,
        mock_marcar_falha,
        mock_finalizar,
        ctx_campanha,
    ):
        """Quando multi-chip está desabilitado, fallback para Evolution funciona normalmente."""
        mock_multi_enabled.return_value = False
        mock_dev_allowlist.return_value = (True, None)
        mock_dedupe.return_value = (True, "dedupe-key-456", None)

        guardrail_result = MagicMock()
        guardrail_result.is_blocked = False
        guardrail_result.human_bypass = False
        mock_guardrails.return_value = guardrail_result

        # Evolution envia com sucesso
        mock_evolution.enviar_mensagem = AsyncMock(
            return_value={"key": {"id": "evo-msg-123"}}
        )

        result = await send_outbound_message(
            telefone="5511999999999",
            texto="Oi Dr!",
            ctx=ctx_campanha,
        )

        assert result.success
        assert result.outcome == SendOutcome.SENT
        mock_evolution.enviar_mensagem.assert_called_once()
