"""
Testes para serviço de Diretrizes Contextuais.

Sprint 32 E10 - Margens de negociação por vaga/médico.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone


class TestCriarMargemVaga:
    """Testes para criar_margem_vaga()."""

    @pytest.mark.asyncio
    async def test_cria_margem_com_valor_maximo(self):
        """Deve criar margem com valor máximo absoluto."""
        from app.services.diretrizes_contextuais import criar_margem_vaga

        with patch("app.services.diretrizes_contextuais.supabase") as mock_supabase:
            mock_insert = MagicMock()
            mock_insert.data = [{"id": "diretriz-123", "valor_maximo": 3000}]
            mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert

            resultado = await criar_margem_vaga(
                vaga_id="vaga-123",
                valor_maximo=3000,
                criado_por="gestor-rafael",
            )

            assert resultado is not None
            assert resultado.get("valor_maximo") == 3000

    @pytest.mark.asyncio
    async def test_cria_margem_com_percentual(self):
        """Deve criar margem com percentual máximo."""
        from app.services.diretrizes_contextuais import criar_margem_vaga

        with patch("app.services.diretrizes_contextuais.supabase") as mock_supabase:
            mock_insert = MagicMock()
            mock_insert.data = [{"id": "diretriz-456", "percentual_maximo": 15.0}]
            mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert

            resultado = await criar_margem_vaga(
                vaga_id="vaga-456",
                percentual_maximo=15.0,
                criado_por="gestor-rafael",
            )

            assert resultado is not None


class TestCriarMargemMedico:
    """Testes para criar_margem_medico()."""

    @pytest.mark.asyncio
    async def test_cria_margem_para_medico(self):
        """Deve criar margem específica para médico."""
        from app.services.diretrizes_contextuais import criar_margem_medico

        with patch("app.services.diretrizes_contextuais.supabase") as mock_supabase:
            mock_insert = MagicMock()
            mock_insert.data = [{"id": "diretriz-789", "cliente_id": "medico-123"}]
            mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert

            resultado = await criar_margem_medico(
                cliente_id="medico-123",
                percentual_maximo=10.0,
                instrucao="Médico premium, pode flexibilizar",
                criado_por="gestor-rafael",
            )

            assert resultado is not None


class TestBuscarMargemParaNegociacao:
    """Testes para buscar_margem_para_negociacao()."""

    @pytest.mark.asyncio
    async def test_encontra_margem_por_vaga(self):
        """Deve encontrar margem específica da vaga."""
        from app.services.diretrizes_contextuais import buscar_margem_para_negociacao

        with patch("app.services.diretrizes_contextuais._buscar_diretrizes_ativas") as mock_buscar:
            mock_buscar.return_value = [
                {"id": "d1", "escopo": "vaga", "valor_maximo": 3000, "percentual_maximo": None}
            ]

            resultado = await buscar_margem_para_negociacao(
                vaga_id="vaga-123",
            )

            assert resultado["tem_margem"] is True
            assert resultado["valor_maximo"] == 3000
            assert resultado["escopo"] == "vaga"

    @pytest.mark.asyncio
    async def test_prioriza_vaga_sobre_hospital(self):
        """Deve priorizar margem de vaga sobre hospital."""
        from app.services.diretrizes_contextuais import buscar_margem_para_negociacao

        with patch("app.services.diretrizes_contextuais._buscar_diretrizes_ativas") as mock_buscar:
            # Simula retorno com margem de vaga e hospital
            def buscar_side_effect(tipo, escopo, **kwargs):
                if escopo == "vaga":
                    return [{"id": "d1", "escopo": "vaga", "valor_maximo": 3000}]
                elif escopo == "hospital":
                    return [{"id": "d2", "escopo": "hospital", "valor_maximo": 2500}]
                return []

            mock_buscar.side_effect = buscar_side_effect

            resultado = await buscar_margem_para_negociacao(
                vaga_id="vaga-123",
                hospital_id="hosp-123",
            )

            assert resultado["tem_margem"] is True
            assert resultado["valor_maximo"] == 3000  # Vaga tem precedência

    @pytest.mark.asyncio
    async def test_retorna_sem_margem_quando_nao_existe(self):
        """Deve retornar sem margem quando não existe diretriz."""
        from app.services.diretrizes_contextuais import buscar_margem_para_negociacao

        with patch("app.services.diretrizes_contextuais._buscar_diretrizes_ativas") as mock_buscar:
            mock_buscar.return_value = []

            resultado = await buscar_margem_para_negociacao(
                vaga_id="vaga-sem-margem",
            )

            assert resultado["tem_margem"] is False
            assert resultado["valor_maximo"] is None


class TestBuscarInstrucoesEspeciais:
    """Testes para buscar_instrucoes_especiais()."""

    @pytest.mark.asyncio
    async def test_combina_instrucoes_de_multiplos_escopos(self):
        """Deve combinar instruções de diferentes escopos."""
        from app.services.diretrizes_contextuais import buscar_instrucoes_especiais

        with patch("app.services.diretrizes_contextuais._buscar_diretrizes_ativas") as mock_buscar:
            def buscar_side_effect(tipo, escopo, **kwargs):
                if escopo == "vaga":
                    return [{"instrucao": "Instrução da vaga"}]
                elif escopo == "hospital":
                    return [{"instrucao": "Instrução do hospital"}]
                return []

            mock_buscar.side_effect = buscar_side_effect

            resultado = await buscar_instrucoes_especiais(
                vaga_id="vaga-123",
                hospital_id="hosp-123",
            )

            assert len(resultado) == 2
            assert "Instrução da vaga" in resultado
            assert "Instrução do hospital" in resultado

    @pytest.mark.asyncio
    async def test_retorna_lista_vazia_sem_instrucoes(self):
        """Deve retornar lista vazia se não há instruções."""
        from app.services.diretrizes_contextuais import buscar_instrucoes_especiais

        with patch("app.services.diretrizes_contextuais._buscar_diretrizes_ativas") as mock_buscar:
            mock_buscar.return_value = []

            resultado = await buscar_instrucoes_especiais(
                vaga_id="vaga-sem-instrucao",
            )

            assert resultado == []


class TestExpirarDiretriz:
    """Testes para expirar_diretriz()."""

    @pytest.mark.asyncio
    async def test_expira_diretriz_com_sucesso(self):
        """Deve expirar diretriz corretamente."""
        from app.services.diretrizes_contextuais import expirar_diretriz

        with patch("app.services.diretrizes_contextuais.supabase") as mock_supabase:
            mock_update = MagicMock()
            mock_update.data = [{"id": "diretriz-123", "status": "expirada"}]
            mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_update

            resultado = await expirar_diretriz(
                diretriz_id="diretriz-123",
                motivo="vaga_preenchida",
            )

            assert resultado["success"] is True

    @pytest.mark.asyncio
    async def test_retorna_erro_se_nao_encontrada(self):
        """Deve retornar erro se diretriz não existe."""
        from app.services.diretrizes_contextuais import expirar_diretriz

        with patch("app.services.diretrizes_contextuais.supabase") as mock_supabase:
            mock_update = MagicMock()
            mock_update.data = []
            mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_update

            resultado = await expirar_diretriz(
                diretriz_id="diretriz-inexistente",
                motivo="teste",
            )

            assert resultado["success"] is False


class TestExpirarDiretrizesVaga:
    """Testes para expirar_diretrizes_vaga()."""

    @pytest.mark.asyncio
    async def test_expira_todas_diretrizes_da_vaga(self):
        """Deve expirar todas as diretrizes de uma vaga."""
        from app.services.diretrizes_contextuais import expirar_diretrizes_vaga

        with patch("app.services.diretrizes_contextuais.supabase") as mock_supabase:
            mock_update = MagicMock()
            mock_update.data = [{"id": "d1"}, {"id": "d2"}]
            mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_update

            resultado = await expirar_diretrizes_vaga("vaga-123")

            assert resultado == 2


class TestObterContextoNegociacao:
    """Testes para obter_contexto_negociacao()."""

    @pytest.mark.asyncio
    async def test_calcula_valor_maximo_com_percentual(self):
        """Deve calcular valor máximo baseado em percentual."""
        from app.services.diretrizes_contextuais import obter_contexto_negociacao

        with patch("app.services.diretrizes_contextuais.buscar_margem_para_negociacao") as mock_margem:
            mock_margem.return_value = {
                "tem_margem": True,
                "valor_maximo": None,
                "percentual_maximo": 15.0,
                "escopo": "vaga",
            }

            with patch("app.services.diretrizes_contextuais.buscar_instrucoes_especiais") as mock_instrucoes:
                mock_instrucoes.return_value = []

                vaga = {"id": "vaga-123", "valor": 2000, "hospital_id": "h1", "especialidade_id": "e1"}

                resultado = await obter_contexto_negociacao(vaga, "cliente-123")

                assert resultado["pode_negociar"] is True
                assert resultado["valor_base"] == 2000
                assert resultado["valor_maximo"] == 2300  # 2000 + 15%

    @pytest.mark.asyncio
    async def test_usa_valor_absoluto_quando_definido(self):
        """Deve usar valor absoluto quando definido."""
        from app.services.diretrizes_contextuais import obter_contexto_negociacao

        with patch("app.services.diretrizes_contextuais.buscar_margem_para_negociacao") as mock_margem:
            mock_margem.return_value = {
                "tem_margem": True,
                "valor_maximo": 3000,
                "percentual_maximo": None,
                "escopo": "vaga",
            }

            with patch("app.services.diretrizes_contextuais.buscar_instrucoes_especiais") as mock_instrucoes:
                mock_instrucoes.return_value = ["Instrução especial"]

                vaga = {"id": "vaga-456", "valor": 2500, "hospital_id": "h1", "especialidade_id": "e1"}

                resultado = await obter_contexto_negociacao(vaga, "cliente-456")

                assert resultado["pode_negociar"] is True
                assert resultado["valor_maximo"] == 3000
                assert "Instrução especial" in resultado["instrucoes_especiais"]

    @pytest.mark.asyncio
    async def test_retorna_sem_margem_quando_nao_existe(self):
        """Deve indicar que não pode negociar sem margem."""
        from app.services.diretrizes_contextuais import obter_contexto_negociacao

        with patch("app.services.diretrizes_contextuais.buscar_margem_para_negociacao") as mock_margem:
            mock_margem.return_value = {
                "tem_margem": False,
                "valor_maximo": None,
                "percentual_maximo": None,
            }

            with patch("app.services.diretrizes_contextuais.buscar_instrucoes_especiais") as mock_instrucoes:
                mock_instrucoes.return_value = []

                vaga = {"id": "vaga-789", "valor": 2000}

                resultado = await obter_contexto_negociacao(vaga, "cliente-789")

                assert resultado["pode_negociar"] is False
                assert resultado["valor_base"] == resultado["valor_maximo"]
