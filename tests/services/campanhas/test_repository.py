"""Testes do repository de campanhas.

Sprint 35 - Epic 03
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.services.campanhas.repository import CampanhaRepository
from app.services.campanhas.types import (
    AudienceFilters,
    StatusCampanha,
    TipoCampanha,
)


@pytest.fixture
def repository():
    """Instancia do repository."""
    return CampanhaRepository()


@pytest.fixture
def mock_campanha_row():
    """Linha do banco mockada."""
    return {
        "id": 16,
        "nome_template": "Piloto Discovery",
        "tipo_campanha": "discovery",
        "corpo": "[DISCOVERY] Usar aberturas dinamicas",
        "tom": "amigavel",
        "status": "agendada",
        "agendar_para": "2026-01-21T12:00:00Z",
        "audience_filters": {
            "regioes": ["ABC"],
            "especialidades": ["cardiologia"],
            "quantidade_alvo": 50,
        },
        "pode_ofertar": False,
        "total_destinatarios": 50,
        "enviados": 0,
        "entregues": 0,
        "respondidos": 0,
        "objetivo": "Conhecer medicos",
        "regras": None,
        "escopo_vagas": None,
        "created_at": "2026-01-20T10:00:00Z",
        "iniciada_em": None,
        "concluida_em": None,
    }


class TestBuscarPorId:
    """Testes do metodo buscar_por_id."""

    @pytest.mark.asyncio
    async def test_encontrado(self, repository, mock_campanha_row):
        """Testa busca por ID quando existe."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_campanha_row

            result = await repository.buscar_por_id(16)

            assert result is not None
            assert result.id == 16
            assert result.nome_template == "Piloto Discovery"
            assert result.tipo_campanha == TipoCampanha.DISCOVERY
            assert result.status == StatusCampanha.AGENDADA
            assert result.audience_filters.regioes == ["ABC"]
            assert result.audience_filters.especialidades == ["cardiologia"]

    @pytest.mark.asyncio
    async def test_nao_encontrado(self, repository):
        """Testa busca por ID quando nao existe."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

            result = await repository.buscar_por_id(999)

            assert result is None

    @pytest.mark.asyncio
    async def test_erro_retorna_none(self, repository):
        """Testa que erro retorna None."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("DB Error")

            result = await repository.buscar_por_id(16)

            assert result is None


class TestListarAgendadas:
    """Testes do metodo listar_agendadas."""

    @pytest.mark.asyncio
    async def test_retorna_campanhas(self, repository, mock_campanha_row):
        """Testa listagem de campanhas agendadas."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value.data = [mock_campanha_row]

            result = await repository.listar_agendadas()

            assert len(result) == 1
            assert result[0].id == 16
            assert result[0].status == StatusCampanha.AGENDADA

    @pytest.mark.asyncio
    async def test_retorna_lista_vazia(self, repository):
        """Testa listagem quando nao ha campanhas."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value.data = []

            result = await repository.listar_agendadas()

            assert result == []


class TestListarAtivas:
    """Testes do metodo listar_ativas."""

    @pytest.mark.asyncio
    async def test_retorna_campanhas_ativas(self, repository, mock_campanha_row):
        """Testa listagem de campanhas ativas."""
        mock_campanha_row["status"] = "ativa"

        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_campanha_row]

            result = await repository.listar_ativas()

            assert len(result) == 1
            assert result[0].status == StatusCampanha.ATIVA


