"""Testes dos endpoints de campanhas.

Sprint 35 - Epic 05
Fase 2 DDD: Mocks apontam para o Application Service
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.core.exceptions import DatabaseError, NotFoundError, ValidationError
from app.services.campanhas.types import (
    AudienceFilters,
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)


@pytest.fixture
def campanha_data():
    """Campanha de teste."""
    return CampanhaData(
        id=16,
        nome_template="Piloto Discovery",
        tipo_campanha=TipoCampanha.DISCOVERY,
        corpo="[DISCOVERY] Usar aberturas dinamicas",
        status=StatusCampanha.AGENDADA,
        audience_filters=AudienceFilters(
            regioes=["ABC"],
            especialidades=["cardiologia"],
            quantidade_alvo=50,
        ),
        total_destinatarios=50,
        enviados=0,
        entregues=0,
        respondidos=0,
    )


@pytest.fixture
def mock_service():
    """Mock do CampanhasApplicationService."""
    with patch("app.api.routes.campanhas.get_campanhas_service") as mock_factory:
        service = AsyncMock()
        mock_factory.return_value = service
        yield service


class TestCriarCampanha:
    """Testes do endpoint POST /campanhas/."""

    @pytest.mark.asyncio
    async def test_criar_campanha_sucesso(self, mock_service, campanha_data):
        """Testa criacao de campanha com sucesso."""
        mock_service.criar_campanha.return_value = campanha_data

        from app.api.routes.campanhas import criar_campanha, CriarCampanhaRequest

        request = CriarCampanhaRequest(
            nome_template="Nova Campanha",
            tipo_campanha="discovery",
            corpo="Oi {nome}!",
            especialidades=["cardiologia"],
            regioes=["ABC"],
            quantidade_alvo=50,
        )

        result = await criar_campanha(request)

        assert result.id == 16
        assert result.nome_template == "Piloto Discovery"
        assert result.tipo_campanha == "discovery"
        mock_service.criar_campanha.assert_called_once()

    @pytest.mark.asyncio
    async def test_criar_campanha_tipo_invalido(self, mock_service):
        """Testa erro ao criar campanha com tipo invalido."""
        from fastapi import HTTPException
        from app.api.routes.campanhas import criar_campanha, CriarCampanhaRequest

        mock_service.criar_campanha.side_effect = ValidationError(
            "Tipo de campanha invalido: tipo_invalido"
        )

        request = CriarCampanhaRequest(
            nome_template="Campanha",
            tipo_campanha="tipo_invalido",
        )

        with pytest.raises(HTTPException) as exc:
            await criar_campanha(request)

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_criar_campanha_erro_banco(self, mock_service):
        """Testa erro quando banco falha."""
        from fastapi import HTTPException
        from app.api.routes.campanhas import criar_campanha, CriarCampanhaRequest

        mock_service.criar_campanha.side_effect = DatabaseError(
            "Erro ao criar campanha no banco de dados."
        )

        request = CriarCampanhaRequest(
            nome_template="Campanha",
            tipo_campanha="oferta",
        )

        with pytest.raises(HTTPException) as exc:
            await criar_campanha(request)

        assert exc.value.status_code == 500


class TestIniciarCampanha:
    """Testes do endpoint POST /campanhas/{id}/iniciar."""

    @pytest.mark.asyncio
    async def test_iniciar_campanha_sucesso(self, mock_service):
        """Testa inicio de campanha com sucesso."""
        mock_service.executar_campanha.return_value = {
            "status": "iniciada",
            "campanha_id": 16,
            "message": "Campanha iniciada com sucesso.",
        }

        from app.api.routes.campanhas import iniciar_campanha

        result = await iniciar_campanha(16)

        assert result["status"] == "iniciada"
        assert result["campanha_id"] == 16
        mock_service.executar_campanha.assert_called_once_with(16)

    @pytest.mark.asyncio
    async def test_iniciar_campanha_nao_encontrada(self, mock_service):
        """Testa erro quando campanha nao existe."""
        from fastapi import HTTPException
        from app.api.routes.campanhas import iniciar_campanha

        mock_service.executar_campanha.side_effect = NotFoundError("Campanha", "999")

        with pytest.raises(HTTPException) as exc:
            await iniciar_campanha(999)

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_iniciar_campanha_status_invalido(self, mock_service):
        """Testa erro quando campanha tem status invalido para iniciar."""
        from fastapi import HTTPException
        from app.api.routes.campanhas import iniciar_campanha

        mock_service.executar_campanha.side_effect = ValidationError(
            "Campanha com status 'concluida' nao pode ser iniciada"
        )

        with pytest.raises(HTTPException) as exc:
            await iniciar_campanha(16)

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_iniciar_campanha_erro_executor(self, mock_service):
        """Testa erro quando executor falha."""
        from fastapi import HTTPException
        from app.api.routes.campanhas import iniciar_campanha

        mock_service.executar_campanha.side_effect = DatabaseError(
            "Erro interno ao executar a campanha."
        )

        with pytest.raises(HTTPException) as exc:
            await iniciar_campanha(16)

        assert exc.value.status_code == 500


class TestRelatorioCampanha:
    """Testes do endpoint GET /campanhas/{id}/relatorio."""

    @pytest.mark.asyncio
    async def test_relatorio_campanha_sucesso(self, mock_service):
        """Testa relatorio de campanha com sucesso."""
        mock_service.relatorio_campanha.return_value = {
            "campanha_id": 16,
            "nome": "Piloto Discovery",
            "tipo_campanha": "discovery",
            "status": "agendada",
            "contadores": {
                "total_destinatarios": 50,
                "enviados": 0,
                "entregues": 0,
                "respondidos": 0,
            },
            "fila": {
                "total": 4,
                "enviados": 2,
                "erros": 1,
                "pendentes": 1,
                "taxa_entrega": 0.5,
            },
            "periodo": {
                "criada_em": None,
                "agendada_para": None,
                "iniciada_em": None,
                "concluida_em": None,
            },
            "audience_filters": {},
        }

        from app.api.routes.campanhas import relatorio_campanha

        result = await relatorio_campanha(16)

        assert result["campanha_id"] == 16
        assert result["nome"] == "Piloto Discovery"
        assert result["tipo_campanha"] == "discovery"
        assert result["fila"]["total"] == 4
        assert result["fila"]["enviados"] == 2
        assert result["fila"]["pendentes"] == 1
        assert result["fila"]["erros"] == 1

    @pytest.mark.asyncio
    async def test_relatorio_campanha_nao_encontrada(self, mock_service):
        """Testa erro quando campanha nao existe."""
        from fastapi import HTTPException
        from app.api.routes.campanhas import relatorio_campanha

        mock_service.relatorio_campanha.side_effect = NotFoundError("Campanha", "999")

        with pytest.raises(HTTPException) as exc:
            await relatorio_campanha(999)

        assert exc.value.status_code == 404


class TestPreviewSegmento:
    """Testes do endpoint POST /campanhas/segmento/preview."""

    @pytest.mark.asyncio
    async def test_preview_segmento_sucesso(self, mock_service):
        """Testa preview de segmento."""
        mock_service.preview_segmento.return_value = {
            "total": 100,
            "amostra": [
                {"nome": "Carlos", "especialidade": "Cardiologia", "regiao": "ABC"},
                {"nome": "Maria", "especialidade": "Anestesiologia", "regiao": "SP"},
            ],
        }

        from app.api.routes.campanhas import preview_segmento

        result = await preview_segmento({"especialidade": "cardiologia"})

        assert result["total"] == 100
        assert len(result["amostra"]) == 2
        assert result["amostra"][0]["nome"] == "Carlos"


class TestListarCampanhas:
    """Testes do endpoint GET /campanhas/."""

    @pytest.mark.asyncio
    async def test_listar_campanhas_sucesso(self, mock_service):
        """Testa listagem de campanhas."""
        mock_service.listar_campanhas.return_value = {
            "campanhas": [
                {
                    "id": 16,
                    "nome_template": "Discovery",
                    "tipo_campanha": "discovery",
                    "status": "agendada",
                    "total_destinatarios": 50,
                    "enviados": 0,
                    "entregues": 0,
                    "respondidos": 0,
                },
                {
                    "id": 17,
                    "nome_template": "Oferta",
                    "tipo_campanha": "oferta",
                    "status": "ativa",
                    "total_destinatarios": 100,
                    "enviados": 50,
                    "entregues": 45,
                    "respondidos": 10,
                },
            ],
            "total": 2,
        }

        from app.api.routes.campanhas import listar_campanhas

        result = await listar_campanhas()

        assert result["total"] == 2
        assert len(result["campanhas"]) == 2
        assert result["campanhas"][0]["id"] == 16

    @pytest.mark.asyncio
    async def test_listar_campanhas_com_filtros(self, mock_service):
        """Testa listagem com filtros."""
        mock_service.listar_campanhas.return_value = {
            "campanhas": [
                {
                    "id": 16,
                    "nome_template": "Discovery",
                    "tipo_campanha": "discovery",
                    "status": "agendada",
                    "total_destinatarios": 50,
                    "enviados": 0,
                    "entregues": 0,
                    "respondidos": 0,
                },
            ],
            "total": 1,
        }

        from app.api.routes.campanhas import listar_campanhas

        result = await listar_campanhas(status="agendada", tipo="discovery")

        assert result["total"] == 1
        mock_service.listar_campanhas.assert_called_once_with(
            status="agendada", tipo="discovery", limit=50
        )


class TestBuscarCampanha:
    """Testes do endpoint GET /campanhas/{id}."""

    @pytest.mark.asyncio
    async def test_buscar_campanha_sucesso(self, mock_service, campanha_data):
        """Testa busca de campanha por ID."""
        mock_service.buscar_campanha.return_value = campanha_data

        from app.api.routes.campanhas import buscar_campanha

        result = await buscar_campanha(16)

        assert result["id"] == 16
        assert result["nome_template"] == "Piloto Discovery"

    @pytest.mark.asyncio
    async def test_buscar_campanha_nao_encontrada(self, mock_service):
        """Testa erro quando campanha nao existe."""
        from fastapi import HTTPException
        from app.api.routes.campanhas import buscar_campanha

        mock_service.buscar_campanha.side_effect = NotFoundError("Campanha", "999")

        with pytest.raises(HTTPException) as exc:
            await buscar_campanha(999)

        assert exc.value.status_code == 404


class TestAtualizarStatusCampanha:
    """Testes do endpoint PATCH /campanhas/{id}/status."""

    @pytest.mark.asyncio
    async def test_atualizar_status_sucesso(self, mock_service):
        """Testa atualizacao de status com sucesso."""
        mock_service.atualizar_status.return_value = {
            "campanha_id": 16,
            "status_anterior": "agendada",
            "status_novo": "ativa",
        }

        from app.api.routes.campanhas import atualizar_status_campanha

        result = await atualizar_status_campanha(16, "ativa")

        assert result["campanha_id"] == 16
        assert result["status_anterior"] == "agendada"
        assert result["status_novo"] == "ativa"

    @pytest.mark.asyncio
    async def test_atualizar_status_invalido(self, mock_service):
        """Testa erro ao atualizar para status invalido."""
        from fastapi import HTTPException
        from app.api.routes.campanhas import atualizar_status_campanha

        mock_service.atualizar_status.side_effect = ValidationError(
            "Status invalido: status_invalido"
        )

        with pytest.raises(HTTPException) as exc:
            await atualizar_status_campanha(16, "status_invalido")

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_atualizar_status_campanha_nao_encontrada(self, mock_service):
        """Testa erro quando campanha nao existe."""
        from fastapi import HTTPException
        from app.api.routes.campanhas import atualizar_status_campanha

        mock_service.atualizar_status.side_effect = NotFoundError("Campanha", "999")

        with pytest.raises(HTTPException) as exc:
            await atualizar_status_campanha(999, "ativa")

        assert exc.value.status_code == 404


class TestCriarCampanhaRequest:
    """Testes do modelo CriarCampanhaRequest."""

    def test_modelo_com_valores_default(self):
        """Testa criacao do modelo com valores default."""
        from app.api.routes.campanhas import CriarCampanhaRequest

        request = CriarCampanhaRequest(nome_template="Teste")

        assert request.nome_template == "Teste"
        assert request.tipo_campanha == "oferta"
        assert request.corpo is None
        assert request.tom == "amigavel"
        assert request.quantidade_alvo == 50
        assert request.pode_ofertar is True

    def test_modelo_com_todos_campos(self):
        """Testa criacao do modelo com todos os campos."""
        from app.api.routes.campanhas import CriarCampanhaRequest
        from datetime import datetime

        agendar_para = datetime(2026, 1, 25, 12, 0, 0)

        request = CriarCampanhaRequest(
            nome_template="Campanha Completa",
            tipo_campanha="discovery",
            corpo="Oi {nome}!",
            tom="profissional",
            objetivo="Prospectar novos medicos",
            especialidades=["cardiologia", "anestesiologia"],
            regioes=["ABC", "SP"],
            quantidade_alvo=100,
            agendar_para=agendar_para,
            pode_ofertar=False,
        )

        assert request.nome_template == "Campanha Completa"
        assert request.tipo_campanha == "discovery"
        assert request.corpo == "Oi {nome}!"
        assert request.tom == "profissional"
        assert request.objetivo == "Prospectar novos medicos"
        assert request.especialidades == ["cardiologia", "anestesiologia"]
        assert request.regioes == ["ABC", "SP"]
        assert request.quantidade_alvo == 100
        assert request.agendar_para == agendar_para
        assert request.pode_ofertar is False
