"""
Testes do Application Service de Campanhas.

Valida que o CampanhasApplicationService orquestra corretamente
os casos de uso, delegando ao repositório existente e lançando
exceções de domínio (não HTTPException).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.contexts.campanhas.application import CampanhasApplicationService
from app.core.exceptions import DatabaseError, NotFoundError, ValidationError
from app.services.campanhas.types import (
    AudienceFilters,
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)


@pytest.fixture
def mock_repository():
    """Repositório mockado para testes unitários."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_executor():
    """Executor mockado para testes unitários."""
    executor = AsyncMock()
    return executor


@pytest.fixture
def mock_segmentacao():
    """Serviço de segmentação mockado."""
    seg = AsyncMock()
    seg.contar_segmento = AsyncMock(return_value=25)
    seg.buscar_segmento = AsyncMock(return_value=[])
    return seg


@pytest.fixture
def service(mock_repository, mock_executor, mock_segmentacao):
    """Application Service com dependências injetadas."""
    return CampanhasApplicationService(
        repository=mock_repository,
        executor=mock_executor,
        segmentacao=mock_segmentacao,
    )


@pytest.fixture
def campanha_fixture():
    """Campanha de teste."""
    return CampanhaData(
        id=1,
        nome_template="Teste Discovery",
        tipo_campanha=TipoCampanha.DISCOVERY,
        status=StatusCampanha.AGENDADA,
        total_destinatarios=25,
        enviados=0,
        entregues=0,
        respondidos=0,
        audience_filters=AudienceFilters(
            regioes=["ABC"],
            especialidades=["cardiologia"],
            quantidade_alvo=50,
        ),
    )


# --- criar_campanha ---


class TestCriarCampanha:
    """Testes para o caso de uso de criação de campanha."""

    @pytest.mark.asyncio
    async def test_criar_campanha_sucesso(self, service, mock_repository, campanha_fixture):
        mock_repository.criar.return_value = campanha_fixture
        mock_repository.atualizar_total_destinatarios.return_value = True

        result = await service.criar_campanha(
            nome_template="Teste Discovery",
            tipo_campanha="discovery",
            especialidades=["cardiologia"],
            regioes=["ABC"],
        )

        assert result.id == 1
        assert result.nome_template == "Teste Discovery"
        mock_repository.criar.assert_awaited_once()
        mock_repository.atualizar_total_destinatarios.assert_awaited_once_with(1, 25)

    @pytest.mark.asyncio
    async def test_criar_campanha_tipo_invalido(self, service):
        with pytest.raises(ValidationError, match="Tipo de campanha inválido"):
            await service.criar_campanha(
                nome_template="Teste",
                tipo_campanha="tipo_inexistente",
            )

    @pytest.mark.asyncio
    async def test_criar_campanha_erro_banco(self, service, mock_repository):
        mock_repository.criar.return_value = None

        with pytest.raises(DatabaseError, match="Erro ao criar campanha"):
            await service.criar_campanha(
                nome_template="Teste",
                tipo_campanha="discovery",
            )


# --- executar_campanha ---


class TestExecutarCampanha:
    """Testes para o caso de uso de execução de campanha."""

    @pytest.mark.asyncio
    async def test_executar_campanha_sucesso(
        self, service, mock_repository, mock_executor, campanha_fixture
    ):
        mock_repository.buscar_por_id.return_value = campanha_fixture
        mock_executor.executar.return_value = True

        result = await service.executar_campanha(1)

        assert result["status"] == "iniciada"
        assert result["campanha_id"] == 1
        mock_executor.executar.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_executar_campanha_nao_encontrada(self, service, mock_repository):
        mock_repository.buscar_por_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.executar_campanha(999)

    @pytest.mark.asyncio
    async def test_executar_campanha_status_invalido(
        self, service, mock_repository, campanha_fixture
    ):
        campanha_fixture.status = StatusCampanha.CONCLUIDA
        mock_repository.buscar_por_id.return_value = campanha_fixture

        with pytest.raises(ValidationError, match="não pode ser iniciada"):
            await service.executar_campanha(1)

    @pytest.mark.asyncio
    async def test_executar_campanha_erro_executor(
        self, service, mock_repository, mock_executor, campanha_fixture
    ):
        mock_repository.buscar_por_id.return_value = campanha_fixture
        mock_executor.executar.return_value = False

        with pytest.raises(DatabaseError, match="Erro interno"):
            await service.executar_campanha(1)


# --- buscar_campanha ---


class TestBuscarCampanha:
    """Testes para o caso de uso de busca de campanha."""

    @pytest.mark.asyncio
    async def test_buscar_campanha_sucesso(
        self, service, mock_repository, campanha_fixture
    ):
        mock_repository.buscar_por_id.return_value = campanha_fixture

        result = await service.buscar_campanha(1)

        assert result.id == 1
        mock_repository.buscar_por_id.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_buscar_campanha_nao_encontrada(self, service, mock_repository):
        mock_repository.buscar_por_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.buscar_campanha(999)


# --- listar_campanhas ---


