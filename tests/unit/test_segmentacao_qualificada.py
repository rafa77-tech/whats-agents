"""
Testes do buscar_alvos_campanha.

Sprint 24 E01: Target set qualificado para campanhas.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

from app.services.segmentacao import SegmentacaoService


@pytest.fixture
def service():
    return SegmentacaoService()


class TestBuscarAlvosCampanha:
    """Testes da função buscar_alvos_campanha."""

    @pytest.mark.asyncio
    @patch("app.services.segmentacao.supabase")
    async def test_retorna_medicos_elegiveis(self, mock_supabase, service):
        """Deve retornar médicos elegíveis via RPC."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "uuid-1",
                "nome": "Dr Carlos",
                "telefone": "5511999998888",
                "especialidade_nome": "Cardiologia",
                "regiao": "abc",
                "last_outbound_at": None,
                "contact_count_7d": 0,
            },
            {
                "id": "uuid-2",
                "nome": "Dra Maria",
                "telefone": "5511999997777",
                "especialidade_nome": "Cardiologia",
                "regiao": "abc",
                "last_outbound_at": "2024-12-01T10:00:00Z",
                "contact_count_7d": 2,
            },
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        result = await service.buscar_alvos_campanha(
            filtros={"especialidade": "Cardiologia"},
            limite=100
        )

        assert len(result) == 2
        assert result[0]["nome"] == "Dr Carlos"
        assert result[1]["nome"] == "Dra Maria"

        # Verificar chamada RPC
        mock_supabase.rpc.assert_called_once_with("buscar_alvos_campanha", {
            "p_filtros": {"especialidade": "Cardiologia"},
            "p_dias_sem_contato": 14,
            "p_excluir_cooling": True,
            "p_excluir_em_atendimento": True,
            "p_contact_cap": 5,
            "p_limite": 100,
        })

    @pytest.mark.asyncio
    @patch("app.services.segmentacao.supabase")
    async def test_parametros_customizados(self, mock_supabase, service):
        """Deve passar parâmetros customizados para RPC."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        await service.buscar_alvos_campanha(
            filtros={"regiao": "sp"},
            dias_sem_contato=7,
            excluir_cooling=False,
            excluir_em_atendimento=False,
            contact_cap=10,
            limite=500,
        )

        mock_supabase.rpc.assert_called_once_with("buscar_alvos_campanha", {
            "p_filtros": {"regiao": "sp"},
            "p_dias_sem_contato": 7,
            "p_excluir_cooling": False,
            "p_excluir_em_atendimento": False,
            "p_contact_cap": 10,
            "p_limite": 500,
        })

    @pytest.mark.asyncio
    @patch("app.services.segmentacao.supabase")
    async def test_sem_filtros(self, mock_supabase, service):
        """Deve funcionar sem filtros demográficos."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "uuid-1", "nome": "Dr X"}]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        result = await service.buscar_alvos_campanha()

        assert len(result) == 1
        mock_supabase.rpc.assert_called_once()
        call_args = mock_supabase.rpc.call_args[0]
        assert call_args[1]["p_filtros"] == {}

    @pytest.mark.asyncio
    @patch("app.services.segmentacao.supabase")
    async def test_retorno_vazio(self, mock_supabase, service):
        """Deve retornar lista vazia se não houver elegíveis."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        result = await service.buscar_alvos_campanha(
            filtros={"especialidade": "Inexistente"}
        )

        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.segmentacao.supabase")
    async def test_erro_rpc_propaga_excecao(self, mock_supabase, service):
        """Deve propagar exceção em caso de erro na RPC."""
        mock_supabase.rpc.return_value.execute.side_effect = Exception("RPC failed")

        with pytest.raises(Exception) as exc_info:
            await service.buscar_alvos_campanha()

        assert "RPC failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("app.services.segmentacao.supabase")
    async def test_campos_retornados(self, mock_supabase, service):
        """Deve retornar campos esperados para cada médico."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "uuid-123",
                "nome": "Dr Carlos Silva",
                "telefone": "5511999998888",
                "especialidade_nome": "Cardiologia",
                "regiao": "abc",
                "last_outbound_at": "2024-12-15T10:00:00Z",
                "contact_count_7d": 3,
            }
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        result = await service.buscar_alvos_campanha()

        medico = result[0]
        assert "id" in medico
        assert "nome" in medico
        assert "telefone" in medico
        assert "especialidade_nome" in medico
        assert "regiao" in medico
        assert "last_outbound_at" in medico
        assert "contact_count_7d" in medico


class TestBuscarAlvosCampanhaIntegracao:
    """
    Testes de integração (requerem banco).

    Estes testes validam o comportamento da RPC no banco.
    Executar apenas em ambiente de staging.
    """

    @pytest.mark.skip(reason="Requer banco de staging")
    @pytest.mark.asyncio
    async def test_medico_sem_doctor_state_incluido(self, service):
        """Médico novo (sem doctor_state) deve ser incluído."""
        # Criar médico sem doctor_state
        # Chamar buscar_alvos_campanha
        # Verificar que médico está no resultado
        pass

    @pytest.mark.skip(reason="Requer banco de staging")
    @pytest.mark.asyncio
    async def test_medico_contact_cap_excedido_excluido(self, service):
        """Médico com contact_count_7d >= cap deve ser excluído."""
        # Criar médico com contact_count_7d = 5
        # Chamar buscar_alvos_campanha com contact_cap=5
        # Verificar que médico NÃO está no resultado
        pass

    @pytest.mark.skip(reason="Requer banco de staging")
    @pytest.mark.asyncio
    async def test_medico_conversa_humana_excluido(self, service):
        """Médico com conversa controlled_by='human' deve ser excluído."""
        # Criar médico com conversa ativa sob humano
        # Chamar buscar_alvos_campanha
        # Verificar que médico NÃO está no resultado
        pass

    @pytest.mark.skip(reason="Requer banco de staging")
    @pytest.mark.asyncio
    async def test_medico_inbound_recente_excluido(self, service):
        """Médico com inbound < 30min deve ser excluído se flag ativa."""
        # Criar médico com last_inbound_at = 10 minutos atrás
        # Chamar buscar_alvos_campanha com excluir_em_atendimento=True
        # Verificar que médico NÃO está no resultado
        pass

    @pytest.mark.skip(reason="Requer banco de staging")
    @pytest.mark.asyncio
    async def test_ordem_deterministica(self, service):
        """Ordem deve ser determinística (mesmo resultado em execuções consecutivas)."""
        # Criar vários médicos
        # Chamar buscar_alvos_campanha 2x
        # Verificar que ordem é idêntica
        pass


class TestBuscarSegmentoDeprecated:
    """Testes do método legado buscar_segmento."""

    @pytest.mark.asyncio
    @patch("app.services.segmentacao.supabase")
    async def test_ainda_funciona(self, mock_supabase, service):
        """Método legado ainda deve funcionar."""
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.neq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[{"id": "1"}])

        mock_supabase.table.return_value = mock_query

        result = await service.buscar_segmento(
            filtros={"especialidade": "Cardiologia"},
            limite=100
        )

        assert len(result) == 1
