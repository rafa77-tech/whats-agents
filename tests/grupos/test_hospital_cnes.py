"""
Testes para lookup CNES de hospitais.

Sprint 61 - Épico 1.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.grupos.hospital_cnes import (
    InfoCNES,
    buscar_hospital_cnes,
    _buscar_cnes_rpc,
    SCORE_MINIMO_CNES,
)


# =====================================================================
# Fixtures
# =====================================================================


CNES_ROW = {
    "cnes_codigo": "2077485",
    "nome_fantasia": "Hospital São Luiz",
    "razao_social": "Rede D'Or São Luiz S.A.",
    "cidade": "São Paulo",
    "uf": "SP",
    "logradouro": "Rua Engenheiro Oscar Americano",
    "numero": "840",
    "bairro": "Morumbi",
    "cep": "05605-050",
    "telefone": "(11) 3093-1100",
    "latitude": -23.5989,
    "longitude": -46.7234,
    "score": 0.72,
}


@pytest.fixture
def mock_supabase():
    """Mock do Supabase."""
    with patch("app.services.grupos.hospital_cnes.supabase") as mock:
        yield mock


# =====================================================================
# _buscar_cnes_rpc
# =====================================================================


class TestBuscarCnesRpc:
    """Testes da chamada RPC de busca CNES."""

    @pytest.mark.asyncio
    async def test_retorna_info_cnes_quando_match(self, mock_supabase):
        """Deve retornar InfoCNES quando RPC retorna match com score suficiente."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[CNES_ROW]
        )

        info = await _buscar_cnes_rpc("Hospital São Luiz", None, "SP")

        assert info is not None
        assert isinstance(info, InfoCNES)
        assert info.cnes_codigo == "2077485"
        assert info.nome_oficial == "Hospital São Luiz"
        assert info.cidade == "São Paulo"
        assert info.estado == "SP"
        assert info.logradouro == "Rua Engenheiro Oscar Americano"
        assert info.telefone == "(11) 3093-1100"
        assert info.latitude == -23.5989
        assert info.score == 0.72

    @pytest.mark.asyncio
    async def test_retorna_none_quando_score_baixo(self, mock_supabase):
        """Deve retornar None quando score < SCORE_MINIMO_CNES."""
        low_score_row = {**CNES_ROW, "score": 0.2}
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[low_score_row]
        )

        info = await _buscar_cnes_rpc("Hospital XYZ", None, "SP")

        assert info is None

    @pytest.mark.asyncio
    async def test_retorna_none_quando_vazio(self, mock_supabase):
        """Deve retornar None quando RPC retorna lista vazia."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[])

        info = await _buscar_cnes_rpc("Hospital Inexistente", None, "SP")

        assert info is None

    @pytest.mark.asyncio
    async def test_retorna_none_em_erro(self, mock_supabase):
        """Deve retornar None e não propagar exceção."""
        mock_supabase.rpc.side_effect = Exception("Connection error")

        info = await _buscar_cnes_rpc("Hospital Erro", None, "SP")

        assert info is None

    @pytest.mark.asyncio
    async def test_usa_razao_social_quando_nome_fantasia_none(self, mock_supabase):
        """Deve usar razao_social quando nome_fantasia é None."""
        row = {**CNES_ROW, "nome_fantasia": None}
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[row])

        info = await _buscar_cnes_rpc("Rede D'Or", None, "SP")

        assert info is not None
        assert info.nome_oficial == "Rede D'Or São Luiz S.A."

    @pytest.mark.asyncio
    async def test_parametros_rpc_corretos(self, mock_supabase):
        """Deve chamar RPC com os parâmetros corretos."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[])

        await _buscar_cnes_rpc("Hospital ABC", "São Paulo", "SP")

        mock_supabase.rpc.assert_called_once_with(
            "buscar_cnes_por_nome",
            {
                "p_nome": "Hospital ABC",
                "p_cidade": "São Paulo",
                "p_uf": "SP",
                "p_limite": 1,
            },
        )

    @pytest.mark.asyncio
    async def test_latitude_longitude_none_quando_ausentes(self, mock_supabase):
        """Deve retornar None para lat/lng quando ausentes na resposta."""
        row = {**CNES_ROW, "latitude": None, "longitude": None}
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[row])

        info = await _buscar_cnes_rpc("Hospital São Luiz", None, "SP")

        assert info is not None
        assert info.latitude is None
        assert info.longitude is None


# =====================================================================
# buscar_hospital_cnes (função principal)
# =====================================================================


class TestBuscarHospitalCnes:
    """Testes da função principal de busca CNES."""

    @pytest.mark.asyncio
    async def test_busca_com_cidade_primeiro(self, mock_supabase):
        """Deve tentar com cidade primeiro quando disponível."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[CNES_ROW]
        )

        info = await buscar_hospital_cnes("Hospital São Luiz", "São Paulo", "SP")

        assert info is not None
        # Primeira chamada deve incluir cidade
        call_args = mock_supabase.rpc.call_args_list[0]
        assert call_args[0][1]["p_cidade"] == "São Paulo"

    @pytest.mark.asyncio
    async def test_fallback_sem_cidade_quando_primeira_falha(self, mock_supabase):
        """Deve tentar sem cidade quando busca com cidade não encontra."""
        # Primeira chamada (com cidade) = vazio; segunda (sem cidade) = match
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.rpc.return_value.execute.side_effect = [
            MagicMock(data=[]),  # Com cidade: nada
            MagicMock(data=[CNES_ROW]),  # Sem cidade: match
        ]

        info = await buscar_hospital_cnes("Hospital São Luiz", "Campinas", "SP")

        assert info is not None
        assert mock_supabase.rpc.call_count == 2
        # Segunda chamada deve ter cidade=None
        second_call_args = mock_supabase.rpc.call_args_list[1]
        assert second_call_args[0][1]["p_cidade"] is None

    @pytest.mark.asyncio
    async def test_pula_cidade_nao_informada(self, mock_supabase):
        """Deve pular busca com cidade 'Não informada'."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[CNES_ROW]
        )

        await buscar_hospital_cnes("Hospital São Luiz", "Não informada", "SP")

        # Deve fazer apenas 1 chamada (sem cidade)
        assert mock_supabase.rpc.call_count == 1
        call_args = mock_supabase.rpc.call_args_list[0]
        assert call_args[0][1]["p_cidade"] is None

    @pytest.mark.asyncio
    async def test_sem_cidade_vai_direto(self, mock_supabase):
        """Deve ir direto sem filtro de cidade quando cidade é None."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[CNES_ROW]
        )

        await buscar_hospital_cnes("Hospital São Luiz", None, "SP")

        assert mock_supabase.rpc.call_count == 1
        call_args = mock_supabase.rpc.call_args_list[0]
        assert call_args[0][1]["p_cidade"] is None

    @pytest.mark.asyncio
    async def test_retorna_none_quando_nenhum_match(self, mock_supabase):
        """Deve retornar None quando nenhum match encontrado."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[])

        info = await buscar_hospital_cnes("Hospital Inexistente XYZ")

        assert info is None


class TestScoreMinimoCnes:
    """Testes da constante de score mínimo."""

    def test_score_minimo_valor(self):
        """Score mínimo deve ser 0.4."""
        assert SCORE_MINIMO_CNES == 0.4
