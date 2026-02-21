"""
Testes para tools de mensagens interativas.

Sprint 67 (Chunk 7b) — 15 testes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.tools.interactive_messages import (
    TOOL_ENVIAR_OPCOES,
    TOOL_ENVIAR_LISTA,
    TOOL_ENVIAR_CTA,
    handle_enviar_opcoes,
    handle_enviar_lista,
    handle_enviar_cta,
    _gerar_payload_buttons,
    _gerar_payload_list,
    _gerar_payload_cta,
    _gerar_fallback_texto_opcoes,
    _gerar_fallback_texto_lista,
    _gerar_fallback_texto_cta,
)


class TestToolDefinitions:
    """Testes de schema das tools."""

    def test_enviar_opcoes_schema(self):
        assert TOOL_ENVIAR_OPCOES["name"] == "enviar_opcoes"
        props = TOOL_ENVIAR_OPCOES["input_schema"]["properties"]
        assert "texto" in props
        assert "opcoes" in props

    def test_enviar_lista_schema(self):
        assert TOOL_ENVIAR_LISTA["name"] == "enviar_lista"
        props = TOOL_ENVIAR_LISTA["input_schema"]["properties"]
        assert "texto" in props
        assert "itens" in props
        assert "botao_texto" in props

    def test_enviar_cta_schema(self):
        assert TOOL_ENVIAR_CTA["name"] == "enviar_cta"
        props = TOOL_ENVIAR_CTA["input_schema"]["properties"]
        assert "url" in props


class TestPayloadBuilders:
    """Testes de construção de payloads."""

    def test_gerar_payload_buttons(self):
        payload = _gerar_payload_buttons("Escolha:", ["Sim", "Não"])
        assert payload["type"] == "button"
        assert payload["body"]["text"] == "Escolha:"
        assert len(payload["action"]["buttons"]) == 2
        assert payload["action"]["buttons"][0]["reply"]["title"] == "Sim"

    def test_gerar_payload_buttons_trunca_titulo(self):
        payload = _gerar_payload_buttons("Msg", ["A" * 30])
        assert len(payload["action"]["buttons"][0]["reply"]["title"]) <= 20

    def test_gerar_payload_list(self):
        itens = [
            {"titulo": "Vaga 1", "descricao": "Hospital ABC"},
            {"titulo": "Vaga 2"},
        ]
        payload = _gerar_payload_list("Vagas:", "Ver vagas", itens)
        assert payload["type"] == "list"
        rows = payload["action"]["sections"][0]["rows"]
        assert len(rows) == 2
        assert rows[0]["title"] == "Vaga 1"
        assert rows[0]["description"] == "Hospital ABC"
        assert "description" not in rows[1]

    def test_gerar_payload_cta(self):
        payload = _gerar_payload_cta("Veja:", "Acessar", "https://revoluna.com")
        assert payload["type"] == "cta_url"
        assert payload["action"]["parameters"]["url"] == "https://revoluna.com"

    def test_gerar_payload_buttons_max_3(self):
        payload = _gerar_payload_buttons("Msg", ["A", "B", "C", "D"])
        assert len(payload["action"]["buttons"]) == 3


class TestFallbackGenerators:
    """Testes de geração de fallback text."""

    def test_fallback_opcoes(self):
        text = _gerar_fallback_texto_opcoes("Escolha:", ["Sim", "Não"])
        assert "Escolha:" in text
        assert "1. Sim" in text
        assert "2. Não" in text

    def test_fallback_lista(self):
        text = _gerar_fallback_texto_lista(
            "Vagas:",
            [{"titulo": "Vaga 1", "descricao": "Hospital ABC"}],
        )
        assert "Vagas:" in text
        assert "Vaga 1" in text
        assert "Hospital ABC" in text

    def test_fallback_cta(self):
        text = _gerar_fallback_texto_cta("Veja:", "https://revoluna.com")
        assert "Veja:" in text
        assert "https://revoluna.com" in text


class TestHandlers:
    """Testes dos handlers de tool."""

    @pytest.mark.asyncio
    async def test_handle_enviar_opcoes_sem_texto(self):
        """Deve retornar erro sem texto."""
        result = await handle_enviar_opcoes({"opcoes": ["Sim"]})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_handle_enviar_opcoes_sem_medico(self):
        """Deve retornar instrucao sem médico."""
        result = await handle_enviar_opcoes(
            {"texto": "Escolha:", "opcoes": ["Sim", "Não"]},
            medico=None,
        )
        assert result["success"] is False
        assert "instrucao" in result

    @pytest.mark.asyncio
    async def test_handle_enviar_lista_sem_itens(self):
        result = await handle_enviar_lista({"texto": "Vagas:"})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_handle_enviar_cta_sem_url(self):
        result = await handle_enviar_cta({"texto": "Veja:", "botao_texto": "Link"})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_handle_enviar_opcoes_com_medico_sem_telefone(self):
        """Deve retornar instrucao quando médico sem telefone."""
        result = await handle_enviar_opcoes(
            {"texto": "Escolha:", "opcoes": ["Sim", "Não"]},
            medico={"nome": "Dr. Carlos"},
        )
        assert result["success"] is False
        assert "instrucao" in result
