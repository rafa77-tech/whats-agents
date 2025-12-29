"""
Testes para funcao marcar_vaga_realizada.

Sprint 17 - E01.3
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.services.vagas.service import marcar_vaga_realizada, STATUS_VALIDOS_PARA_REALIZADA


class TestMarcarVagaRealizada:
    """Testes para marcar_vaga_realizada."""

    @pytest.mark.asyncio
    @patch("app.services.vagas.service.supabase")
    async def test_marcar_vaga_realizada_de_reservada(self, mock_supabase):
        """Marca vaga reservada como realizada."""
        # Arrange
        vaga_id = "vaga-uuid-123"
        mock_select = MagicMock()
        mock_select.data = {"id": vaga_id, "status": "reservada"}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_select

        mock_update = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        # Act
        result = await marcar_vaga_realizada(vaga_id, "test_user")

        # Assert
        assert result is True
        mock_supabase.table.return_value.update.assert_called_once()
        update_call = mock_supabase.table.return_value.update.call_args[0][0]
        assert update_call["status"] == "realizada"
        assert update_call["realizada_por"] == "test_user"
        assert "realizada_em" in update_call

    @pytest.mark.asyncio
    @patch("app.services.vagas.service.supabase")
    async def test_marcar_vaga_realizada_de_fechada_legado(self, mock_supabase):
        """Marca vaga fechada (legado) como realizada."""
        # Arrange
        vaga_id = "vaga-uuid-456"
        mock_select = MagicMock()
        mock_select.data = {"id": vaga_id, "status": "fechada"}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_select

        mock_update = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        # Act
        result = await marcar_vaga_realizada(vaga_id, "ops")

        # Assert
        assert result is True
        update_call = mock_supabase.table.return_value.update.call_args[0][0]
        assert update_call["status"] == "realizada"

    @pytest.mark.asyncio
    @patch("app.services.vagas.service.supabase")
    async def test_marcar_vaga_realizada_status_invalido_aberta(self, mock_supabase):
        """Falha ao marcar vaga aberta como realizada."""
        # Arrange
        vaga_id = "vaga-uuid-789"
        mock_select = MagicMock()
        mock_select.data = {"id": vaga_id, "status": "aberta"}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_select

        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await marcar_vaga_realizada(vaga_id)

        assert "deve estar reservada ou fechada" in str(exc.value)
        assert "aberta" in str(exc.value)

    @pytest.mark.asyncio
    @patch("app.services.vagas.service.supabase")
    async def test_marcar_vaga_realizada_status_invalido_cancelada(self, mock_supabase):
        """Falha ao marcar vaga cancelada como realizada."""
        # Arrange
        vaga_id = "vaga-uuid-abc"
        mock_select = MagicMock()
        mock_select.data = {"id": vaga_id, "status": "cancelada"}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_select

        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await marcar_vaga_realizada(vaga_id)

        assert "deve estar reservada ou fechada" in str(exc.value)
        assert "cancelada" in str(exc.value)

    @pytest.mark.asyncio
    @patch("app.services.vagas.service.supabase")
    async def test_marcar_vaga_realizada_vaga_nao_encontrada(self, mock_supabase):
        """Falha ao marcar vaga inexistente."""
        # Arrange
        vaga_id = "vaga-inexistente"
        mock_select = MagicMock()
        mock_select.data = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_select

        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await marcar_vaga_realizada(vaga_id)

        assert "nao encontrada" in str(exc.value)
        assert vaga_id in str(exc.value)

    @pytest.mark.asyncio
    @patch("app.services.vagas.service.supabase")
    async def test_marcar_vaga_realizada_default_ops(self, mock_supabase):
        """Usa 'ops' como default para realizada_por."""
        # Arrange
        vaga_id = "vaga-uuid-default"
        mock_select = MagicMock()
        mock_select.data = {"id": vaga_id, "status": "reservada"}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_select

        mock_update = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        # Act
        result = await marcar_vaga_realizada(vaga_id)

        # Assert
        assert result is True
        update_call = mock_supabase.table.return_value.update.call_args[0][0]
        assert update_call["realizada_por"] == "ops"


class TestStatusValidosParaRealizada:
    """Testes para constante STATUS_VALIDOS_PARA_REALIZADA."""

    def test_status_validos_inclui_reservada(self):
        """Status 'reservada' esta na lista."""
        assert "reservada" in STATUS_VALIDOS_PARA_REALIZADA

    def test_status_validos_inclui_fechada(self):
        """Status 'fechada' (legado) esta na lista."""
        assert "fechada" in STATUS_VALIDOS_PARA_REALIZADA

    def test_status_validos_nao_inclui_aberta(self):
        """Status 'aberta' nao esta na lista."""
        assert "aberta" not in STATUS_VALIDOS_PARA_REALIZADA

    def test_status_validos_nao_inclui_cancelada(self):
        """Status 'cancelada' nao esta na lista."""
        assert "cancelada" not in STATUS_VALIDOS_PARA_REALIZADA
