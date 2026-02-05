"""
Testes do processamento de fila de mensagens.

Sprint 10 - S10.E3.1 - Processamento de fila
Sprint 44 - Integração com multi-chip
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import dataclass

from app.services.jobs.fila_mensagens import (
    processar_fila,
    _processar_mensagem,
    StatsFilaMensagens,
)


@pytest.fixture
def mensagem_campanha():
    """Mensagem de campanha mockada."""
    return {
        "id": "msg-123",
        "cliente_id": "cliente-abc",
        "conversa_id": "conv-xyz",
        "conteudo": "Oi Dr Carlos! Tudo bem?",
        "tipo": "campanha",
        "prioridade": 3,
        "status": "processando",
        "tentativas": 0,
        "metadata": {
            "campanha_id": "42",
            "tipo_campanha": "discovery"
        },
        "clientes": {
            "telefone": "5511999999999",
            "primeiro_nome": "Carlos"
        }
    }


@pytest.fixture
def mensagem_sem_telefone():
    """Mensagem sem telefone."""
    return {
        "id": "msg-sem-tel",
        "cliente_id": "cliente-abc",
        "conteudo": "Teste",
        "tipo": "campanha",
        "metadata": {},
        "clientes": {}
    }


@pytest.fixture
def mensagem_com_chips_excluidos():
    """Mensagem com chips excluídos."""
    return {
        "id": "msg-456",
        "cliente_id": "cliente-def",
        "conversa_id": "conv-123",
        "conteudo": "Mensagem com chips excluídos",
        "tipo": "campanha",
        "metadata": {
            "chips_excluidos": ["chip-1", "chip-2"]
        },
        "clientes": {
            "telefone": "5511888888888",
            "primeiro_nome": "Maria"
        }
    }


class TestStatsFilaMensagens:
    """Testes do dataclass de estatísticas."""

    def test_stats_inicial(self):
        """Estatísticas iniciais são zero."""
        stats = StatsFilaMensagens()
        assert stats.processadas == 0
        assert stats.enviadas == 0
        assert stats.bloqueadas_optout == 0
        assert stats.erros == 0

    def test_stats_com_valores(self):
        """Estatísticas com valores."""
        stats = StatsFilaMensagens(
            processadas=10,
            enviadas=8,
            bloqueadas_optout=1,
            erros=1
        )
        assert stats.processadas == 10
        assert stats.enviadas == 8


class TestProcessarFila:
    """Testes do processamento da fila."""

    @pytest.mark.asyncio
    async def test_processar_fila_vazia(self):
        """Fila vazia retorna stats zeradas."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila:
            mock_fila.obter_proxima = AsyncMock(return_value=None)

            stats = await processar_fila(limite=20)

            assert stats.processadas == 0
            assert stats.enviadas == 0

    @pytest.mark.asyncio
    async def test_processar_fila_com_mensagens(self, mensagem_campanha):
        """Processa múltiplas mensagens."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens._processar_mensagem") as mock_processar:

            # Retorna mensagem nas 2 primeiras chamadas, depois None
            mock_fila.obter_proxima = AsyncMock(side_effect=[
                mensagem_campanha,
                {**mensagem_campanha, "id": "msg-456"},
                None
            ])
            mock_processar.return_value = "enviada"

            stats = await processar_fila(limite=10)

            assert stats.processadas == 2
            assert stats.enviadas == 2

    @pytest.mark.asyncio
    async def test_processar_fila_respeita_limite(self, mensagem_campanha):
        """Respeita o limite de processamento."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens._processar_mensagem") as mock_processar:

            # Sempre retorna mensagem
            mock_fila.obter_proxima = AsyncMock(return_value=mensagem_campanha)
            mock_processar.return_value = "enviada"

            stats = await processar_fila(limite=5)

            assert stats.processadas == 5

    @pytest.mark.asyncio
    async def test_processar_fila_contabiliza_optout(self, mensagem_campanha):
        """Contabiliza mensagens bloqueadas por opt-out."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens._processar_mensagem") as mock_processar:

            mock_fila.obter_proxima = AsyncMock(side_effect=[
                mensagem_campanha,
                None
            ])
            mock_processar.return_value = "optout"

            stats = await processar_fila(limite=10)

            assert stats.processadas == 1
            assert stats.bloqueadas_optout == 1
            assert stats.enviadas == 0

    @pytest.mark.asyncio
    async def test_processar_fila_contabiliza_erros(self, mensagem_campanha):
        """Contabiliza erros de processamento."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens._processar_mensagem") as mock_processar:

            mock_fila.obter_proxima = AsyncMock(side_effect=[
                mensagem_campanha,
                None
            ])
            mock_processar.return_value = "erro"

            stats = await processar_fila(limite=10)

            assert stats.processadas == 1
            assert stats.erros == 1


