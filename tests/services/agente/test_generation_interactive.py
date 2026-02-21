"""
Testes para integração de tools interativas no generation.py.

Sprint 67 (Chunk 8) — 5 testes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agente.generation import (
    JULIA_TOOLS,
    processar_tool_call,
)


class TestInteractiveToolsRegistration:
    """Verifica que tools interativas estão registradas."""

    def test_julia_tools_inclui_interactive(self):
        """JULIA_TOOLS deve conter as 3 tools interativas."""
        tool_names = [t["name"] for t in JULIA_TOOLS]
        assert "enviar_opcoes" in tool_names
        assert "enviar_lista" in tool_names
        assert "enviar_cta" in tool_names

    def test_julia_tools_tem_10_tools(self):
        """JULIA_TOOLS deve ter 10 tools no total."""
        assert len(JULIA_TOOLS) == 10

    def test_tools_interativas_tem_input_schema(self):
        """Cada tool interativa deve ter input_schema válido."""
        interactive_names = {"enviar_opcoes", "enviar_lista", "enviar_cta"}
        for tool in JULIA_TOOLS:
            if tool["name"] in interactive_names:
                assert "input_schema" in tool
                assert tool["input_schema"]["type"] == "object"
                assert "required" in tool["input_schema"]


class TestInteractiveToolHandlers:
    """Verifica que handlers interativos funcionam via processar_tool_call."""

    @pytest.mark.asyncio
    async def test_handler_enviar_opcoes_chamado(self):
        """processar_tool_call deve rotear para handle_enviar_opcoes."""
        with patch(
            "app.services.agente.generation.handle_enviar_opcoes",
            new_callable=AsyncMock,
            return_value={"success": True, "mensagem_enviada": True},
        ) as mock_handler:
            result = await processar_tool_call(
                "enviar_opcoes",
                {"texto": "Confirma?", "opcoes": ["Sim", "Não"]},
                {"telefone": "5511999990001"},
                {"id": "conv-1"},
            )
            mock_handler.assert_called_once()
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_handler_tool_desconhecida(self):
        """Tool desconhecida deve retornar erro."""
        result = await processar_tool_call(
            "tool_inexistente",
            {},
            {},
            {},
        )
        assert result["success"] is False
        assert "desconhecida" in result["error"]
