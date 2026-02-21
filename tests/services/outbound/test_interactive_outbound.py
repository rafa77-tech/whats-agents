"""
Testes para envio outbound de mensagens interativas.

Sprint 67 (Chunk 7a) — 6 testes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.services.outbound.interactive import (
    send_outbound_interactive,
    _enviar_interactive_via_multi_chip,
)
from app.services.guardrails import (
    OutboundContext,
    OutboundMethod,
    OutboundChannel,
    ActorType,
)


def _make_ctx(**kwargs):
    defaults = {
        "cliente_id": "5511999990001",
        "actor_type": ActorType.BOT,
        "channel": OutboundChannel.WHATSAPP,
        "method": OutboundMethod.REPLY,
        "is_proactive": False,
    }
    defaults.update(kwargs)
    return OutboundContext(**defaults)


class TestEnviarInteractiveViaMultiChip:
    """Testes para _enviar_interactive_via_multi_chip."""

    @pytest.mark.asyncio
    async def test_sem_chip_retorna_fallback(self):
        """Sem chip disponível → fallback."""
        ctx = _make_ctx()
        mock_sel = MagicMock()
        mock_sel.selecionar_chip = AsyncMock(return_value=None)

        with patch("app.services.chips.selector.chip_selector", mock_sel):
            result = await _enviar_interactive_via_multi_chip(
                telefone="5511999990001",
                interactive_payload={"type": "button"},
                fallback_text="Fallback",
                ctx=ctx,
            )

        assert result["fallback"] is True

    @pytest.mark.asyncio
    async def test_chip_meta_na_janela_envia_interactive(self):
        """Chip Meta na janela → envia interactive."""
        ctx = _make_ctx()
        chip = {"id": "chip-1", "telefone": "5511999990002", "provider": "meta"}
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message_id = "msg-123"
        mock_result.provider = "meta"

        mock_sel = MagicMock()
        mock_sel.selecionar_chip = AsyncMock(return_value=chip)
        mock_provider = AsyncMock()
        mock_provider.send_interactive = AsyncMock(return_value=mock_result)
        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=True)

        with patch("app.services.chips.selector.chip_selector", mock_sel), \
             patch("app.services.whatsapp_providers.get_provider", return_value=mock_provider), \
             patch("app.services.meta.window_tracker.window_tracker", mock_wt):

            result = await _enviar_interactive_via_multi_chip(
                telefone="5511999990001",
                interactive_payload={"type": "button"},
                fallback_text="Fallback",
                ctx=ctx,
            )

        assert result["success"] is True
        mock_provider.send_interactive.assert_called_once()

    @pytest.mark.asyncio
    async def test_chip_meta_fora_janela_envia_fallback(self):
        """Chip Meta fora da janela → envia fallback text."""
        ctx = _make_ctx()
        chip = {"id": "chip-1", "telefone": "5511999990002", "provider": "meta"}
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message_id = "msg-123"
        mock_result.provider = "meta"

        mock_sel = MagicMock()
        mock_sel.selecionar_chip = AsyncMock(return_value=chip)
        mock_provider = AsyncMock()
        mock_provider.send_text = AsyncMock(return_value=mock_result)
        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=False)

        with patch("app.services.chips.selector.chip_selector", mock_sel), \
             patch("app.services.whatsapp_providers.get_provider", return_value=mock_provider), \
             patch("app.services.meta.window_tracker.window_tracker", mock_wt):

            result = await _enviar_interactive_via_multi_chip(
                telefone="5511999990001",
                interactive_payload={"type": "button"},
                fallback_text="Fallback text",
                ctx=ctx,
            )

        assert result["success"] is True
        mock_provider.send_text.assert_called_once_with("5511999990001", "Fallback text")

    @pytest.mark.asyncio
    async def test_chip_evolution_envia_fallback(self):
        """Chip Evolution → envia fallback text."""
        ctx = _make_ctx()
        chip = {"id": "chip-1", "telefone": "5511999990002", "provider": "evolution"}
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message_id = "msg-123"
        mock_result.provider = "evolution"

        mock_sel = MagicMock()
        mock_sel.selecionar_chip = AsyncMock(return_value=chip)
        mock_provider = AsyncMock()
        mock_provider.send_text = AsyncMock(return_value=mock_result)

        with patch("app.services.chips.selector.chip_selector", mock_sel), \
             patch("app.services.whatsapp_providers.get_provider", return_value=mock_provider):

            result = await _enviar_interactive_via_multi_chip(
                telefone="5511999990001",
                interactive_payload={"type": "button"},
                fallback_text="Fallback text",
                ctx=ctx,
            )

        assert result["success"] is True
        mock_provider.send_text.assert_called_once()


class TestSendOutboundInteractive:
    """Testes para send_outbound_interactive (integração)."""

    @pytest.mark.asyncio
    async def test_dev_allowlist_block(self):
        """Deve bloquear em DEV sem allowlist."""
        with patch(
            "app.services.outbound.interactive._verificar_dev_allowlist",
            return_value=(False, "dev_not_allowlisted"),
        ):
            result = await send_outbound_interactive(
                telefone="5511999990001",
                interactive_payload={"type": "button"},
                fallback_text="Fallback",
            )

            assert result.success is False

    @pytest.mark.asyncio
    async def test_dedup_block(self):
        """Deve deduplicar mensagem repetida."""
        with patch(
            "app.services.outbound.interactive._verificar_dev_allowlist",
            return_value=(True, ""),
        ), patch(
            "app.services.outbound.interactive.verificar_e_reservar",
            new_callable=AsyncMock,
            return_value=(False, "key-123", "duplicate"),
        ):
            result = await send_outbound_interactive(
                telefone="5511999990001",
                interactive_payload={"type": "button"},
                fallback_text="Fallback",
            )

            assert result.success is False
            assert result.deduped is True
