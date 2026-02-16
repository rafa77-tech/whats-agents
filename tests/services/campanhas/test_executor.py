"""Testes do executor de campanhas.

Sprint 35 - Epic 04
Sprint 57 - Anti-spam tests
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.campanhas.executor import CampanhaExecutor, MAX_UNANSWERED_OUTBOUND
from app.services.campanhas.types import (
    AudienceFilters,
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)
from app.services.campaign_cooldown import CooldownResult


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
             patch("app.services.campanhas.executor.supabase") as mock_supabase, \
             patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura, \
             patch("app.services.campanhas.executor.check_campaign_cooldown") as mock_cooldown:

            # Setup mocks
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=destinatarios)
            mock_fila.enfileirar = AsyncMock()
            mock_abertura.return_value = "Oi Dr Carlos! Tudo bem?"
            mock_cooldown.return_value = CooldownResult(is_blocked=False)
            executor._excedeu_limite_sem_resposta = AsyncMock(return_value=False)
            # Mock deduplicação (Sprint 44)
            mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = []

            # Executar
            result = await executor.executar(16)

            # Verificar
            assert result is True
            assert mock_abertura.call_count == 2  # Uma vez por destinatario
            assert mock_fila.enfileirar.call_count == 2
            # Sprint 57: campanha deve ir para CONCLUIDA
            status_calls = [c.args for c in mock_repo.atualizar_status.call_args_list]
            assert status_calls[-1] == (16, StatusCampanha.CONCLUIDA)

    @pytest.mark.asyncio
    async def test_executar_campanha_oferta_com_template(self, executor, campanha_oferta, destinatarios):
        """Testa execucao de campanha oferta com template."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.segmentacao_service") as mock_seg, \
             patch("app.services.campanhas.executor.fila_service") as mock_fila, \
             patch("app.services.campanhas.executor.supabase") as mock_supabase, \
             patch("app.services.campanhas.executor.check_campaign_cooldown") as mock_cooldown:

            # Setup mocks
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_oferta)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=destinatarios)
            mock_fila.enfileirar = AsyncMock()
            mock_cooldown.return_value = CooldownResult(is_blocked=False)
            executor._excedeu_limite_sem_resposta = AsyncMock(return_value=False)
            # Mock deduplicação (Sprint 44)
            mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = []

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
             patch("app.services.campanhas.executor.segmentacao_service") as mock_seg, \
             patch("app.services.campanhas.executor.supabase") as mock_supabase:

            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=[])
            # Mock deduplicação (Sprint 44) - não afeta pois lista vazia
            mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = []

            result = await executor.executar(16)

            # Deve retornar True mas marcar como concluida
            assert result is True
            # Deve ter chamado atualizar_status duas vezes (ativa, depois concluida)
            assert mock_repo.atualizar_status.call_count == 2


    @pytest.mark.asyncio
    async def test_executar_deduplica_clientes_ja_enviados(self, executor, campanha_discovery, destinatarios):
        """Testa que clientes que já receberam a campanha são ignorados (Sprint 44)."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.segmentacao_service") as mock_seg, \
             patch("app.services.campanhas.executor.fila_service") as mock_fila, \
             patch("app.services.campanhas.executor.supabase") as mock_supabase, \
             patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura, \
             patch("app.services.campanhas.executor.check_campaign_cooldown") as mock_cooldown:

            # Setup mocks
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=destinatarios)
            mock_fila.enfileirar = AsyncMock()
            mock_abertura.return_value = "Oi! Tudo bem?"
            mock_cooldown.return_value = CooldownResult(is_blocked=False)
            executor._excedeu_limite_sem_resposta = AsyncMock(return_value=False)
            # Mock: uuid-1 já recebeu essa campanha antes
            mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = [
                {"cliente_id": "uuid-1"}
            ]

            # Executar
            result = await executor.executar(16)

            # Verificar: apenas 1 destinatário (uuid-2) deve receber
            assert result is True
            assert mock_fila.enfileirar.call_count == 1
            # Verificar que foi o uuid-2 que recebeu
            call_args = mock_fila.enfileirar.call_args
            assert call_args.kwargs["cliente_id"] == "uuid-2"


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
            mock_abertura.assert_called_once_with("uuid-1", "Carlos", soft=True)

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

    @pytest.mark.asyncio
    async def test_gerar_mensagem_oferta_sem_corpo_retorna_none(self, executor):
        """Testa que oferta sem corpo retorna None (corpo é obrigatório)."""
        campanha = CampanhaData(
            id=20,
            nome_template="Oferta Sem Corpo",
            tipo_campanha=TipoCampanha.OFERTA,
            corpo=None,
            status=StatusCampanha.AGENDADA,
        )
        destinatario = {"id": "uuid-1", "primeiro_nome": "Carlos", "especialidade_nome": "Cardio"}

        mensagem = await executor._gerar_mensagem(campanha, destinatario)

        assert mensagem is None

    @pytest.mark.asyncio
    async def test_gerar_mensagem_oferta_plantao_sem_corpo_retorna_none(self, executor):
        """Testa que oferta_plantao sem corpo retorna None (corpo é obrigatório)."""
        campanha = CampanhaData(
            id=21,
            nome_template="Oferta Plantao Sem Corpo",
            tipo_campanha=TipoCampanha.OFERTA_PLANTAO,
            corpo=None,
            status=StatusCampanha.AGENDADA,
        )
        destinatario = {"id": "uuid-1", "primeiro_nome": "Maria", "especialidade_nome": "Anestesio"}

        mensagem = await executor._gerar_mensagem(campanha, destinatario)

        assert mensagem is None

    @pytest.mark.asyncio
    async def test_gerar_mensagem_oferta_plantao_com_corpo(self, executor):
        """Testa oferta_plantao com corpo usa o template."""
        campanha = CampanhaData(
            id=22,
            nome_template="Oferta Plantao Com Corpo",
            tipo_campanha=TipoCampanha.OFERTA_PLANTAO,
            corpo="Oi Dr {nome}! Temos uma vaga de {especialidade}",
            status=StatusCampanha.AGENDADA,
        )
        destinatario = {"id": "uuid-1", "primeiro_nome": "Ana", "especialidade_nome": "Pediatria"}

        mensagem = await executor._gerar_mensagem(campanha, destinatario)

        assert mensagem is not None
        assert "Ana" in mensagem
        assert "Pediatria" in mensagem


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
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=destinatarios)

            result = await executor._buscar_destinatarios(campanha_oferta)

            assert len(result) == 2
            # Verificar que filtros foram passados (Sprint 44: usa kwargs)
            call_args = mock_seg.buscar_alvos_campanha.call_args
            filtros = call_args.kwargs.get("filtros", {})
            assert filtros.get("especialidade") == "cardiologia"

    @pytest.mark.asyncio
    async def test_buscar_sem_filtros(self, executor, campanha_discovery, destinatarios):
        """Testa busca sem filtros especificos."""
        with patch("app.services.campanhas.executor.segmentacao_service") as mock_seg:
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=destinatarios)

            result = await executor._buscar_destinatarios(campanha_discovery)

            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_buscar_com_erro(self, executor, campanha_discovery):
        """Testa busca quando ocorre erro."""
        with patch("app.services.campanhas.executor.segmentacao_service") as mock_seg:
            mock_seg.buscar_alvos_campanha = AsyncMock(side_effect=Exception("DB Error"))

            result = await executor._buscar_destinatarios(campanha_discovery)

            assert result == []


class TestAntiSpam:
    """Testes anti-spam (Sprint 57 - #109, #110, #111)."""

    @pytest.fixture
    def executor(self):
        return CampanhaExecutor()

    @pytest.fixture
    def campanha_agendada(self):
        return CampanhaData(
            id=100,
            nome_template="Test Anti-Spam",
            tipo_campanha=TipoCampanha.DISCOVERY,
            corpo=None,
            status=StatusCampanha.AGENDADA,
            audience_filters=AudienceFilters(quantidade_alvo=3),
        )

    @pytest.fixture
    def tres_destinatarios(self):
        return [
            {"id": "uuid-a", "primeiro_nome": "Ana", "especialidade_nome": "Clinica"},
            {"id": "uuid-b", "primeiro_nome": "Bruno", "especialidade_nome": "Cardio"},
            {"id": "uuid-c", "primeiro_nome": "Carlos", "especialidade_nome": "Orto"},
        ]

    @pytest.mark.asyncio
    async def test_campanha_ativa_nao_pode_executar(self, executor):
        """#111: Campanha com status ATIVA nao pode ser executada novamente."""
        campanha = CampanhaData(
            id=100,
            nome_template="Test",
            tipo_campanha=TipoCampanha.DISCOVERY,
            corpo=None,
            status=StatusCampanha.ATIVA,
            audience_filters=AudienceFilters(),
        )

        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo:
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            result = await executor.executar(100)

            assert result is False
            # Nao deve tentar mudar status
            mock_repo.atualizar_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_cooldown_bloqueia_destinatario(
        self, executor, campanha_agendada, tres_destinatarios
    ):
        """#109: Destinatario em cooldown deve ser ignorado."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.segmentacao_service") as mock_seg, \
             patch("app.services.campanhas.executor.fila_service") as mock_fila, \
             patch("app.services.campanhas.executor.supabase") as mock_supabase, \
             patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura, \
             patch("app.services.campanhas.executor.check_campaign_cooldown") as mock_cooldown:

            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_agendada)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=tres_destinatarios)
            mock_fila.enfileirar = AsyncMock()
            mock_abertura.return_value = "Oi!"
            executor._excedeu_limite_sem_resposta = AsyncMock(return_value=False)
            mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = []

            # uuid-a e uuid-c em cooldown, uuid-b ok
            async def cooldown_side_effect(cliente_id, campaign_id):
                if cliente_id in ("uuid-a", "uuid-c"):
                    return CooldownResult(
                        is_blocked=True,
                        reason="different_campaign_recent",
                    )
                return CooldownResult(is_blocked=False)

            mock_cooldown.side_effect = cooldown_side_effect

            result = await executor.executar(100)

            assert result is True
            # Apenas uuid-b deve receber
            assert mock_fila.enfileirar.call_count == 1
            call_args = mock_fila.enfileirar.call_args
            assert call_args.kwargs["cliente_id"] == "uuid-b"

    @pytest.mark.asyncio
    async def test_limite_sem_resposta_bloqueia_destinatario(
        self, executor, campanha_agendada, tres_destinatarios
    ):
        """#110: Destinatario com muitos outbound sem resposta deve ser ignorado."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.segmentacao_service") as mock_seg, \
             patch("app.services.campanhas.executor.fila_service") as mock_fila, \
             patch("app.services.campanhas.executor.supabase") as mock_supabase, \
             patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura, \
             patch("app.services.campanhas.executor.check_campaign_cooldown") as mock_cooldown:

            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_agendada)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=tres_destinatarios)
            mock_fila.enfileirar = AsyncMock()
            mock_abertura.return_value = "Oi!"
            mock_cooldown.return_value = CooldownResult(is_blocked=False)
            mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = []

            # uuid-b excedeu limite sem resposta
            async def unanswered_side_effect(cliente_id):
                return cliente_id == "uuid-b"

            executor._excedeu_limite_sem_resposta = AsyncMock(side_effect=unanswered_side_effect)

            result = await executor.executar(100)

            assert result is True
            # uuid-a e uuid-c devem receber, uuid-b nao
            assert mock_fila.enfileirar.call_count == 2
            clientes_enviados = [
                c.kwargs["cliente_id"]
                for c in mock_fila.enfileirar.call_args_list
            ]
            assert "uuid-a" in clientes_enviados
            assert "uuid-c" in clientes_enviados
            assert "uuid-b" not in clientes_enviados

    @pytest.mark.asyncio
    async def test_campanha_conclui_apos_execucao(
        self, executor, campanha_agendada, tres_destinatarios
    ):
        """#111: Campanha deve ir para CONCLUIDA apos processar todos os envios."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.segmentacao_service") as mock_seg, \
             patch("app.services.campanhas.executor.fila_service") as mock_fila, \
             patch("app.services.campanhas.executor.supabase") as mock_supabase, \
             patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura, \
             patch("app.services.campanhas.executor.check_campaign_cooldown") as mock_cooldown:

            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_agendada)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=tres_destinatarios)
            mock_fila.enfileirar = AsyncMock()
            mock_abertura.return_value = "Oi!"
            mock_cooldown.return_value = CooldownResult(is_blocked=False)
            executor._excedeu_limite_sem_resposta = AsyncMock(return_value=False)
            mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = []

            await executor.executar(100)

            # Verificar transicoes de status: AGENDADA -> ATIVA -> CONCLUIDA
            status_calls = mock_repo.atualizar_status.call_args_list
            assert len(status_calls) == 2
            assert status_calls[0].args == (100, StatusCampanha.ATIVA)
            assert status_calls[1].args == (100, StatusCampanha.CONCLUIDA)

    @pytest.mark.asyncio
    async def test_todos_bloqueados_ainda_conclui_campanha(
        self, executor, campanha_agendada, tres_destinatarios
    ):
        """Campanha deve concluir mesmo se todos destinatarios foram filtrados."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.segmentacao_service") as mock_seg, \
             patch("app.services.campanhas.executor.fila_service") as mock_fila, \
             patch("app.services.campanhas.executor.supabase") as mock_supabase, \
             patch("app.services.campanhas.executor.check_campaign_cooldown") as mock_cooldown:

            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_agendada)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=tres_destinatarios)
            mock_fila.enfileirar = AsyncMock()
            # Todos em cooldown
            mock_cooldown.return_value = CooldownResult(
                is_blocked=True, reason="different_campaign_recent"
            )
            mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = []

            result = await executor.executar(100)

            assert result is True
            # Nenhum envio
            mock_fila.enfileirar.assert_not_called()
            mock_repo.incrementar_enviados.assert_called_once_with(100, 0)
            # Campanha deve concluir mesmo assim
            last_status = mock_repo.atualizar_status.call_args_list[-1]
            assert last_status.args == (100, StatusCampanha.CONCLUIDA)


