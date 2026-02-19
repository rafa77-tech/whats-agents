"""
Testes do GruposWorker.

Sprint 63 - Escalabilidade: estágios paralelos, semáforos por tipo, guard de ciclo.
"""

import asyncio

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

from app.workers.grupos_worker import (
    GruposWorker,
    processar_ciclo_grupos,
    obter_status_worker,
    _ciclo_lock,
    _semaforo_para_estagio,
    BUDGET_LLM,
    BUDGET_API_EXTERNA,
    BUDGET_DB,
    _ESTAGIOS_LLM,
    _ESTAGIOS_API_EXTERNA,
    _ESTAGIOS_DB,
)
from app.services.grupos.fila import EstagioPipeline


# =============================================================================
# Testes de Budget e Semáforos
# =============================================================================


class TestBudgetSemaforos:
    """Testes dos budgets de concorrência por tipo."""

    def test_budget_llm_menor_que_db(self):
        """LLM deve ter budget menor que DB (rate limit Anthropic)."""
        assert BUDGET_LLM < BUDGET_DB

    def test_budget_api_externa_intermediario(self):
        """API externa deve ter budget intermediário."""
        assert BUDGET_LLM < BUDGET_API_EXTERNA <= BUDGET_DB

    def test_estagios_llm_corretos(self):
        """Classificação e extração usam LLM."""
        assert EstagioPipeline.CLASSIFICACAO in _ESTAGIOS_LLM
        assert EstagioPipeline.EXTRACAO in _ESTAGIOS_LLM

    def test_estagios_api_externa_corretos(self):
        """Normalização usa APIs externas."""
        assert EstagioPipeline.NORMALIZACAO in _ESTAGIOS_API_EXTERNA

    def test_estagios_db_corretos(self):
        """Deduplicação e importação são apenas banco."""
        assert EstagioPipeline.DEDUPLICACAO in _ESTAGIOS_DB
        assert EstagioPipeline.IMPORTACAO in _ESTAGIOS_DB
        assert EstagioPipeline.PENDENTE in _ESTAGIOS_DB

    def test_semaforo_para_estagio_llm(self):
        """Deve retornar semáforo LLM para estágios LLM."""
        semaforos = {
            "llm": asyncio.Semaphore(BUDGET_LLM),
            "api_externa": asyncio.Semaphore(BUDGET_API_EXTERNA),
            "db": asyncio.Semaphore(BUDGET_DB),
        }
        sem = _semaforo_para_estagio(EstagioPipeline.CLASSIFICACAO, semaforos)
        assert sem is semaforos["llm"]

    def test_semaforo_para_estagio_api(self):
        """Deve retornar semáforo API para normalização."""
        semaforos = {
            "llm": asyncio.Semaphore(BUDGET_LLM),
            "api_externa": asyncio.Semaphore(BUDGET_API_EXTERNA),
            "db": asyncio.Semaphore(BUDGET_DB),
        }
        sem = _semaforo_para_estagio(EstagioPipeline.NORMALIZACAO, semaforos)
        assert sem is semaforos["api_externa"]

    def test_semaforo_para_estagio_db(self):
        """Deve retornar semáforo DB para estágios rápidos."""
        semaforos = {
            "llm": asyncio.Semaphore(BUDGET_LLM),
            "api_externa": asyncio.Semaphore(BUDGET_API_EXTERNA),
            "db": asyncio.Semaphore(BUDGET_DB),
        }
        sem = _semaforo_para_estagio(EstagioPipeline.DEDUPLICACAO, semaforos)
        assert sem is semaforos["db"]


# =============================================================================
# Testes do Worker
# =============================================================================


class TestGruposWorker:
    """Testes do GruposWorker."""

    def test_init_defaults(self):
        """Deve inicializar com defaults corretos."""
        worker = GruposWorker()
        assert worker.batch_size == 50
        assert worker.max_workers == 20
        assert worker._stats["ciclos"] == 0

    def test_init_semaforos_criados(self):
        """Deve criar semáforos por tipo."""
        worker = GruposWorker()
        assert "llm" in worker._semaforos
        assert "api_externa" in worker._semaforos
        assert "db" in worker._semaforos

    @pytest.mark.asyncio
    async def test_ciclo_sem_itens(self):
        """Ciclo sem itens deve retornar stats zeradas."""
        with patch("app.workers.grupos_worker.buscar_proximos_pendentes", new_callable=AsyncMock) as mock:
            mock.return_value = []
            worker = GruposWorker()
            stats = await worker.processar_ciclo()

            assert stats["processados"] == 0
            assert stats["erros"] == 0

    @pytest.mark.asyncio
    async def test_ciclo_incrementa_contador(self):
        """Cada ciclo deve incrementar o contador."""
        with patch("app.workers.grupos_worker.buscar_proximos_pendentes", new_callable=AsyncMock) as mock:
            mock.return_value = []
            worker = GruposWorker()

            await worker.processar_ciclo()
            await worker.processar_ciclo()

            assert worker._stats["ciclos"] == 2

    @pytest.mark.asyncio
    async def test_stats_property(self):
        """Stats property deve retornar cópia."""
        worker = GruposWorker()
        stats = worker.stats
        stats["ciclos"] = 999

        assert worker._stats["ciclos"] == 0  # Original não modificado


# =============================================================================
# Testes do Guard de Ciclo
# =============================================================================


class TestGuardCiclo:
    """Testes do guard contra ciclos sobrepostos."""

    @pytest.mark.asyncio
    async def test_ciclo_normal(self):
        """Deve processar ciclo normalmente."""
        with (
            patch("app.workers.grupos_worker.GruposWorker") as MockWorker,
            patch("app.workers.grupos_worker.obter_estatisticas_fila", new_callable=AsyncMock) as mock_stats,
        ):
            mock_instance = MockWorker.return_value
            mock_instance.processar_ciclo = AsyncMock(return_value={"processados": 5, "erros": 0})
            mock_stats.return_value = {}

            resultado = await processar_ciclo_grupos()

            assert resultado["sucesso"] is True
            assert "skipped" not in resultado

    @pytest.mark.asyncio
    async def test_ciclo_sobreposto_ignorado(self):
        """Segundo ciclo deve ser ignorado se o primeiro ainda roda."""
        bloqueio = asyncio.Event()

        async def ciclo_lento():
            """Simula ciclo que demora."""
            # Importa aqui para garantir que usa o lock do módulo
            from app.workers.grupos_worker import _ciclo_lock

            async with _ciclo_lock:
                bloqueio.set()
                await asyncio.sleep(1)

        # Inicia ciclo lento (que segura o lock)
        task = asyncio.create_task(ciclo_lento())
        await bloqueio.wait()

        # Tenta segundo ciclo - deve ser ignorado
        resultado = await processar_ciclo_grupos()

        assert resultado["sucesso"] is True
        assert resultado.get("skipped") is True
        assert resultado["motivo"] == "ciclo_anterior_em_andamento"

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_status_mostra_ciclo_em_andamento(self):
        """Status deve indicar se ciclo está rodando."""
        with (
            patch("app.workers.grupos_worker.obter_estatisticas_fila", new_callable=AsyncMock) as mock_stats,
            patch("app.services.grupos.fila.obter_itens_travados", new_callable=AsyncMock) as mock_travados,
        ):
            mock_stats.return_value = {}
            mock_travados.return_value = []

            status = await obter_status_worker()

            assert "ciclo_em_andamento" in status
            assert status["ciclo_em_andamento"] is False
