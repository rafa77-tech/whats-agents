"""Testes do executor de campanhas.

Sprint 35 - Epic 04
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.campanhas.executor import CampanhaExecutor
from app.services.campanhas.types import (
    AudienceFilters,
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)


@pytest.fixture
def executor():
    """Instancia do executor."""
    return CampanhaExecutor()


@pytest.fixture
def campanha_discovery():
    """Campanha discovery de teste."""
    return CampanhaData(
        id=16,
        nome_template="Piloto Discovery",
        tipo_campanha=TipoCampanha.DISCOVERY,
        corpo="[DISCOVERY] Usar aberturas dinamicas",
        status=StatusCampanha.AGENDADA,
        audience_filters=AudienceFilters(quantidade_alvo=2),
    )


@pytest.fixture
def campanha_oferta():
    """Campanha oferta de teste."""
    return CampanhaData(
        id=17,
        nome_template="Oferta Cardio",
        tipo_campanha=TipoCampanha.OFERTA,
        corpo="Oi Dr {nome}! Temos uma vaga de {especialidade} pra vc!",
        status=StatusCampanha.AGENDADA,
        audience_filters=AudienceFilters(especialidades=["cardiologia"]),
    )


@pytest.fixture
def campanha_reativacao():
    """Campanha reativacao de teste."""
    return CampanhaData(
        id=18,
        nome_template="Reativacao",
        tipo_campanha=TipoCampanha.REATIVACAO,
        corpo=None,  # Vai usar template padrao
        status=StatusCampanha.AGENDADA,
        audience_filters=AudienceFilters(),
    )


@pytest.fixture
def destinatarios():
    """Lista de destinatarios de teste."""
    return [
        {"id": "uuid-1", "primeiro_nome": "Carlos", "especialidade_nome": "Cardiologia"},
        {"id": "uuid-2", "primeiro_nome": "Maria", "especialidade_nome": "Anestesiologia"},
    ]


class TestExecutar:
    """Testes do metodo executar."""

    @pytest.mark.asyncio
    async def test_executar_campanha_discovery(self, executor, campanha_discovery, destinatarios):
        """Testa execucao de campanha discovery."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.segmentacao_service") as mock_seg, \
             patch("app.services.campanhas.executor.fila_service") as mock_fila, \
             patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura:

            # Setup mocks
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_segmento = AsyncMock(return_value=destinatarios)
            mock_fila.enfileirar = AsyncMock()
            mock_abertura.return_value = "Oi Dr Carlos! Tudo bem?"

            # Executar
            result = await executor.executar(16)

            # Verificar
            assert result is True
            assert mock_abertura.call_count == 2  # Uma vez por destinatario
            assert mock_fila.enfileirar.call_count == 2

    @pytest.mark.asyncio
    async def test_executar_campanha_oferta_com_template(self, executor, campanha_oferta, destinatarios):
        """Testa execucao de campanha oferta com template."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.segmentacao_service") as mock_seg, \
             patch("app.services.campanhas.executor.fila_service") as mock_fila:

            # Setup mocks
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_oferta)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_segmento = AsyncMock(return_value=destinatarios)
            mock_fila.enfileirar = AsyncMock()

            # Executar
            result = await executor.executar(17)

            # Verificar
            assert result is True
            # Verificar que template foi formatado
            call_args = mock_fila.enfileirar.call_args_list[0]
            assert "Carlos" in call_args.kwargs["conteudo"]
            assert "Cardiologia" in call_args.kwargs["conteudo"]

    @pytest.mark.asyncio
    async def test_executar_campanha_nao_encontrada(self, executor):
        """Testa execucao quando campanha nao existe."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo:
            mock_repo.buscar_por_id = AsyncMock(return_value=None)

            result = await executor.executar(999)

            assert result is False

    @pytest.mark.asyncio
    async def test_executar_campanha_status_invalido(self, executor, campanha_discovery):
        """Testa execucao quando campanha tem status invalido."""
        campanha_discovery.status = StatusCampanha.CONCLUIDA

        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo:
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)

            result = await executor.executar(16)

            assert result is False

    @pytest.mark.asyncio
    async def test_executar_sem_destinatarios(self, executor, campanha_discovery):
        """Testa execucao quando nao ha destinatarios."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.segmentacao_service") as mock_seg:

            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_seg.buscar_segmento = AsyncMock(return_value=[])

            result = await executor.executar(16)

            # Deve retornar True mas marcar como concluida
            assert result is True
            # Deve ter chamado atualizar_status duas vezes (ativa, depois concluida)
            assert mock_repo.atualizar_status.call_count == 2


class TestGerarMensagem:
    """Testes do metodo _gerar_mensagem."""

    @pytest.mark.asyncio
    async def test_gerar_mensagem_discovery(self, executor, campanha_discovery):
        """Testa geracao de mensagem para discovery."""
        destinatario = {"id": "uuid-1", "primeiro_nome": "Carlos"}

        with patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura:
            mock_abertura.return_value = "Oi Dr Carlos! Sou a Julia da Revoluna"

            mensagem = await executor._gerar_mensagem(campanha_discovery, destinatario)

            assert mensagem == "Oi Dr Carlos! Sou a Julia da Revoluna"
            mock_abertura.assert_called_once_with("uuid-1", "Carlos")

    @pytest.mark.asyncio
    async def test_gerar_mensagem_oferta(self, executor, campanha_oferta):
        """Testa geracao de mensagem para oferta."""
        destinatario = {"id": "uuid-1", "primeiro_nome": "Carlos", "especialidade_nome": "Cardio"}

        mensagem = await executor._gerar_mensagem(campanha_oferta, destinatario)

        assert "Carlos" in mensagem
        assert "Cardio" in mensagem

    @pytest.mark.asyncio
    async def test_gerar_mensagem_reativacao_sem_corpo(self, executor, campanha_reativacao):
        """Testa geracao de mensagem para reativacao sem corpo definido."""
        destinatario = {"id": "uuid-1", "primeiro_nome": "Maria"}

        mensagem = await executor._gerar_mensagem(campanha_reativacao, destinatario)

        assert "Maria" in mensagem
        assert "Faz tempo" in mensagem

    @pytest.mark.asyncio
    async def test_gerar_mensagem_followup_sem_corpo(self, executor):
        """Testa geracao de mensagem para followup sem corpo."""
        campanha = CampanhaData(
            id=19,
            nome_template="Followup",
            tipo_campanha=TipoCampanha.FOLLOWUP,
            corpo=None,
            status=StatusCampanha.AGENDADA,
        )
        destinatario = {"id": "uuid-1", "primeiro_nome": "Pedro"}

        mensagem = await executor._gerar_mensagem(campanha, destinatario)

        assert "Pedro" in mensagem
        assert "Lembrei de vc" in mensagem


class TestFormatarTemplate:
    """Testes do metodo _formatar_template."""

    def test_formatar_template_simples(self, executor):
        """Testa formatacao de template simples."""
        template = "Oi Dr {nome}! Voce e {especialidade}?"

        resultado = executor._formatar_template(template, "Carlos", "cardiologista")

        assert resultado == "Oi Dr Carlos! Voce e cardiologista?"

    def test_formatar_template_chaves_duplas(self, executor):
        """Testa formatacao de template com chaves duplas."""
        template = "Oi Dr {{nome}}!"

        resultado = executor._formatar_template(template, "Maria", "")

        assert resultado == "Oi Dr Maria!"

    def test_formatar_template_sem_placeholders(self, executor):
        """Testa template sem placeholders."""
        template = "Mensagem fixa sem variaveis"

        resultado = executor._formatar_template(template, "Carlos", "cardio")

        assert resultado == "Mensagem fixa sem variaveis"

    def test_formatar_template_misto(self, executor):
        """Testa template com ambos formatos de placeholder."""
        template = "Oi {nome}, voce {{especialidade}}?"

        resultado = executor._formatar_template(template, "Ana", "anestesio")

        assert resultado == "Oi Ana, voce anestesio?"


class TestBuscarDestinatarios:
    """Testes do metodo _buscar_destinatarios."""

    @pytest.mark.asyncio
    async def test_buscar_com_filtros(self, executor, campanha_oferta, destinatarios):
        """Testa busca com filtros de audiencia."""
        with patch("app.services.campanhas.executor.segmentacao_service") as mock_seg:
            mock_seg.buscar_segmento = AsyncMock(return_value=destinatarios)

            result = await executor._buscar_destinatarios(campanha_oferta)

            assert len(result) == 2
            # Verificar que filtros foram passados
            call_args = mock_seg.buscar_segmento.call_args
            filtros = call_args[0][0]
            assert filtros["especialidade"] == "cardiologia"

    @pytest.mark.asyncio
    async def test_buscar_sem_filtros(self, executor, campanha_discovery, destinatarios):
        """Testa busca sem filtros especificos."""
        with patch("app.services.campanhas.executor.segmentacao_service") as mock_seg:
            mock_seg.buscar_segmento = AsyncMock(return_value=destinatarios)

            result = await executor._buscar_destinatarios(campanha_discovery)

            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_buscar_com_erro(self, executor, campanha_discovery):
        """Testa busca quando ocorre erro."""
        with patch("app.services.campanhas.executor.segmentacao_service") as mock_seg:
            mock_seg.buscar_segmento = AsyncMock(side_effect=Exception("DB Error"))

            result = await executor._buscar_destinatarios(campanha_discovery)

            assert result == []
