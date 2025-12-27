"""
Testes para o classificador heurístico.

Sprint 14 - E03 - S03.4
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.grupos.classificador import (
    buscar_mensagens_pendentes,
    atualizar_resultado_heuristica,
    classificar_batch_heuristica,
    classificar_mensagem_individual,
)
from app.services.grupos.heuristica import ResultadoHeuristica


@pytest.fixture
def mock_supabase_classificador():
    """Mock do Supabase para o classificador."""
    with patch("app.services.grupos.classificador.supabase") as mock:
        mock.table.return_value = mock
        mock.select.return_value = mock
        mock.update.return_value = mock
        mock.eq.return_value = mock
        mock.order.return_value = mock
        mock.limit.return_value = mock
        mock.execute.return_value = MagicMock(data=[])

        yield mock


class TestBuscarMensagensPendentes:
    """Testes para buscar_mensagens_pendentes."""

    @pytest.mark.asyncio
    async def test_busca_mensagens(self, mock_supabase_classificador):
        """Deve buscar mensagens com status pendente."""
        mock_supabase_classificador.execute.return_value.data = [
            {"id": str(uuid4()), "texto": "Plantão disponível"},
            {"id": str(uuid4()), "texto": "Vaga urgente"},
        ]

        resultado = await buscar_mensagens_pendentes(limite=10)

        assert len(resultado) == 2
        mock_supabase_classificador.table.assert_called_with("mensagens_grupo")
        mock_supabase_classificador.eq.assert_called_with("status", "pendente")

    @pytest.mark.asyncio
    async def test_busca_vazia(self, mock_supabase_classificador):
        """Deve retornar lista vazia se não houver mensagens."""
        mock_supabase_classificador.execute.return_value.data = []

        resultado = await buscar_mensagens_pendentes()

        assert resultado == []


class TestAtualizarResultadoHeuristica:
    """Testes para atualizar_resultado_heuristica."""

    @pytest.mark.asyncio
    async def test_atualiza_passou(self, mock_supabase_classificador):
        """Deve atualizar status para heuristica_passou."""
        mensagem_id = uuid4()
        resultado = ResultadoHeuristica(
            passou=True,
            score=0.75,
            keywords_encontradas=["plantao:plantão", "hospital:hospital"],
            motivo_rejeicao=None
        )

        await atualizar_resultado_heuristica(mensagem_id, resultado)

        mock_supabase_classificador.update.assert_called_once()
        call_args = mock_supabase_classificador.update.call_args[0][0]

        assert call_args["status"] == "heuristica_passou"
        assert call_args["passou_heuristica"] is True
        assert call_args["score_heuristica"] == 0.75

    @pytest.mark.asyncio
    async def test_atualiza_rejeitou(self, mock_supabase_classificador):
        """Deve atualizar status para heuristica_rejeitou."""
        mensagem_id = uuid4()
        resultado = ResultadoHeuristica(
            passou=False,
            score=0.0,
            keywords_encontradas=[],
            motivo_rejeicao="keyword_negativa"
        )

        await atualizar_resultado_heuristica(mensagem_id, resultado)

        call_args = mock_supabase_classificador.update.call_args[0][0]

        assert call_args["status"] == "heuristica_rejeitou"
        assert call_args["passou_heuristica"] is False
        assert call_args["motivo_descarte"] == "keyword_negativa"


class TestClassificarBatchHeuristica:
    """Testes para classificar_batch_heuristica."""

    @pytest.mark.asyncio
    async def test_processa_batch(self, mock_supabase_classificador):
        """Deve processar batch de mensagens."""
        mock_supabase_classificador.execute.return_value.data = [
            {"id": str(uuid4()), "texto": "Plantão Hospital ABC R$ 1500"},
            {"id": str(uuid4()), "texto": "Bom dia pessoal"},
            {"id": str(uuid4()), "texto": "Vaga urgente UTI noturno"},
        ]

        stats = await classificar_batch_heuristica(limite=10)

        assert stats["total"] == 3
        assert stats["passou"] == 2  # Duas ofertas
        assert stats["rejeitou"] == 1  # Um cumprimento
        assert stats["erros"] == 0

    @pytest.mark.asyncio
    async def test_batch_vazio(self, mock_supabase_classificador):
        """Deve retornar stats zeradas para batch vazio."""
        mock_supabase_classificador.execute.return_value.data = []

        stats = await classificar_batch_heuristica()

        assert stats["total"] == 0
        assert stats["passou"] == 0
        assert stats["rejeitou"] == 0

    @pytest.mark.asyncio
    async def test_trata_erros(self, mock_supabase_classificador):
        """Deve tratar erros em mensagens individuais."""
        mock_supabase_classificador.execute.return_value.data = [
            {"id": "invalid-uuid", "texto": "Teste"},  # UUID inválido
        ]

        stats = await classificar_batch_heuristica()

        assert stats["erros"] == 1


class TestClassificarMensagemIndividual:
    """Testes para classificar_mensagem_individual."""

    @pytest.mark.asyncio
    async def test_classifica_oferta(self, mock_supabase_classificador):
        """Deve classificar oferta como passou."""
        mensagem_id = uuid4()
        texto = "Plantão Hospital XYZ R$ 2000"

        resultado = await classificar_mensagem_individual(mensagem_id, texto)

        assert resultado.passou is True
        assert resultado.score > 0

    @pytest.mark.asyncio
    async def test_classifica_nao_oferta(self, mock_supabase_classificador):
        """Deve classificar não-oferta como rejeitou."""
        mensagem_id = uuid4()
        texto = "Bom dia a todos"

        resultado = await classificar_mensagem_individual(mensagem_id, texto)

        assert resultado.passou is False
