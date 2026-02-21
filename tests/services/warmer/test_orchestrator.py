"""Testes do Warming Orchestrator.

Valida que o orchestrator delega execução ao executor real,
gerencia transições de fase e coordena o ciclo de warmup.

Sprint 65: Testes para warming_started_at, warming_day, obter_status_pool com chips.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from datetime import datetime, timezone, timedelta

from app.services.warmer.orchestrator import (
    WarmingOrchestrator,
    FaseWarmup,
    CriteriosTransicao,
    CRITERIOS_FASE,
    SEQUENCIA_FASES,
)
from app.services.warmer.scheduler import AtividadeAgendada, TipoAtividade


CHIP_ID = "aaaaaaaa-1111-2222-3333-444444444444"


@pytest.fixture
def orchestrator():
    """Instância limpa do orchestrator."""
    return WarmingOrchestrator()


@pytest.fixture
def atividade_conversa():
    return AtividadeAgendada(
        id="act-001",
        chip_id=CHIP_ID,
        tipo=TipoAtividade.CONVERSA_PAR,
        horario=datetime.now(timezone.utc),
    )


@pytest.fixture
def atividade_sem_id():
    """Atividade sem ID (não precisa marcar no scheduler)."""
    return AtividadeAgendada(
        id=None,
        chip_id=CHIP_ID,
        tipo=TipoAtividade.MARCAR_LIDO,
        horario=datetime.now(timezone.utc),
    )


# ── executar_atividade (delegação ao executor) ─────────────────


class TestExecutarAtividade:
    """Testa que orchestrator delega ao executor real."""

    @patch("app.services.warmer.orchestrator.scheduler")
    @patch("app.services.warmer.orchestrator._executor_executar")
    async def test_delega_ao_executor_e_retorna_sucesso(
        self, mock_executor, mock_scheduler, orchestrator, atividade_conversa
    ):
        mock_executor.return_value = True
        mock_scheduler.marcar_executada = AsyncMock()

        result = await orchestrator.executar_atividade(atividade_conversa)

        assert result["success"] is True
        assert result["tipo"] == "conversa_par"
        mock_executor.assert_awaited_once_with(atividade_conversa)

    @patch("app.services.warmer.orchestrator.scheduler")
    @patch("app.services.warmer.orchestrator._executor_executar")
    async def test_delega_ao_executor_e_retorna_falha(
        self, mock_executor, mock_scheduler, orchestrator, atividade_conversa
    ):
        mock_executor.return_value = False
        mock_scheduler.marcar_executada = AsyncMock()

        result = await orchestrator.executar_atividade(atividade_conversa)

        assert result["success"] is False

    @patch("app.services.warmer.orchestrator.scheduler")
    @patch("app.services.warmer.orchestrator._executor_executar")
    async def test_marca_atividade_executada_no_scheduler(
        self, mock_executor, mock_scheduler, orchestrator, atividade_conversa
    ):
        mock_executor.return_value = True
        mock_scheduler.marcar_executada = AsyncMock()

        await orchestrator.executar_atividade(atividade_conversa)

        mock_scheduler.marcar_executada.assert_awaited_once_with(
            "act-001",
            True,
            {"success": True, "tipo": "conversa_par"},
        )

    @patch("app.services.warmer.orchestrator._executor_executar")
    async def test_nao_marca_scheduler_quando_sem_id(
        self, mock_executor, orchestrator, atividade_sem_id
    ):
        mock_executor.return_value = True

        result = await orchestrator.executar_atividade(atividade_sem_id)

        assert result["success"] is True
        # Sem ID, não deve chamar marcar_executada

    @patch("app.services.warmer.orchestrator._executor_executar")
    async def test_rejeita_chip_duplicado(self, mock_executor, orchestrator, atividade_conversa):
        # Simular chip já em processamento: criar e adquirir o lock
        orchestrator._chip_locks[CHIP_ID] = asyncio.Lock()
        await orchestrator._chip_locks[CHIP_ID].acquire()

        result = await orchestrator.executar_atividade(atividade_conversa)

        assert result["success"] is False
        assert "já em processamento" in result["error"]
        mock_executor.assert_not_awaited()

        # Limpar lock
        orchestrator._chip_locks[CHIP_ID].release()

    @patch("app.services.warmer.orchestrator.scheduler")
    @patch("app.services.warmer.orchestrator._executor_executar")
    async def test_libera_lock_apos_execucao(
        self, mock_executor, mock_scheduler, orchestrator, atividade_conversa
    ):
        mock_executor.return_value = True
        mock_scheduler.marcar_executada = AsyncMock()

        await orchestrator.executar_atividade(atividade_conversa)

        # Lock deve estar liberado após execução
        assert not orchestrator._chip_locks[CHIP_ID].locked()

    @patch("app.services.warmer.orchestrator.scheduler")
    @patch("app.services.warmer.orchestrator._executor_executar")
    async def test_libera_lock_mesmo_com_erro(
        self, mock_executor, mock_scheduler, orchestrator, atividade_conversa
    ):
        mock_executor.side_effect = RuntimeError("boom")
        mock_scheduler.marcar_executada = AsyncMock()

        with pytest.raises(RuntimeError):
            await orchestrator.executar_atividade(atividade_conversa)

        # Lock deve estar liberado mesmo após erro
        assert not orchestrator._chip_locks[CHIP_ID].locked()


# ── iniciar_chip ───────────────────────────────────────────────


class TestIniciarChip:
    @patch("app.services.warmer.orchestrator.scheduler")
    @patch("app.services.warmer.orchestrator.calcular_trust_score")
    @patch("app.services.warmer.orchestrator.supabase")
    async def test_inicia_warmup_para_chip_conectado(
        self, mock_sb, mock_trust, mock_scheduler, orchestrator
    ):
        # Mock busca do chip
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": CHIP_ID,
                "telefone": "5511999990001",
                "status": "connected",
                "fase_warmup": "repouso",
            }
        )
        # Mock update
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
        # Mock insert (transição)
        mock_sb.table.return_value.insert.return_value.execute.return_value = None

        mock_trust.return_value = {"score": 42, "level": "amarelo"}
        mock_scheduler.planejar_dia = AsyncMock(return_value=["a1", "a2", "a3"])
        mock_scheduler.salvar_agenda = AsyncMock()

        result = await orchestrator.iniciar_chip(CHIP_ID)

        assert result["success"] is True
        assert result["fase"] == "setup"
        assert result["trust_score"] == 42
        assert result["atividades_agendadas"] == 3

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_rejeita_chip_nao_conectado(self, mock_sb, orchestrator):
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": CHIP_ID,
                "telefone": "5511999990001",
                "status": "disconnected",
                "fase_warmup": "repouso",
            }
        )

        result = await orchestrator.iniciar_chip(CHIP_ID)

        assert result["success"] is False
        assert "não conectado" in result["error"]

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_retorna_fase_se_ja_em_warmup(self, mock_sb, orchestrator):
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": CHIP_ID,
                "telefone": "5511999990001",
                "status": "connected",
                "fase_warmup": "expansao",
            }
        )

        result = await orchestrator.iniciar_chip(CHIP_ID)

        assert result["success"] is True
        assert result["fase"] == "expansao"
        assert result["message"] == "Chip já em warmup"

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_chip_nao_encontrado(self, mock_sb, orchestrator):
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = await orchestrator.iniciar_chip(CHIP_ID)

        assert result["success"] is False
        assert "não encontrado" in result["error"]


# ── pausar_chip ────────────────────────────────────────────────


class TestPausarChip:
    @patch("app.services.warmer.orchestrator.supabase")
    @patch("app.services.warmer.orchestrator.scheduler")
    async def test_pausa_cancela_atividades_e_volta_repouso(
        self, mock_scheduler, mock_sb, orchestrator
    ):
        mock_scheduler.cancelar_atividades = AsyncMock(return_value=5)
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None

        result = await orchestrator.pausar_chip(CHIP_ID, "teste_pausa")

        assert result["success"] is True
        assert result["atividades_canceladas"] == 5
        mock_scheduler.cancelar_atividades.assert_awaited_once_with(CHIP_ID, "teste_pausa")


# ── verificar_transicao ───────────────────────────────────────


class TestVerificarTransicao:
    @patch("app.services.warmer.orchestrator.supabase")
    async def test_transiciona_quando_criterios_atendidos(self, mock_sb, orchestrator):
        created_at = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "fase_warmup": "setup",
                "created_at": created_at,
                "msgs_enviadas_total": 30,
                "msgs_recebidas_total": 15,
                "taxa_resposta": 0.5,
                "trust_score": 55,
                "conversas_bidirecionais": 6,
                "grupos_count": 0,
                "erros_ultimas_24h": 0,
            }
        )

        nova_fase = await orchestrator.verificar_transicao(CHIP_ID)

        assert nova_fase == "primeiros_contatos"

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_nao_transiciona_trust_insuficiente(self, mock_sb, orchestrator):
        created_at = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "fase_warmup": "setup",
                "created_at": created_at,
                "msgs_enviadas_total": 30,
                "msgs_recebidas_total": 15,
                "taxa_resposta": 0.5,
                "trust_score": 35,  # abaixo do mínimo 50
                "conversas_bidirecionais": 6,
                "grupos_count": 0,
                "erros_ultimas_24h": 0,
            }
        )

        nova_fase = await orchestrator.verificar_transicao(CHIP_ID)

        assert nova_fase is None

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_nao_transiciona_dias_insuficientes(self, mock_sb, orchestrator):
        created_at = datetime.now(timezone.utc).isoformat()  # criado hoje
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "fase_warmup": "setup",
                "created_at": created_at,
                "msgs_enviadas_total": 100,
                "msgs_recebidas_total": 50,
                "taxa_resposta": 0.9,
                "trust_score": 90,
                "conversas_bidirecionais": 20,
                "grupos_count": 5,
                "erros_ultimas_24h": 0,
            }
        )

        nova_fase = await orchestrator.verificar_transicao(CHIP_ID)

        # Precisa de pelo menos 3 dias para primeiros_contatos
        assert nova_fase is None

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_operacao_nao_tem_transicao(self, mock_sb, orchestrator):
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"fase_warmup": "operacao"}
        )

        nova_fase = await orchestrator.verificar_transicao(CHIP_ID)

        assert nova_fase is None

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_chip_nao_encontrado_retorna_none(self, mock_sb, orchestrator):
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        nova_fase = await orchestrator.verificar_transicao(CHIP_ID)

        assert nova_fase is None

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_nao_transiciona_com_erros_excessivos(self, mock_sb, orchestrator):
        created_at = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "fase_warmup": "setup",
                "created_at": created_at,
                "msgs_enviadas_total": 30,
                "msgs_recebidas_total": 15,
                "taxa_resposta": 0.5,
                "trust_score": 55,
                "conversas_bidirecionais": 6,
                "grupos_count": 0,
                "erros_ultimas_24h": 10,  # acima do max 5
            }
        )

        nova_fase = await orchestrator.verificar_transicao(CHIP_ID)

        assert nova_fase is None


# ── executar_transicao ─────────────────────────────────────────


class TestExecutarTransicao:
    @patch("app.services.warmer.orchestrator.scheduler")
    @patch("app.services.warmer.orchestrator.calcular_trust_score")
    @patch("app.services.warmer.orchestrator.supabase")
    async def test_executa_transicao_e_replaneja(
        self, mock_sb, mock_trust, mock_scheduler, orchestrator
    ):
        # Mock busca fase atual
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"fase_warmup": "setup"}
        )
        # Mock update e insert
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
        mock_sb.table.return_value.insert.return_value.execute.return_value = None

        mock_trust.return_value = {"score": 55}
        mock_scheduler.cancelar_atividades = AsyncMock()
        mock_scheduler.planejar_dia = AsyncMock(return_value=["a1", "a2"])
        mock_scheduler.salvar_agenda = AsyncMock()

        result = await orchestrator.executar_transicao(
            CHIP_ID, "primeiros_contatos", automatico=True
        )

        assert result["success"] is True
        assert result["fase_anterior"] == "setup"
        assert result["fase_nova"] == "primeiros_contatos"
        assert result["trust_score"] == 55
        mock_scheduler.cancelar_atividades.assert_awaited_once()


# ── ciclo_warmup ───────────────────────────────────────────────


class TestCicloWarmup:
    @patch("app.services.warmer.orchestrator.calcular_trust_score")
    @patch("app.services.warmer.orchestrator.supabase")
    @patch("app.services.warmer.orchestrator.scheduler")
    @patch("app.services.warmer.orchestrator._executor_executar")
    async def test_ciclo_executa_atividades_e_verifica_transicoes(
        self, mock_executor, mock_scheduler, mock_sb, mock_trust, orchestrator
    ):
        # Mock _garantir_planejamento_diario (chips ativos sem atividades)
        mock_sb.table.return_value.select.return_value.neq.return_value.execute.return_value = (
            MagicMock(data=[])
        )
        # Atividades pendentes
        atividade = AtividadeAgendada(
            id="act-100",
            chip_id=CHIP_ID,
            tipo=TipoAtividade.CONVERSA_PAR,
        )
        mock_scheduler.obter_proximas_atividades = AsyncMock(return_value=[atividade])
        mock_scheduler.obter_estatisticas = AsyncMock(return_value={"total": 5})
        mock_scheduler.marcar_executada = AsyncMock()

        mock_executor.return_value = True

        # Chips para transição (nenhum, simplifica teste)
        mock_sb.table.return_value.select.return_value.neq.return_value.neq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        await orchestrator.ciclo_warmup()

        mock_executor.assert_awaited_once()
        # Lock deve estar liberado após ciclo completar
        assert not orchestrator._ciclo_lock.locked()

    async def test_ciclo_nao_reentra(self, orchestrator):
        # Simular ciclo já em andamento adquirindo o lock
        await orchestrator._ciclo_lock.acquire()

        # Não deve lançar exceção, apenas retorna (lock já adquirido)
        await orchestrator.ciclo_warmup()

        # Lock ainda deve estar adquirido (ciclo não executou)
        assert orchestrator._ciclo_lock.locked()

        # Limpar
        orchestrator._ciclo_lock.release()


# ── obter_status_pool ──────────────────────────────────────────


class TestObterStatusPool:
    @patch("app.services.warmer.orchestrator.supabase")
    async def test_calcula_estatisticas_do_pool(self, mock_sb, orchestrator):
        mock_sb.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[
                {"fase_warmup": "setup", "trust_score": 40, "status": "connected"},
                {"fase_warmup": "expansao", "trust_score": 60, "status": "connected"},
                {"fase_warmup": "operacao", "trust_score": 80, "status": "connected"},
            ]
        )

        stats = await orchestrator.obter_status_pool()

        assert stats["total"] == 3
        assert stats["por_fase"]["setup"] == 1
        assert stats["por_fase"]["expansao"] == 1
        assert stats["por_fase"]["operacao"] == 1
        assert stats["trust_medio"] == 60.0
        assert stats["prontos_operacao"] == 1  # operacao com trust >= 75

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_pool_vazio(self, mock_sb, orchestrator):
        mock_sb.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])

        stats = await orchestrator.obter_status_pool()

        assert stats["total"] == 0
        assert stats["trust_medio"] == 0
        assert stats["prontos_operacao"] == 0


# ── Constantes e estrutura ─────────────────────────────────────


class TestConstantes:
    def test_sequencia_fases_completa(self):
        assert len(SEQUENCIA_FASES) == 7
        assert SEQUENCIA_FASES[0] == FaseWarmup.REPOUSO
        assert SEQUENCIA_FASES[-1] == FaseWarmup.OPERACAO

    def test_criterios_existem_para_cada_fase_exceto_repouso(self):
        for fase in SEQUENCIA_FASES[1:]:
            assert fase in CRITERIOS_FASE

    def test_criterios_progressivos(self):
        """Trust score mínimo deve aumentar a cada fase."""
        trust_anterior = 0
        for fase in SEQUENCIA_FASES[1:]:
            criterio = CRITERIOS_FASE[fase]
            assert criterio.trust_score_min >= trust_anterior
            trust_anterior = criterio.trust_score_min

    def test_dias_minimos_progressivos(self):
        """Dias mínimos devem aumentar a cada fase."""
        dias_anterior = 0
        for fase in SEQUENCIA_FASES[1:]:
            criterio = CRITERIOS_FASE[fase]
            assert criterio.dias_minimos >= dias_anterior
            dias_anterior = criterio.dias_minimos

    def test_grupos_min_zero_em_todas_as_fases(self):
        """Sprint 65: Todas as fases devem ter grupos_min=0 (stub não implementado)."""
        for fase, criterio in CRITERIOS_FASE.items():
            assert criterio.grupos_min == 0, f"Fase {fase} tem grupos_min={criterio.grupos_min}"


# ── verificar_transicao — Sprint 65 (warming_started_at) ────


class TestVerificarTransicaoSprint65:
    """Sprint 65: Testa que warming_started_at é usado para calcular idade."""

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_usa_warming_started_at_quando_disponivel(self, mock_sb, orchestrator):
        """warming_started_at deve ter prioridade sobre created_at."""
        # warming_started_at = 5 dias atrás (deve transicionar)
        warming_started = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        # created_at = hoje (não deveria transicionar se usado)
        created_at = datetime.now(timezone.utc).isoformat()

        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "fase_warmup": "setup",
                "warming_started_at": warming_started,
                "created_at": created_at,
                "msgs_enviadas_total": 30,
                "msgs_recebidas_total": 15,
                "taxa_resposta": 0.5,
                "trust_score": 55,
                "conversas_bidirecionais": 6,
                "grupos_count": 0,
                "erros_ultimas_24h": 0,
            }
        )

        nova_fase = await orchestrator.verificar_transicao(CHIP_ID)

        # Deve transicionar porque warming_started_at indica 5 dias
        assert nova_fase == "primeiros_contatos"

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_fallback_para_created_at_quando_sem_warming_started(
        self, mock_sb, orchestrator
    ):
        """Sem warming_started_at, deve usar created_at como fallback."""
        created_at = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "fase_warmup": "setup",
                "warming_started_at": None,
                "fase_iniciada_em": None,
                "created_at": created_at,
                "msgs_enviadas_total": 30,
                "msgs_recebidas_total": 15,
                "taxa_resposta": 0.5,
                "trust_score": 55,
                "conversas_bidirecionais": 6,
                "grupos_count": 0,
                "erros_ultimas_24h": 0,
            }
        )

        nova_fase = await orchestrator.verificar_transicao(CHIP_ID)

        assert nova_fase == "primeiros_contatos"

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_taxa_resposta_string_convertida(self, mock_sb, orchestrator):
        """Sprint 65: taxa_resposta pode vir como string do banco."""
        warming_started = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "fase_warmup": "setup",
                "warming_started_at": warming_started,
                "created_at": warming_started,
                "msgs_enviadas_total": 30,
                "msgs_recebidas_total": 15,
                "taxa_resposta": "0.5",  # String ao invés de float
                "trust_score": 55,
                "conversas_bidirecionais": 6,
                "grupos_count": 0,
                "erros_ultimas_24h": 0,
            }
        )

        nova_fase = await orchestrator.verificar_transicao(CHIP_ID)

        assert nova_fase == "primeiros_contatos"


# ── _atualizar_warming_days (Sprint 65) ──────────────────────


class TestAtualizarWarmingDays:
    """Sprint 65: Testa cálculo e persistência de warming_day."""

    @patch("app.services.warmer.orchestrator.agora_brasilia")
    @patch("app.services.warmer.orchestrator.supabase")
    async def test_calcula_warming_day_corretamente(self, mock_sb, mock_agora, orchestrator):
        agora = datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc)
        mock_agora.return_value = agora

        warming_started = (agora - timedelta(days=7)).isoformat()
        mock_sb.table.return_value.select.return_value.in_.return_value.not_.is_.return_value.execute.return_value = MagicMock(
            data=[{"id": CHIP_ID, "warming_started_at": warming_started}]
        )
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None

        await orchestrator._atualizar_warming_days()

        # Verificar que update foi chamado com warming_day=7
        update_call = mock_sb.table.return_value.update.call_args[0][0]
        assert update_call["warming_day"] == 7

    @patch("app.services.warmer.orchestrator.agora_brasilia")
    @patch("app.services.warmer.orchestrator.supabase")
    async def test_sem_chips_nao_faz_update(self, mock_sb, mock_agora, orchestrator):
        mock_agora.return_value = datetime.now(timezone.utc)
        mock_sb.table.return_value.select.return_value.in_.return_value.not_.is_.return_value.execute.return_value = MagicMock(
            data=[]
        )

        await orchestrator._atualizar_warming_days()

        mock_sb.table.return_value.update.assert_not_called()


# ── obter_status_pool — Sprint 65 (com chips array) ─────────


class TestObterStatusPoolSprint65:
    """Sprint 65: Verifica que obter_status_pool retorna chips array com detalhes."""

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_retorna_chips_com_detalhes(self, mock_sb, orchestrator):
        mock_sb.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "telefone": "5511999990001",
                    "fase_warmup": "expansao",
                    "trust_score": 60,
                    "trust_level": "amarelo",
                    "status": "warming",
                    "warming_day": 10,
                    "msgs_enviadas_hoje": 5,
                    "evolution_connected": True,
                    "provider": "evolution",
                },
            ]
        )

        stats = await orchestrator.obter_status_pool()

        assert "chips" in stats
        assert len(stats["chips"]) == 1
        chip = stats["chips"][0]
        assert chip["telefone_masked"] == "0001"
        assert chip["fase"] == "expansao"
        assert chip["warming_day"] == 10
        assert chip["trust"] == 60
        assert chip["provider"] == "evolution"

    @patch("app.services.warmer.orchestrator.supabase")
    async def test_por_status_calculado(self, mock_sb, orchestrator):
        mock_sb.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "telefone": "5511999990001",
                    "fase_warmup": "setup",
                    "trust_score": 40,
                    "trust_level": "vermelho",
                    "status": "warming",
                    "warming_day": 1,
                    "msgs_enviadas_hoje": 0,
                    "evolution_connected": True,
                    "provider": "evolution",
                },
                {
                    "telefone": "5511999990002",
                    "fase_warmup": "operacao",
                    "trust_score": 80,
                    "trust_level": "verde",
                    "status": "active",
                    "warming_day": 30,
                    "msgs_enviadas_hoje": 3,
                    "evolution_connected": True,
                    "provider": "z-api",
                },
            ]
        )

        stats = await orchestrator.obter_status_pool()

        assert stats["por_status"]["warming"] == 1
        assert stats["por_status"]["active"] == 1
        assert stats["prontos_operacao"] == 1