class TestProcessarMensagem:
    """Testes do processamento de mensagem individual."""

    @pytest.mark.asyncio
    async def test_processar_mensagem_sucesso(self, mensagem_campanha):
        """Processa mensagem com sucesso."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens.send_outbound_message") as mock_send, \
             patch("app.services.jobs.fila_mensagens.criar_contexto_followup") as mock_ctx, \
             patch("app.services.jobs.fila_mensagens.buscar_ou_criar_conversa") as mock_conversa, \
             patch("app.services.jobs.fila_mensagens.salvar_interacao") as mock_interacao:

            # Mock do resultado de envio
            mock_result = MagicMock()
            mock_result.blocked = False
            mock_result.success = True
            mock_result.chip_id = "chip-123"
            mock_send.return_value = mock_result

            mock_ctx.return_value = {}
            mock_fila.marcar_enviada = AsyncMock(return_value=True)
            mock_interacao.return_value = None

            resultado = await _processar_mensagem(mensagem_campanha)

            assert resultado == "enviada"
            mock_fila.marcar_enviada.assert_called_once_with("msg-123")
            mock_interacao.assert_called_once()

    @pytest.mark.asyncio
    async def test_processar_mensagem_sem_telefone(self, mensagem_sem_telefone):
        """Retorna erro quando telefone não está presente."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila:
            mock_fila.marcar_erro = AsyncMock()

            resultado = await _processar_mensagem(mensagem_sem_telefone)

            assert resultado == "erro"
            mock_fila.marcar_erro.assert_called_once()

    @pytest.mark.asyncio
    async def test_processar_mensagem_sem_cliente_id(self, mensagem_campanha):
        """Retorna erro quando cliente_id não está presente."""
        mensagem_campanha["cliente_id"] = None

        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila:
            mock_fila.marcar_erro = AsyncMock()

            resultado = await _processar_mensagem(mensagem_campanha)

            assert resultado == "erro"

    @pytest.mark.asyncio
    async def test_processar_mensagem_bloqueada_optout(self, mensagem_campanha):
        """Retorna optout quando guardrail bloqueia por opt-out."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens.send_outbound_message") as mock_send, \
             patch("app.services.jobs.fila_mensagens.criar_contexto_followup") as mock_ctx, \
             patch("app.services.jobs.fila_mensagens.buscar_ou_criar_conversa") as mock_conversa:

            mock_result = MagicMock()
            mock_result.blocked = True
            mock_result.block_reason = "opted_out"
            mock_send.return_value = mock_result

            mock_ctx.return_value = {}
            mock_fila.marcar_erro = AsyncMock()

            resultado = await _processar_mensagem(mensagem_campanha)

            assert resultado == "optout"

    @pytest.mark.asyncio
    async def test_processar_mensagem_bloqueada_outro_motivo(self, mensagem_campanha):
        """Retorna erro quando guardrail bloqueia por outro motivo."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens.send_outbound_message") as mock_send, \
             patch("app.services.jobs.fila_mensagens.criar_contexto_followup") as mock_ctx, \
             patch("app.services.jobs.fila_mensagens.buscar_ou_criar_conversa") as mock_conversa:

            mock_result = MagicMock()
            mock_result.blocked = True
            mock_result.block_reason = "rate_limit"
            mock_send.return_value = mock_result

            mock_ctx.return_value = {}
            mock_fila.marcar_erro = AsyncMock()

            resultado = await _processar_mensagem(mensagem_campanha)

            assert resultado == "erro"

    @pytest.mark.asyncio
    async def test_processar_mensagem_falha_envio(self, mensagem_campanha):
        """Retorna erro quando envio falha."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens.send_outbound_message") as mock_send, \
             patch("app.services.jobs.fila_mensagens.criar_contexto_followup") as mock_ctx, \
             patch("app.services.jobs.fila_mensagens.buscar_ou_criar_conversa") as mock_conversa:

            mock_result = MagicMock()
            mock_result.blocked = False
            mock_result.success = False
            mock_result.error = "Provider timeout"
            mock_send.return_value = mock_result

            mock_ctx.return_value = {}
            mock_fila.marcar_erro = AsyncMock()

            resultado = await _processar_mensagem(mensagem_campanha)

            assert resultado == "erro"
            mock_fila.marcar_erro.assert_called()

    @pytest.mark.asyncio
    async def test_processar_mensagem_com_chips_excluidos(self, mensagem_com_chips_excluidos):
        """Passa chips_excluidos do metadata para o envio."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens.send_outbound_message") as mock_send, \
             patch("app.services.jobs.fila_mensagens.criar_contexto_followup") as mock_ctx, \
             patch("app.services.jobs.fila_mensagens.buscar_ou_criar_conversa") as mock_conversa, \
             patch("app.services.jobs.fila_mensagens.salvar_interacao") as mock_interacao:

            mock_result = MagicMock()
            mock_result.blocked = False
            mock_result.success = True
            mock_result.chip_id = "chip-3"
            mock_send.return_value = mock_result

            mock_ctx.return_value = {}
            mock_fila.marcar_enviada = AsyncMock(return_value=True)
            mock_interacao.return_value = None

            resultado = await _processar_mensagem(mensagem_com_chips_excluidos)

            assert resultado == "enviada"
            # Verificar que chips_excluidos foi passado
            call_kwargs = mock_send.call_args.kwargs
            assert call_kwargs.get("chips_excluidos") == ["chip-1", "chip-2"]

    @pytest.mark.asyncio
    async def test_processar_mensagem_cria_conversa_se_nao_existir(self, mensagem_campanha):
        """Cria conversa se não existir conversa_id."""
        mensagem_campanha["conversa_id"] = None

        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens.send_outbound_message") as mock_send, \
             patch("app.services.jobs.fila_mensagens.criar_contexto_followup") as mock_ctx, \
             patch("app.services.jobs.fila_mensagens.buscar_ou_criar_conversa") as mock_conversa, \
             patch("app.services.jobs.fila_mensagens.salvar_interacao") as mock_interacao:

            mock_result = MagicMock()
            mock_result.blocked = False
            mock_result.success = True
            mock_result.chip_id = "chip-123"
            mock_send.return_value = mock_result

            mock_conversa.return_value = {"id": "conv-nova"}
            mock_ctx.return_value = {}
            mock_fila.marcar_enviada = AsyncMock(return_value=True)
            mock_interacao.return_value = None

            resultado = await _processar_mensagem(mensagem_campanha)

            assert resultado == "enviada"
            mock_conversa.assert_called_once_with("cliente-abc")

    @pytest.mark.asyncio
    async def test_processar_mensagem_exception(self, mensagem_campanha):
        """Trata exceção durante processamento."""
        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens.send_outbound_message") as mock_send, \
             patch("app.services.jobs.fila_mensagens.criar_contexto_followup") as mock_ctx, \
             patch("app.services.jobs.fila_mensagens.buscar_ou_criar_conversa") as mock_conversa:

            mock_ctx.return_value = {}
            mock_send.side_effect = Exception("Connection error")
            mock_fila.marcar_erro = AsyncMock()

            resultado = await _processar_mensagem(mensagem_campanha)

            assert resultado == "erro"
            mock_fila.marcar_erro.assert_called()