class TestListarCampanhas:
    """Testes para o caso de uso de listagem de campanhas."""

    @pytest.mark.asyncio
    async def test_listar_por_status(
        self, service, mock_repository, campanha_fixture
    ):
        mock_repository.listar.return_value = [campanha_fixture]

        result = await service.listar_campanhas(status="agendada")

        assert result["total"] == 1
        assert len(result["campanhas"]) == 1
        mock_repository.listar.assert_awaited_once_with(
            status="agendada", tipo=None, limit=50
        )

    @pytest.mark.asyncio
    async def test_listar_status_invalido(self, service):
        with pytest.raises(ValidationError, match="Status inválido"):
            await service.listar_campanhas(status="inexistente")

    @pytest.mark.asyncio
    async def test_listar_todas(self, service, mock_repository, campanha_fixture):
        mock_repository.listar.return_value = [campanha_fixture]

        result = await service.listar_campanhas()

        assert result["total"] == 1
        mock_repository.listar.assert_awaited_once_with(
            status=None, tipo=None, limit=50
        )


# --- atualizar_status ---


class TestAtualizarStatus:
    """Testes para o caso de uso de atualização de status."""

    @pytest.mark.asyncio
    async def test_atualizar_status_sucesso(
        self, service, mock_repository, campanha_fixture
    ):
        mock_repository.buscar_por_id.return_value = campanha_fixture
        mock_repository.atualizar_status.return_value = True

        result = await service.atualizar_status(1, "ativa")

        assert result["status_anterior"] == "agendada"
        assert result["status_novo"] == "ativa"
        mock_repository.atualizar_status.assert_awaited_once_with(
            1, StatusCampanha.ATIVA
        )

    @pytest.mark.asyncio
    async def test_atualizar_status_invalido(self, service):
        with pytest.raises(ValidationError, match="Status inválido"):
            await service.atualizar_status(1, "status_fake")

    @pytest.mark.asyncio
    async def test_atualizar_status_campanha_nao_encontrada(
        self, service, mock_repository
    ):
        mock_repository.buscar_por_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.atualizar_status(999, "ativa")

    @pytest.mark.asyncio
    async def test_atualizar_status_erro_persistencia(
        self, service, mock_repository, campanha_fixture
    ):
        mock_repository.buscar_por_id.return_value = campanha_fixture
        mock_repository.atualizar_status.return_value = False

        with pytest.raises(DatabaseError, match="Erro ao atualizar"):
            await service.atualizar_status(1, "ativa")


# --- relatorio_campanha ---


class TestRelatorioCampanha:
    """Testes para o caso de uso de relatório de campanha."""

    @pytest.mark.asyncio
    async def test_relatorio_sucesso(
        self, service, mock_repository, campanha_fixture
    ):
        mock_repository.buscar_por_id.return_value = campanha_fixture
        mock_repository.buscar_envios_da_fila.return_value = [
            {"status": "enviada"},
            {"status": "enviada"},
            {"status": "erro"},
        ]

        result = await service.relatorio_campanha(1)

        assert result["campanha_id"] == 1
        assert result["nome"] == "Teste Discovery"
        assert result["tipo_campanha"] == "discovery"
        assert result["status"] == "agendada"
        assert "contadores" in result
        assert "periodo" in result
        assert result["fila"]["total"] == 3

    @pytest.mark.asyncio
    async def test_relatorio_campanha_nao_encontrada(self, service, mock_repository):
        mock_repository.buscar_por_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.relatorio_campanha(999)


# --- preview_segmento ---


class TestPreviewSegmento:
    """Testes para o caso de uso de preview de segmento."""

    @pytest.mark.asyncio
    async def test_preview_segmento_sucesso(self, service, mock_segmentacao):
        mock_segmentacao.contar_segmento.return_value = 10
        mock_segmentacao.buscar_segmento.return_value = [
            {
                "primeiro_nome": "Carlos",
                "especialidade_nome": "Cardiologia",
                "regiao": "ABC",
            }
        ]

        result = await service.preview_segmento({"especialidade": "cardiologia"})

        assert result["total"] == 10
        assert len(result["amostra"]) == 1
        assert result["amostra"][0]["nome"] == "Carlos"


# --- Testes de integração: exceções nunca são HTTPException ---


class TestExcecoesDominio:
    """
    Verifica que o Application Service NUNCA lança HTTPException.

    Isso é o teste mais importante do ponto de vista arquitetural (ADR-007):
    a camada de aplicação deve lançar exceções de domínio, e a rota
    converte para HTTP.
    """

    @pytest.mark.asyncio
    async def test_nao_importa_httpexception(self):
        """Verifica que o módulo não importa HTTPException."""
        import inspect
        import app.contexts.campanhas.application as mod

        source = inspect.getsource(mod)
        assert "HTTPException" not in source, (
            "Application Service não deve importar HTTPException. "
            "Use exceções de app.core.exceptions."
        )

    @pytest.mark.asyncio
    async def test_nao_importa_fastapi(self):
        """Verifica que o módulo não importa nada do FastAPI."""
        import inspect
        import app.contexts.campanhas.application as mod

        source = inspect.getsource(mod)
        assert "from fastapi" not in source, (
            "Application Service não deve depender do FastAPI. "
            "Isso permite testes sem framework web."
        )