class TestCriar:
    """Testes do metodo criar."""

    @pytest.mark.asyncio
    async def test_criar_campanha_simples(self, repository):
        """Testa criacao de campanha simples."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
                "id": 17,
                "nome_template": "Nova Campanha",
                "tipo_campanha": "oferta",
                "status": "rascunho",
                "audience_filters": {},
                "pode_ofertar": True,
                "total_destinatarios": 0,
                "enviados": 0,
                "entregues": 0,
                "respondidos": 0,
            }]

            result = await repository.criar(
                nome_template="Nova Campanha",
                tipo_campanha=TipoCampanha.OFERTA,
                pode_ofertar=True,
            )

            assert result is not None
            assert result.id == 17
            assert result.tipo_campanha == TipoCampanha.OFERTA
            assert result.status == StatusCampanha.RASCUNHO

    @pytest.mark.asyncio
    async def test_criar_campanha_agendada(self, repository):
        """Testa criacao de campanha com agendamento."""
        agendar_para = datetime(2026, 1, 25, 12, 0, 0)

        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
                "id": 18,
                "nome_template": "Campanha Agendada",
                "tipo_campanha": "discovery",
                "status": "agendada",
                "agendar_para": agendar_para.isoformat(),
                "audience_filters": {"regioes": ["SP"]},
                "pode_ofertar": False,
                "total_destinatarios": 0,
                "enviados": 0,
                "entregues": 0,
                "respondidos": 0,
            }]

            result = await repository.criar(
                nome_template="Campanha Agendada",
                tipo_campanha=TipoCampanha.DISCOVERY,
                agendar_para=agendar_para,
                audience_filters=AudienceFilters(regioes=["SP"]),
            )

            assert result is not None
            assert result.status == StatusCampanha.AGENDADA

            # Verificar que insert foi chamado com status agendada
            call_args = mock_supabase.table.return_value.insert.call_args
            assert call_args[0][0]["status"] == "agendada"


class TestAtualizarStatus:
    """Testes do metodo atualizar_status."""

    @pytest.mark.asyncio
    async def test_atualizar_para_ativa(self, repository):
        """Testa atualizacao de status para ativa."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            result = await repository.atualizar_status(16, StatusCampanha.ATIVA)

            assert result is True

            # Verificar que update foi chamado com status e iniciada_em
            call_args = mock_supabase.table.return_value.update.call_args
            assert call_args[0][0]["status"] == "ativa"
            assert "iniciada_em" in call_args[0][0]
            assert "started_at" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_atualizar_para_concluida(self, repository):
        """Testa atualizacao de status para concluida."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            result = await repository.atualizar_status(16, StatusCampanha.CONCLUIDA)

            assert result is True

            # Verificar que update foi chamado com status e concluida_em
            call_args = mock_supabase.table.return_value.update.call_args
            assert call_args[0][0]["status"] == "concluida"
            assert "concluida_em" in call_args[0][0]
            assert "completed_at" in call_args[0][0]


class TestIncrementarEnviados:
    """Testes do metodo incrementar_enviados."""

    @pytest.mark.asyncio
    async def test_incrementa_corretamente(self, repository):
        """Testa incremento de enviados."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            # Mock busca atual
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"enviados": 10}
            # Mock update
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            result = await repository.incrementar_enviados(16, 5)

            assert result is True

            # Verificar que update foi chamado com valor correto (10 + 5 = 15)
            update_calls = mock_supabase.table.return_value.update.call_args_list
            assert len(update_calls) > 0
            update_data = update_calls[0][0][0]
            assert update_data["enviados"] == 15

    @pytest.mark.asyncio
    async def test_incrementa_de_zero(self, repository):
        """Testa incremento quando enviados eh zero ou None."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"enviados": None}
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            result = await repository.incrementar_enviados(16, 1)

            assert result is True

            update_data = mock_supabase.table.return_value.update.call_args[0][0]
            assert update_data["enviados"] == 1


class TestAtualizarTotalDestinatarios:
    """Testes do metodo atualizar_total_destinatarios."""

    @pytest.mark.asyncio
    async def test_atualiza_total(self, repository):
        """Testa atualizacao do total de destinatarios."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            result = await repository.atualizar_total_destinatarios(16, 100)

            assert result is True

            update_data = mock_supabase.table.return_value.update.call_args[0][0]
            assert update_data["total_destinatarios"] == 100


class TestAtualizarContadores:
    """Testes do metodo atualizar_contadores."""

    @pytest.mark.asyncio
    async def test_atualiza_todos_contadores(self, repository):
        """Testa atualizacao de todos os contadores."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            result = await repository.atualizar_contadores(
                campanha_id=16,
                enviados=50,
                entregues=45,
                respondidos=10,
            )

            assert result is True

            update_data = mock_supabase.table.return_value.update.call_args[0][0]
            assert update_data["enviados"] == 50
            assert update_data["entregues"] == 45
            assert update_data["respondidos"] == 10

    @pytest.mark.asyncio
    async def test_atualiza_parcial(self, repository):
        """Testa atualizacao parcial de contadores."""
        with patch("app.services.campanhas.repository.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            result = await repository.atualizar_contadores(
                campanha_id=16,
                respondidos=5,
            )

            assert result is True

            update_data = mock_supabase.table.return_value.update.call_args[0][0]
            assert "respondidos" in update_data
            assert "enviados" not in update_data
            assert "entregues" not in update_data


class TestTypes:
    """Testes dos tipos."""

    def test_tipo_campanha_values(self):
        """Testa valores do enum TipoCampanha."""
        assert TipoCampanha.DISCOVERY.value == "discovery"
        assert TipoCampanha.OFERTA.value == "oferta"
        assert TipoCampanha.REATIVACAO.value == "reativacao"
        assert TipoCampanha.FOLLOWUP.value == "followup"

    def test_status_campanha_values(self):
        """Testa valores do enum StatusCampanha."""
        assert StatusCampanha.RASCUNHO.value == "rascunho"
        assert StatusCampanha.AGENDADA.value == "agendada"
        assert StatusCampanha.ATIVA.value == "ativa"
        assert StatusCampanha.CONCLUIDA.value == "concluida"

    def test_audience_filters_to_dict(self):
        """Testa conversao de AudienceFilters para dict."""
        filters = AudienceFilters(
            regioes=["ABC", "Capital"],
            especialidades=["cardiologia"],
            quantidade_alvo=100,
        )

        result = filters.to_dict()

        assert result["regioes"] == ["ABC", "Capital"]
        assert result["especialidades"] == ["cardiologia"]
        assert result["quantidade_alvo"] == 100

    def test_audience_filters_from_dict(self):
        """Testa criacao de AudienceFilters a partir de dict."""
        data = {
            "regioes": ["SP"],
            "especialidades": ["anestesiologia", "cardiologia"],
            "quantidade_alvo": 200,
        }

        result = AudienceFilters.from_dict(data)

        assert result.regioes == ["SP"]
        assert result.especialidades == ["anestesiologia", "cardiologia"]
        assert result.quantidade_alvo == 200

    def test_audience_filters_from_empty_dict(self):
        """Testa criacao de AudienceFilters a partir de dict vazio."""
        result = AudienceFilters.from_dict({})

        assert result.regioes == []
        assert result.especialidades == []
        assert result.quantidade_alvo == 50  # default

    def test_audience_filters_from_none(self):
        """Testa criacao de AudienceFilters a partir de None."""
        result = AudienceFilters.from_dict(None)

        assert result.regioes == []
        assert result.especialidades == []
