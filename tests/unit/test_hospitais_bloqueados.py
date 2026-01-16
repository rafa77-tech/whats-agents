"""
Testes para serviço de Hospitais Bloqueados.

Sprint 32 E12 - Bloquear/desbloquear hospitais.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestBloquearHospital:
    """Testes para bloquear_hospital()."""

    @pytest.mark.asyncio
    async def test_bloqueia_hospital_com_sucesso(self):
        """Deve bloquear hospital e mover vagas."""
        from app.services.hospitais_bloqueados import bloquear_hospital

        with patch("app.services.hospitais_bloqueados.supabase") as mock_supabase:
            # Mock busca hospital
            mock_hospital = MagicMock()
            mock_hospital.data = [{"id": "hosp-123", "nome": "Hospital São Luiz"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_hospital

            # Mock verifica bloqueio existente
            mock_bloqueio = MagicMock()
            mock_bloqueio.data = []
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_bloqueio

            # Mock insert bloqueio
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

            # Mock busca vagas
            mock_vagas = MagicMock()
            mock_vagas.data = [{"id": "v1"}, {"id": "v2"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value = mock_vagas

            # Mock update/insert vagas
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            with patch("app.services.hospitais_bloqueados.enviar_slack") as mock_slack:
                mock_slack.return_value = True

                resultado = await bloquear_hospital(
                    hospital_id="hosp-123",
                    motivo="Problema temporário",
                    bloqueado_por="gestor-rafael",
                )

                assert resultado["success"] is True
                assert "bloqueio_id" in resultado

    @pytest.mark.asyncio
    async def test_rejeita_se_ja_bloqueado(self):
        """Deve rejeitar se hospital já está bloqueado."""
        from app.services.hospitais_bloqueados import bloquear_hospital

        with patch("app.services.hospitais_bloqueados._buscar_hospital") as mock_buscar:
            mock_buscar.return_value = {"id": "hosp-123", "nome": "Hospital"}

            with patch("app.services.hospitais_bloqueados.verificar_hospital_bloqueado") as mock_verificar:
                mock_verificar.return_value = {"id": "bloqueio-existente"}

                resultado = await bloquear_hospital(
                    hospital_id="hosp-123",
                    motivo="Teste",
                    bloqueado_por="gestor",
                )

                assert resultado["success"] is False
                assert "já está bloqueado" in resultado["error"]

    @pytest.mark.asyncio
    async def test_rejeita_hospital_inexistente(self):
        """Deve rejeitar se hospital não existe."""
        from app.services.hospitais_bloqueados import bloquear_hospital

        with patch("app.services.hospitais_bloqueados._buscar_hospital") as mock_buscar:
            mock_buscar.return_value = None

            resultado = await bloquear_hospital(
                hospital_id="hosp-inexistente",
                motivo="Teste",
                bloqueado_por="gestor",
            )

            assert resultado["success"] is False
            assert "não encontrado" in resultado["error"]


class TestDesbloquearHospital:
    """Testes para desbloquear_hospital()."""

    @pytest.mark.asyncio
    async def test_desbloqueia_hospital_com_sucesso(self):
        """Deve desbloquear hospital e restaurar vagas."""
        from app.services.hospitais_bloqueados import desbloquear_hospital

        with patch("app.services.hospitais_bloqueados.verificar_hospital_bloqueado") as mock_verificar:
            mock_verificar.return_value = {"id": "bloqueio-123"}

            with patch("app.services.hospitais_bloqueados.supabase") as mock_supabase:
                # Mock update bloqueio
                mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

                with patch("app.services.hospitais_bloqueados._restaurar_vagas_de_bloqueados") as mock_restaurar:
                    mock_restaurar.return_value = 3

                    with patch("app.services.hospitais_bloqueados._buscar_hospital") as mock_buscar:
                        mock_buscar.return_value = {"nome": "Hospital"}

                        with patch("app.services.hospitais_bloqueados.enviar_slack") as mock_slack:
                            mock_slack.return_value = True

                            resultado = await desbloquear_hospital(
                                hospital_id="hosp-123",
                                desbloqueado_por="gestor-rafael",
                            )

                            assert resultado["success"] is True
                            assert resultado["vagas_restauradas"] == 3

    @pytest.mark.asyncio
    async def test_rejeita_se_nao_bloqueado(self):
        """Deve rejeitar se hospital não está bloqueado."""
        from app.services.hospitais_bloqueados import desbloquear_hospital

        with patch("app.services.hospitais_bloqueados.verificar_hospital_bloqueado") as mock_verificar:
            mock_verificar.return_value = None

            resultado = await desbloquear_hospital(
                hospital_id="hosp-nao-bloqueado",
                desbloqueado_por="gestor",
            )

            assert resultado["success"] is False
            assert "não está bloqueado" in resultado["error"]


class TestVerificarHospitalBloqueado:
    """Testes para verificar_hospital_bloqueado()."""

    @pytest.mark.asyncio
    async def test_retorna_bloqueio_existente(self):
        """Deve retornar dados do bloqueio se existe."""
        from app.services.hospitais_bloqueados import verificar_hospital_bloqueado

        with patch("app.services.hospitais_bloqueados.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": "bloqueio-123", "motivo": "Teste"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await verificar_hospital_bloqueado("hosp-123")

            assert resultado is not None
            assert resultado["motivo"] == "Teste"

    @pytest.mark.asyncio
    async def test_retorna_none_se_nao_bloqueado(self):
        """Deve retornar None se não está bloqueado."""
        from app.services.hospitais_bloqueados import verificar_hospital_bloqueado

        with patch("app.services.hospitais_bloqueados.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = []
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await verificar_hospital_bloqueado("hosp-livre")

            assert resultado is None


class TestListarHospitaisBloqueados:
    """Testes para listar_hospitais_bloqueados()."""

    @pytest.mark.asyncio
    async def test_lista_hospitais_bloqueados(self):
        """Deve listar todos os hospitais bloqueados."""
        from app.services.hospitais_bloqueados import listar_hospitais_bloqueados

        with patch("app.services.hospitais_bloqueados.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [
                {"id": "b1", "hospitais": {"nome": "Hospital A"}},
                {"id": "b2", "hospitais": {"nome": "Hospital B"}},
            ]
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

            resultado = await listar_hospitais_bloqueados()

            assert len(resultado) == 2


class TestHospitalEstaBloqueado:
    """Testes para hospital_esta_bloqueado()."""

    @pytest.mark.asyncio
    async def test_retorna_true_se_bloqueado(self):
        """Deve retornar True se hospital está bloqueado."""
        from app.services.hospitais_bloqueados import hospital_esta_bloqueado

        with patch("app.services.hospitais_bloqueados.verificar_hospital_bloqueado") as mock_verificar:
            mock_verificar.return_value = {"id": "bloqueio"}

            resultado = await hospital_esta_bloqueado("hosp-bloqueado")

            assert resultado is True

    @pytest.mark.asyncio
    async def test_retorna_false_se_nao_bloqueado(self):
        """Deve retornar False se hospital não está bloqueado."""
        from app.services.hospitais_bloqueados import hospital_esta_bloqueado

        with patch("app.services.hospitais_bloqueados.verificar_hospital_bloqueado") as mock_verificar:
            mock_verificar.return_value = None

            resultado = await hospital_esta_bloqueado("hosp-livre")

            assert resultado is False