class TestIntegracaoComCampanhas:
    """Testes de integração do fluxo campanha -> fila -> envio."""

    @pytest.mark.asyncio
    async def test_fluxo_campanha_discovery(self, mensagem_campanha):
        """Testa fluxo completo de campanha discovery."""
        mensagem_campanha["metadata"]["tipo_campanha"] = "discovery"

        with patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila, \
             patch("app.services.jobs.fila_mensagens.send_outbound_message") as mock_send, \
             patch("app.services.jobs.fila_mensagens.criar_contexto_followup") as mock_ctx, \
             patch("app.services.jobs.fila_mensagens.buscar_ou_criar_conversa") as mock_conversa, \
             patch("app.services.jobs.fila_mensagens.salvar_interacao") as mock_interacao:

            mock_result = MagicMock()
            mock_result.blocked = False
            mock_result.success = True
            mock_result.chip_id = "chip-julia-1"
            mock_send.return_value = mock_result

            mock_ctx.return_value = {}
            mock_fila.marcar_enviada = AsyncMock(return_value=True)
            mock_interacao.return_value = None

            resultado = await _processar_mensagem(mensagem_campanha)

            assert resultado == "enviada"
            # Verificar que interação foi salva com chip_id
            call_kwargs = mock_interacao.call_args.kwargs
            assert call_kwargs.get("chip_id") == "chip-julia-1"
            assert call_kwargs.get("tipo") == "saida"
            assert call_kwargs.get("autor_tipo") == "julia"