class TestExcedeuLimiteSemResposta:
    """Testes do metodo _excedeu_limite_sem_resposta."""

    @pytest.fixture
    def executor(self):
        return CampanhaExecutor()

    @pytest.mark.asyncio
    async def test_medico_com_poucas_campanhas_nao_bloqueado(self, executor):
        """Medico com menos de MAX_UNANSWERED_OUTBOUND campanhas nao e bloqueado."""
        with patch("app.services.campanhas.executor.supabase") as mock_supabase:
            # 1 campanha < MAX_UNANSWERED_OUTBOUND (2)
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value.eq.return_value.execute.return_value.count = 1

            result = await executor._excedeu_limite_sem_resposta("uuid-1")

            assert result is False

    @pytest.mark.asyncio
    async def test_medico_com_resposta_nao_bloqueado(self, executor):
        """Medico com campanhas mas que respondeu nao e bloqueado."""
        with patch("app.services.campanhas.executor.supabase") as mock_supabase:
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table

            # Primeira chamada: campaign_contact_history (3 campanhas)
            call_count = {"n": 0}
            def select_side_effect(*args, **kwargs):
                call_count["n"] += 1
                mock_chain = MagicMock()
                if call_count["n"] <= 1:
                    # campaign_contact_history count
                    mock_chain.eq.return_value.execute.return_value.count = 3
                else:
                    # interacoes count - tem resposta
                    mock_chain.eq.return_value.eq.return_value.limit.return_value.execute.return_value.count = 2
                return mock_chain

            mock_table.select.side_effect = select_side_effect

            result = await executor._excedeu_limite_sem_resposta("uuid-1")

            assert result is False

    @pytest.mark.asyncio
    async def test_medico_sem_resposta_bloqueado(self, executor):
        """Medico com campanhas e sem resposta e bloqueado."""
        with patch("app.services.campanhas.executor.supabase") as mock_supabase:
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table

            call_count = {"n": 0}
            def select_side_effect(*args, **kwargs):
                call_count["n"] += 1
                mock_chain = MagicMock()
                if call_count["n"] <= 1:
                    # campaign_contact_history count - 3 campanhas
                    mock_chain.eq.return_value.execute.return_value.count = 3
                else:
                    # interacoes count - sem resposta
                    mock_chain.eq.return_value.eq.return_value.limit.return_value.execute.return_value.count = 0
                return mock_chain

            mock_table.select.side_effect = select_side_effect

            result = await executor._excedeu_limite_sem_resposta("uuid-1")

            assert result is True

    @pytest.mark.asyncio
    async def test_erro_permite_envio(self, executor):
        """Em caso de erro, permite envio (fail-open)."""
        with patch("app.services.campanhas.executor.supabase") as mock_supabase:
            mock_supabase.table.side_effect = Exception("DB Error")

            result = await executor._excedeu_limite_sem_resposta("uuid-1")

            assert result is False
