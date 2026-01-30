"""
Testes para o serviço de status de entrega de mensagens.

Sprint 41 - Rastreamento de Chips e Status de Entrega.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.delivery_status import (
    atualizar_delivery_status,
    atualizar_status_lote,
    _normalizar_status,
    DeliveryStatusResult,
)


class TestNormalizarStatus:
    """Testes para normalização de status."""

    def test_evolution_delivery_ack(self):
        """DELIVERY_ACK da Evolution vira delivered."""
        assert _normalizar_status("DELIVERY_ACK") == "delivered"

    def test_evolution_server_ack(self):
        """SERVER_ACK da Evolution vira delivered."""
        assert _normalizar_status("SERVER_ACK") == "delivered"

    def test_evolution_read(self):
        """READ da Evolution vira read."""
        assert _normalizar_status("READ") == "read"

    def test_zapi_delivered(self):
        """DELIVERED da Z-API vira delivered."""
        assert _normalizar_status("DELIVERED") == "delivered"

    def test_zapi_viewed(self):
        """VIEWED da Z-API vira read."""
        assert _normalizar_status("VIEWED") == "read"

    def test_zapi_played(self):
        """PLAYED da Z-API vira read (audio reproduzido)."""
        assert _normalizar_status("PLAYED") == "read"

    def test_failed_status(self):
        """FAILED vira failed."""
        assert _normalizar_status("FAILED") == "failed"

    def test_error_status(self):
        """ERROR vira failed."""
        assert _normalizar_status("ERROR") == "failed"

    def test_lowercase_passthrough(self):
        """Status já normalizados passam direto."""
        assert _normalizar_status("pending") == "pending"
        assert _normalizar_status("sent") == "sent"
        assert _normalizar_status("delivered") == "delivered"
        assert _normalizar_status("read") == "read"
        assert _normalizar_status("failed") == "failed"

    def test_unknown_status(self):
        """Status desconhecido retorna None."""
        assert _normalizar_status("UNKNOWN") is None
        assert _normalizar_status("SENDING") is None
        assert _normalizar_status("QUEUED") is None

    def test_case_insensitive(self):
        """Normalização é case insensitive."""
        assert _normalizar_status("delivery_ack") == "delivered"
        assert _normalizar_status("Read") == "read"
        assert _normalizar_status("read") == "read"


class TestAtualizarDeliveryStatus:
    """Testes para atualização de status de entrega."""

    @pytest.mark.asyncio
    async def test_provider_message_id_obrigatorio(self):
        """Retorna erro se provider_message_id não for informado."""
        result = await atualizar_delivery_status("", "delivered")

        assert result.atualizado is False
        assert result.erro == "provider_message_id é obrigatório"

    @pytest.mark.asyncio
    async def test_status_nao_reconhecido(self):
        """Retorna erro se status não for reconhecido."""
        result = await atualizar_delivery_status("msg123", "UNKNOWN_STATUS")

        assert result.atualizado is False
        assert "Status não reconhecido" in result.erro

    @pytest.mark.asyncio
    @patch("app.services.delivery_status.supabase")
    async def test_atualizacao_bem_sucedida(self, mock_supabase):
        """Atualização bem sucedida retorna dados corretos."""
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value = MagicMock(
            data=[{
                "atualizado": True,
                "interacao_id": "int123",
                "status_anterior": "sent",
                "status_novo": "delivered",
            }]
        )
        mock_supabase.rpc.return_value = mock_rpc

        result = await atualizar_delivery_status("msg123", "DELIVERY_ACK")

        assert result.atualizado is True
        assert result.interacao_id == "int123"
        assert result.status_anterior == "sent"
        assert result.status_novo == "delivered"
        assert result.erro is None

    @pytest.mark.asyncio
    @patch("app.services.delivery_status.supabase")
    async def test_interacao_nao_encontrada(self, mock_supabase):
        """Retorna atualizado=False se interação não for encontrada."""
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value = MagicMock(
            data=[{
                "atualizado": False,
                "interacao_id": None,
                "status_anterior": None,
                "status_novo": None,
            }]
        )
        mock_supabase.rpc.return_value = mock_rpc

        result = await atualizar_delivery_status("msg_inexistente", "delivered")

        assert result.atualizado is False
        assert result.interacao_id is None

    @pytest.mark.asyncio
    @patch("app.services.delivery_status.supabase")
    async def test_status_mantido(self, mock_supabase):
        """Status mantido quando já está em estado mais avançado."""
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value = MagicMock(
            data=[{
                "atualizado": False,
                "interacao_id": "int123",
                "status_anterior": "read",
                "status_novo": None,
            }]
        )
        mock_supabase.rpc.return_value = mock_rpc

        result = await atualizar_delivery_status("msg123", "delivered")

        assert result.atualizado is False
        assert result.interacao_id == "int123"
        assert result.status_anterior == "read"

    @pytest.mark.asyncio
    @patch("app.services.delivery_status.supabase")
    async def test_rpc_retorna_vazio(self, mock_supabase):
        """Retorna erro se RPC retornar vazio."""
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value = MagicMock(data=None)
        mock_supabase.rpc.return_value = mock_rpc

        result = await atualizar_delivery_status("msg123", "delivered")

        assert result.atualizado is False
        assert result.erro == "RPC retornou vazio"

    @pytest.mark.asyncio
    @patch("app.services.delivery_status.supabase")
    async def test_erro_no_rpc(self, mock_supabase):
        """Retorna erro se RPC lançar exceção."""
        mock_supabase.rpc.side_effect = Exception("Database error")

        result = await atualizar_delivery_status("msg123", "delivered")

        assert result.atualizado is False
        assert "Database error" in result.erro

    @pytest.mark.asyncio
    @patch("app.services.delivery_status.supabase")
    async def test_chip_id_passado_para_rpc(self, mock_supabase):
        """chip_id é passado corretamente para a RPC."""
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value = MagicMock(
            data=[{"atualizado": True, "interacao_id": "int123"}]
        )
        mock_supabase.rpc.return_value = mock_rpc

        await atualizar_delivery_status("msg123", "delivered", chip_id="chip456")

        mock_supabase.rpc.assert_called_once_with(
            "interacao_atualizar_delivery_status",
            {
                "p_provider_message_id": "msg123",
                "p_status": "delivered",
                "p_chip_id": "chip456",
            }
        )


class TestAtualizarStatusLote:
    """Testes para atualização de status em lote."""

    @pytest.mark.asyncio
    @patch("app.services.delivery_status.atualizar_delivery_status")
    async def test_lote_vazio(self, mock_atualizar):
        """Lote vazio retorna zeros."""
        result = await atualizar_status_lote([])

        assert result["total"] == 0
        assert result["atualizados"] == 0
        assert result["erros"] == 0
        mock_atualizar.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.delivery_status.atualizar_delivery_status")
    async def test_lote_com_sucesso(self, mock_atualizar):
        """Lote com atualizações bem sucedidas."""
        mock_atualizar.return_value = DeliveryStatusResult(atualizado=True)

        updates = [
            ("msg1", "delivered", None),
            ("msg2", "read", "chip1"),
            ("msg3", "delivered", "chip2"),
        ]

        result = await atualizar_status_lote(updates)

        assert result["total"] == 3
        assert result["atualizados"] == 3
        assert result["erros"] == 0

    @pytest.mark.asyncio
    @patch("app.services.delivery_status.atualizar_delivery_status")
    async def test_lote_com_erros(self, mock_atualizar):
        """Lote com alguns erros."""
        mock_atualizar.side_effect = [
            DeliveryStatusResult(atualizado=True),
            DeliveryStatusResult(atualizado=False, erro="Falha"),
            DeliveryStatusResult(atualizado=True),
        ]

        updates = [
            ("msg1", "delivered", None),
            ("msg2", "read", None),
            ("msg3", "delivered", None),
        ]

        result = await atualizar_status_lote(updates)

        assert result["total"] == 3
        assert result["atualizados"] == 2
        assert result["erros"] == 1

    @pytest.mark.asyncio
    @patch("app.services.delivery_status.atualizar_delivery_status")
    async def test_lote_nao_atualizados_sem_erro(self, mock_atualizar):
        """Não atualizados sem erro não contam como erro."""
        mock_atualizar.return_value = DeliveryStatusResult(
            atualizado=False,
            interacao_id="int123",  # Encontrado mas não atualizado
            erro=None,
        )

        updates = [("msg1", "delivered", None)]

        result = await atualizar_status_lote(updates)

        assert result["total"] == 1
        assert result["atualizados"] == 0
        assert result["erros"] == 0  # Não é erro, apenas não precisou atualizar
