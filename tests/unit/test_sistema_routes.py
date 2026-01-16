"""
Testes para endpoints /sistema.

Sprint 32 - E20: Toggle Modo Piloto via Dashboard
"""
import pytest
from unittest.mock import patch, MagicMock

from app.api.routes.sistema import (
    get_sistema_status,
    set_pilot_mode,
    PilotModeRequest,
)


class TestGetSistemaStatus:
    """Testes para GET /sistema/status."""

    @pytest.mark.asyncio
    async def test_retorna_status_piloto_ativado(self):
        """Deve retornar pilot_mode=True quando settings.PILOT_MODE=True."""
        with patch("app.api.routes.sistema.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            mock_settings.autonomous_features_status = {
                "discovery_automatico": False,
                "oferta_automatica": False,
                "reativacao_automatica": False,
                "feedback_automatico": False,
            }

            with patch("app.api.routes.sistema.supabase") as mock_supabase:
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data=None
                )

                response = await get_sistema_status()

                assert response.pilot_mode is True
                assert response.autonomous_features["discovery_automatico"] is False
                assert response.autonomous_features["oferta_automatica"] is False

    @pytest.mark.asyncio
    async def test_retorna_status_piloto_desativado(self):
        """Deve retornar pilot_mode=False quando settings.PILOT_MODE=False."""
        with patch("app.api.routes.sistema.settings") as mock_settings:
            mock_settings.is_pilot_mode = False
            mock_settings.autonomous_features_status = {
                "discovery_automatico": True,
                "oferta_automatica": True,
                "reativacao_automatica": True,
                "feedback_automatico": True,
            }

            with patch("app.api.routes.sistema.supabase") as mock_supabase:
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data=None
                )

                response = await get_sistema_status()

                assert response.pilot_mode is False
                assert response.autonomous_features["discovery_automatico"] is True
                assert response.autonomous_features["oferta_automatica"] is True

    @pytest.mark.asyncio
    async def test_retorna_ultima_alteracao(self):
        """Deve retornar dados de ultima alteracao quando disponiveis."""
        with patch("app.api.routes.sistema.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            mock_settings.autonomous_features_status = {
                "discovery_automatico": False,
                "oferta_automatica": False,
                "reativacao_automatica": False,
                "feedback_automatico": False,
            }

            with patch("app.api.routes.sistema.supabase") as mock_supabase:
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data={
                        "updated_at": "2026-01-16T10:00:00Z",
                        "updated_by": "admin@revoluna.com",
                    }
                )

                response = await get_sistema_status()

                assert response.last_changed_at == "2026-01-16T10:00:00Z"
                assert response.last_changed_by == "admin@revoluna.com"


class TestSetPilotMode:
    """Testes para POST /sistema/pilot-mode."""

    @pytest.mark.asyncio
    async def test_ativa_modo_piloto(self):
        """Deve ativar modo piloto com sucesso."""
        with patch("app.api.routes.sistema.settings") as mock_settings:
            mock_settings.autonomous_features_status = {
                "discovery_automatico": False,
                "oferta_automatica": False,
                "reativacao_automatica": False,
                "feedback_automatico": False,
            }

            with patch("app.api.routes.sistema.supabase") as mock_supabase:
                mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()

                request = PilotModeRequest(
                    pilot_mode=True,
                    changed_by="admin@revoluna.com",
                )

                response = await set_pilot_mode(request)

                assert response.success is True
                assert response.pilot_mode is True
                assert mock_settings.PILOT_MODE is True

    @pytest.mark.asyncio
    async def test_desativa_modo_piloto(self):
        """Deve desativar modo piloto com sucesso."""
        with patch("app.api.routes.sistema.settings") as mock_settings:
            mock_settings.autonomous_features_status = {
                "discovery_automatico": True,
                "oferta_automatica": True,
                "reativacao_automatica": True,
                "feedback_automatico": True,
            }

            with patch("app.api.routes.sistema.supabase") as mock_supabase:
                mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()

                request = PilotModeRequest(
                    pilot_mode=False,
                    changed_by="admin@revoluna.com",
                )

                response = await set_pilot_mode(request)

                assert response.success is True
                assert response.pilot_mode is False
                assert mock_settings.PILOT_MODE is False

    @pytest.mark.asyncio
    async def test_salva_no_banco(self):
        """Deve salvar configuracao no banco de dados."""
        with patch("app.api.routes.sistema.settings") as mock_settings:
            mock_settings.autonomous_features_status = {}

            with patch("app.api.routes.sistema.supabase") as mock_supabase:
                mock_upsert = MagicMock()
                mock_supabase.table.return_value.upsert.return_value = mock_upsert
                mock_upsert.execute.return_value = MagicMock()

                request = PilotModeRequest(
                    pilot_mode=True,
                    changed_by="admin@revoluna.com",
                )

                await set_pilot_mode(request)

                # Verificar que upsert foi chamado
                mock_supabase.table.assert_called_with("system_config")
                upsert_call = mock_supabase.table.return_value.upsert.call_args
                assert upsert_call is not None
                data = upsert_call[0][0]
                assert data["key"] == "PILOT_MODE"
                assert data["value"] == "true"
                assert data["updated_by"] == "admin@revoluna.com"

    @pytest.mark.asyncio
    async def test_erro_no_banco_retorna_500(self):
        """Deve retornar erro 500 quando banco falha."""
        from fastapi import HTTPException

        with patch("app.api.routes.sistema.settings"):
            with patch("app.api.routes.sistema.supabase") as mock_supabase:
                mock_supabase.table.return_value.upsert.return_value.execute.side_effect = Exception(
                    "Database error"
                )

                request = PilotModeRequest(pilot_mode=True)

                with pytest.raises(HTTPException) as exc_info:
                    await set_pilot_mode(request)

                assert exc_info.value.status_code == 500


class TestPilotModeRequest:
    """Testes para modelo PilotModeRequest."""

    def test_pilot_mode_obrigatorio(self):
        """pilot_mode deve ser obrigatorio."""
        request = PilotModeRequest(pilot_mode=True)
        assert request.pilot_mode is True

    def test_changed_by_opcional(self):
        """changed_by deve ser opcional."""
        request = PilotModeRequest(pilot_mode=False)
        assert request.changed_by is None

    def test_changed_by_pode_ser_preenchido(self):
        """changed_by deve aceitar valor."""
        request = PilotModeRequest(
            pilot_mode=True,
            changed_by="admin@revoluna.com",
        )
        assert request.changed_by == "admin@revoluna.com"
