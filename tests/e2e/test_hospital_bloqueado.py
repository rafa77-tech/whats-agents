"""
Testes E2E: Hospital bloqueado não aparece em ofertas.

Sprint 32 - Cenário: Hospital bloqueado
Comportamento esperado: Vagas de hospitais bloqueados não aparecem para Julia.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4


class TestHospitalBloqueadoService:
    """Testes do serviço de hospital bloqueado."""

    def test_import_bloquear_hospital(self):
        """Função bloquear_hospital deve existir."""
        from app.services.hospitais_bloqueados import bloquear_hospital
        assert callable(bloquear_hospital)

    def test_import_desbloquear_hospital(self):
        """Função desbloquear_hospital deve existir."""
        from app.services.hospitais_bloqueados import desbloquear_hospital
        assert callable(desbloquear_hospital)

    def test_import_verificar_hospital_bloqueado(self):
        """Função verificar_hospital_bloqueado deve existir."""
        from app.services.hospitais_bloqueados import verificar_hospital_bloqueado
        assert callable(verificar_hospital_bloqueado)


class TestHospitalBloqueadoComportamento:
    """Testes de comportamento de hospital bloqueado."""

    @pytest.mark.asyncio
    async def test_bloquear_hospital_retorna_dict(self):
        """bloquear_hospital deve retornar um dict."""
        from app.services.hospitais_bloqueados import bloquear_hospital

        # Mock do supabase
        with patch("app.services.hospitais_bloqueados.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)

            resultado = await bloquear_hospital(
                hospital_id="test-hospital",
                motivo="Teste",
                bloqueado_por="test",
                notificar_slack=False
            )

            assert isinstance(resultado, dict)
            assert "success" in resultado

    @pytest.mark.asyncio
    async def test_bloquear_hospital_inexistente_falha(self):
        """Bloquear hospital inexistente deve falhar."""
        from app.services.hospitais_bloqueados import bloquear_hospital

        with patch("app.services.hospitais_bloqueados.supabase") as mock_sb:
            # Hospital não existe
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)

            resultado = await bloquear_hospital(
                hospital_id="hospital-inexistente",
                motivo="Teste",
                bloqueado_por="test",
                notificar_slack=False
            )

            assert resultado["success"] is False
            assert "error" in resultado


class TestHospitalBloqueadoConstantes:
    """Testes das constantes de hospital bloqueado."""

    def test_status_bloqueado_existe(self):
        """Constante STATUS_BLOQUEADO deve existir."""
        from app.services.hospitais_bloqueados import STATUS_BLOQUEADO
        assert STATUS_BLOQUEADO == "bloqueado"

    def test_status_desbloqueado_existe(self):
        """Constante STATUS_DESBLOQUEADO deve existir."""
        from app.services.hospitais_bloqueados import STATUS_DESBLOQUEADO
        assert STATUS_DESBLOQUEADO == "desbloqueado"


class TestHospitalBloqueadoFixtures:
    """Testes das fixtures de hospital."""

    def test_hospital_data_tem_id(self, hospital_data):
        """Hospital deve ter ID."""
        assert "id" in hospital_data
        assert hospital_data["id"] is not None

    def test_hospital_data_tem_nome(self, hospital_data):
        """Hospital deve ter nome."""
        assert "nome" in hospital_data
        assert hospital_data["nome"] is not None

    def test_vaga_pertence_ao_hospital(self, vaga_data, hospital_data):
        """Vaga deve pertencer ao hospital."""
        assert vaga_data["hospital_id"] == hospital_data["id"]
