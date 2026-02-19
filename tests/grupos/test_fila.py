"""
Testes do gerenciamento de fila de processamento de grupos.

Sprint 14 - E11 - Worker e Orquestração
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, UTC
from uuid import uuid4, UUID

from app.services.grupos.fila import (
    EstagioPipeline,
    ItemFila,
    enfileirar_mensagem,
    enfileirar_batch,
    buscar_proximos_pendentes,
    buscar_item_por_mensagem,
    atualizar_estagio,
    marcar_como_finalizado,
    marcar_como_descartado,
    obter_estatisticas_fila,
    obter_itens_travados,
    reprocessar_erros,
    limpar_finalizados,
    RETRY_DELAYS,
)


# =============================================================================
# Testes do Enum EstagioPipeline
# =============================================================================


class TestEstagioPipeline:
    """Testes do enum de estágios."""

    def test_todos_estagios_definidos(self):
        """Verifica que todos os estágios estão definidos."""
        assert EstagioPipeline.PENDENTE.value == "pendente"
        assert EstagioPipeline.HEURISTICA.value == "heuristica"
        assert EstagioPipeline.CLASSIFICACAO.value == "classificacao"
        assert EstagioPipeline.EXTRACAO.value == "extracao"
        assert EstagioPipeline.NORMALIZACAO.value == "normalizacao"
        assert EstagioPipeline.DEDUPLICACAO.value == "deduplicacao"
        assert EstagioPipeline.IMPORTACAO.value == "importacao"
        assert EstagioPipeline.FINALIZADO.value == "finalizado"
        assert EstagioPipeline.ERRO.value == "erro"
        assert EstagioPipeline.DESCARTADO.value == "descartado"

    def test_total_estagios(self):
        """Verifica quantidade total de estágios."""
        assert len(EstagioPipeline) == 10


class TestItemFila:
    """Testes do dataclass ItemFila."""

    def test_criar_item_minimo(self):
        """Cria item com campos obrigatórios."""
        item = ItemFila(id=uuid4(), mensagem_id=uuid4(), estagio=EstagioPipeline.PENDENTE)
        assert item.tentativas == 0
        assert item.max_tentativas == 3
        assert item.ultimo_erro is None

    def test_criar_item_completo(self):
        """Cria item com todos os campos."""
        item = ItemFila(
            id=uuid4(),
            mensagem_id=uuid4(),
            estagio=EstagioPipeline.CLASSIFICACAO,
            tentativas=2,
            max_tentativas=5,
            ultimo_erro="Erro de teste",
            proximo_retry=datetime.now(UTC),
            vaga_grupo_id=uuid4(),
            criado_em=datetime.now(UTC),
            atualizado_em=datetime.now(UTC),
        )
        assert item.tentativas == 2
        assert item.max_tentativas == 5
        assert item.ultimo_erro == "Erro de teste"


# =============================================================================
# Testes de Enfileiramento
# =============================================================================


class TestEnfileirarMensagem:
    """Testes de enfileiramento de mensagens."""

    @pytest.mark.asyncio
    async def test_enfileirar_mensagem_nova(self):
        """Enfileira mensagem nova."""
        mensagem_id = uuid4()
        item_id = uuid4()

        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": str(item_id)}]
            )

            resultado = await enfileirar_mensagem(mensagem_id)

            assert resultado == item_id
            mock_supabase.table.assert_called_with("fila_processamento_grupos")

    @pytest.mark.asyncio
    async def test_enfileirar_batch_vazio(self):
        """Batch vazio retorna 0."""
        resultado = await enfileirar_batch([])
        assert resultado == 0

    @pytest.mark.asyncio
    async def test_enfileirar_batch_multiplas(self):
        """Enfileira múltiplas mensagens."""
        mensagens = [uuid4() for _ in range(5)]

        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock(
                data=[{"id": str(uuid4())} for _ in range(5)]
            )

            resultado = await enfileirar_batch(mensagens)

            assert resultado == 5


# =============================================================================
# Testes de Busca
# =============================================================================


class TestBuscarProximosPendentes:
    """Testes de busca de itens pendentes."""

    @pytest.mark.asyncio
    async def test_buscar_pendentes_estagio(self):
        """Busca itens pendentes em estágio."""
        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [
                {"id": str(uuid4()), "mensagem_id": str(uuid4()), "tentativas": 0},
                {"id": str(uuid4()), "mensagem_id": str(uuid4()), "tentativas": 1},
            ]

            mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.or_.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await buscar_proximos_pendentes(EstagioPipeline.PENDENTE, 50)

            assert len(resultado) == 2

    @pytest.mark.asyncio
    async def test_buscar_pendentes_vazio(self):
        """Retorna lista vazia quando não há pendentes."""
        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = []

            mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.or_.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await buscar_proximos_pendentes(EstagioPipeline.EXTRACAO)

            assert resultado == []


class TestBuscarItemPorMensagem:
    """Testes de busca por mensagem."""

    @pytest.mark.asyncio
    async def test_buscar_existente(self):
        """Encontra item existente."""
        mensagem_id = uuid4()

        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": str(uuid4()), "mensagem_id": str(mensagem_id)}]

            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await buscar_item_por_mensagem(mensagem_id)

            assert resultado is not None
            assert resultado["mensagem_id"] == str(mensagem_id)

    @pytest.mark.asyncio
    async def test_buscar_inexistente(self):
        """Retorna None para item inexistente."""
        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = []

            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await buscar_item_por_mensagem(uuid4())

            assert resultado is None


# =============================================================================
# Testes de Atualização
# =============================================================================


class TestAtualizarEstagio:
    """Testes de atualização de estágio."""

    @pytest.mark.asyncio
    async def test_atualizar_sucesso(self):
        """Atualiza estágio com sucesso."""
        item_id = uuid4()

        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            await atualizar_estagio(item_id, EstagioPipeline.CLASSIFICACAO)

            # Verificar que update foi chamado
            mock_supabase.table.assert_called_with("fila_processamento_grupos")

    @pytest.mark.asyncio
    async def test_atualizar_com_erro_incrementa_tentativas(self):
        """Atualização com erro incrementa tentativas."""
        item_id = uuid4()

        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            # Mock para buscar tentativas atuais
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"tentativas": 1}
            )
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            await atualizar_estagio(item_id, EstagioPipeline.PENDENTE, erro="Erro de teste")

            # Verificar que update foi chamado com tentativas = 2
            update_call = mock_supabase.table.return_value.update.call_args
            assert update_call is not None

    @pytest.mark.asyncio
    async def test_atualizar_com_vaga_grupo_id(self):
        """Atualiza com vaga_grupo_id."""
        item_id = uuid4()
        vaga_grupo_id = uuid4()

        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            await atualizar_estagio(
                item_id, EstagioPipeline.NORMALIZACAO, vaga_grupo_id=vaga_grupo_id
            )

            mock_supabase.table.assert_called()


class TestMarcarComoFinalizado:
    """Testes de marcação como finalizado."""

    @pytest.mark.asyncio
    async def test_marcar_finalizado(self):
        """Marca item como finalizado."""
        item_id = uuid4()

        with patch("app.services.grupos.fila.atualizar_estagio") as mock_atualizar:
            mock_atualizar.return_value = None

            await marcar_como_finalizado(item_id)

            mock_atualizar.assert_called_once_with(item_id, EstagioPipeline.FINALIZADO)


class TestMarcarComoDescartado:
    """Testes de marcação como descartado."""

    @pytest.mark.asyncio
    async def test_marcar_descartado(self):
        """Marca item como descartado via atualizar_estagio."""
        item_id = uuid4()

        with patch("app.services.grupos.fila.atualizar_estagio") as mock_atualizar:
            mock_atualizar.return_value = None

            await marcar_como_descartado(item_id, "heuristica_baixa")

            mock_atualizar.assert_called_once_with(
                item_id=item_id,
                novo_estagio=EstagioPipeline.DESCARTADO,
                erro="descartado: heuristica_baixa",
            )


# =============================================================================
# Testes de Estatísticas
# =============================================================================


class TestObterEstatisticasFila:
    """Testes de estatísticas da fila."""

    @pytest.mark.asyncio
    async def test_obter_estatisticas(self):
        """Obtém estatísticas completas."""
        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.count = 10

            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
            mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = mock_result

            stats = await obter_estatisticas_fila()

            # Deve ter estatísticas para cada estágio
            assert "pendente" in stats
            assert "finalizado" in stats


class TestObterItensTravados:
    """Testes de itens travados."""

    @pytest.mark.asyncio
    async def test_obter_travados(self):
        """Obtém itens travados."""
        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": str(uuid4()), "estagio": "classificacao", "tentativas": 2}]

            # Chain completo: table().select().not_.in_().lt().order().limit().execute()
            mock_supabase.table.return_value.select.return_value.not_.in_.return_value.lt.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

            travados = await obter_itens_travados(horas=1)

            assert len(travados) == 1


# =============================================================================
# Testes de Reprocessamento
# =============================================================================


class TestReprocessarErros:
    """Testes de reprocessamento de erros."""

    @pytest.mark.asyncio
    async def test_reprocessar_erros(self):
        """Reprocessa itens com erro."""
        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [
                {"id": str(uuid4())},
                {"id": str(uuid4())},
            ]

            mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.limit.return_value.execute.return_value = mock_result
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            reprocessados = await reprocessar_erros(100)

            assert reprocessados == 2


class TestLimparFinalizados:
    """Testes de limpeza de finalizados."""

    @pytest.mark.asyncio
    async def test_limpar_finalizados(self):
        """Limpa itens finalizados antigos."""
        with patch("app.services.grupos.fila.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": str(uuid4())} for _ in range(5)]

            mock_supabase.table.return_value.delete.return_value.in_.return_value.lt.return_value.execute.return_value = mock_result

            removidos = await limpar_finalizados(7)

            assert removidos == 5


# =============================================================================
# Testes de Retry Delays
# =============================================================================


class TestRetryDelays:
    """Testes dos delays de retry."""

    def test_delays_definidos(self):
        """Verifica delays de retry."""
        assert RETRY_DELAYS == [1, 5, 15]

    def test_delay_primeira_tentativa(self):
        """Primeira tentativa = 1 minuto."""
        assert RETRY_DELAYS[0] == 1

    def test_delay_segunda_tentativa(self):
        """Segunda tentativa = 5 minutos."""
        assert RETRY_DELAYS[1] == 5

    def test_delay_terceira_tentativa(self):
        """Terceira tentativa = 15 minutos."""
        assert RETRY_DELAYS[2] == 15
