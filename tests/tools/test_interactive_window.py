"""
Testes para verificação de janela em mensagens interativas.

Sprint 67 (R10, Chunk 7b) — 7 testes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.tools.interactive_messages import (
    _enviar_interactive_ou_fallback,
)


class TestInteractiveWindowCheck:
    """Testes de verificação de janela para mensagens interativas."""

    @pytest.mark.asyncio
    async def test_sem_telefone_retorna_instrucao(self):
        """Sem telefone → instrução de fallback."""
        result = await _enviar_interactive_ou_fallback(
            medico=None,
            conversa=None,
            interactive_payload={"type": "button"},
            fallback_text="Escolha: 1. Sim 2. Não",
            tipo="buttons",
        )
        assert result["success"] is False
        assert "instrucao" in result
        assert "Escolha:" in result["instrucao"]

    @pytest.mark.asyncio
    async def test_medico_sem_telefone_retorna_instrucao(self):
        """Médico sem telefone → instrução de fallback."""
        result = await _enviar_interactive_ou_fallback(
            medico={"nome": "Dr. Carlos"},
            conversa=None,
            interactive_payload={"type": "button"},
            fallback_text="Texto fallback",
            tipo="buttons",
        )
        assert result["success"] is False
        assert "instrucao" in result

    @pytest.mark.asyncio
    async def test_com_telefone_tenta_enviar(self):
        """Com telefone, deve tentar enviar via outbound."""
        mock_result = MagicMock()
        mock_result.success = True

        with patch(
            "app.tools.interactive_messages.send_outbound_interactive",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await _enviar_interactive_ou_fallback(
                medico={"telefone": "5511999990001"},
                conversa={"id": "conv-123"},
                interactive_payload={"type": "button"},
                fallback_text="Fallback text",
                tipo="buttons",
            )

            assert result["success"] is True
            assert result["mensagem_enviada"] is True

    @pytest.mark.asyncio
    async def test_erro_envio_retorna_instrucao(self):
        """Erro no envio → instrução de fallback."""
        with patch(
            "app.tools.interactive_messages.send_outbound_interactive",
            new_callable=AsyncMock,
            side_effect=Exception("Connection error"),
        ):
            result = await _enviar_interactive_ou_fallback(
                medico={"telefone": "5511999990001"},
                conversa={"id": "conv-123"},
                interactive_payload={"type": "button"},
                fallback_text="Fallback text",
                tipo="buttons",
            )

            assert result["success"] is False
            assert "instrucao" in result

    @pytest.mark.asyncio
    async def test_envio_falha_retorna_instrucao(self):
        """Envio com success=False → instrução de fallback."""
        mock_result = MagicMock()
        mock_result.success = False

        with patch(
            "app.tools.interactive_messages.send_outbound_interactive",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await _enviar_interactive_ou_fallback(
                medico={"telefone": "5511999990001"},
                conversa={"id": "conv-123"},
                interactive_payload={"type": "list"},
                fallback_text="Fallback list",
                tipo="list",
            )

            assert result["success"] is False
            assert "instrucao" in result

    @pytest.mark.asyncio
    async def test_tipo_preservado_no_resultado(self):
        """O tipo do interactive deve ser preservado no resultado."""
        mock_result = MagicMock()
        mock_result.success = True

        with patch(
            "app.tools.interactive_messages.send_outbound_interactive",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await _enviar_interactive_ou_fallback(
                medico={"telefone": "5511999990001"},
                conversa=None,
                interactive_payload={"type": "cta_url"},
                fallback_text="https://link.com",
                tipo="cta_url",
            )

            assert result["tipo"] == "cta_url"

    @pytest.mark.asyncio
    async def test_import_error_fallback(self):
        """Se send_outbound_interactive falha, instrução de fallback."""
        with patch(
            "app.tools.interactive_messages.send_outbound_interactive",
            new_callable=AsyncMock,
            side_effect=ImportError("Module not found"),
        ):
            result = await _enviar_interactive_ou_fallback(
                medico={"telefone": "5511999990001"},
                conversa=None,
                interactive_payload={"type": "button"},
                fallback_text="Fallback",
                tipo="buttons",
            )

            assert result["success"] is False
            assert "instrucao" in result
