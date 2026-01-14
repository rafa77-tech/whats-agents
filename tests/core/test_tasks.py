"""
Testes para utilidades de tasks assincronas.

Sprint 30 - S30.E4.5
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch

from app.core.tasks import (
    safe_create_task,
    fire_and_forget,
    get_task_failure_counts,
    reset_task_failure_counts,
    schedule_with_delay,
    safe_gather,
)


class TestSafeCreateTask:
    """Testes para safe_create_task."""

    def setup_method(self):
        """Limpa contadores antes de cada teste."""
        reset_task_failure_counts()

    @pytest.mark.asyncio
    async def test_executa_task_com_sucesso(self):
        """Task bem sucedida deve retornar resultado."""
        async def task_ok():
            return "sucesso"

        task = safe_create_task(task_ok(), name="task_ok")
        result = await task

        assert result == "sucesso"
        assert get_task_failure_counts().get("task_ok", 0) == 0

    @pytest.mark.asyncio
    async def test_captura_erro_sem_crashar(self):
        """Task com erro deve ser capturada sem crashar."""
        async def task_erro():
            raise ValueError("Erro simulado")

        task = safe_create_task(task_erro(), name="task_erro")
        result = await task

        # Nao deve ter crashado
        assert result is None
        # Deve ter incrementado contador
        assert get_task_failure_counts()["task_erro"] == 1

    @pytest.mark.asyncio
    async def test_loga_erro(self):
        """Erro deve ser logado."""
        async def task_erro():
            raise RuntimeError("Erro de teste")

        with patch("app.core.tasks.logger") as mock_logger:
            task = safe_create_task(task_erro(), name="task_logada")
            await task

            mock_logger.error.assert_called()
            call_args = str(mock_logger.error.call_args)
            assert "task_logada" in call_args

    @pytest.mark.asyncio
    async def test_callback_on_error(self):
        """Callback de erro deve ser chamado."""
        callback = MagicMock()

        async def task_erro():
            raise ValueError("Erro")

        task = safe_create_task(
            task_erro(),
            name="task_callback",
            on_error=callback
        )
        await task

        callback.assert_called_once()
        # Argumento deve ser a exception
        assert isinstance(callback.call_args[0][0], ValueError)

    @pytest.mark.asyncio
    async def test_multiplas_falhas_incrementam_contador(self):
        """Multiplas falhas devem incrementar contador."""
        async def task_erro():
            raise ValueError("Erro")

        for _ in range(5):
            task = safe_create_task(task_erro(), name="task_repetida")
            await task

        assert get_task_failure_counts()["task_repetida"] == 5

    @pytest.mark.asyncio
    async def test_nome_automatico_quando_nao_fornecido(self):
        """Deve usar nome da coroutine quando nao fornecido."""
        async def minha_funcao_teste():
            return "ok"

        task = safe_create_task(minha_funcao_teste())
        result = await task

        assert result == "ok"


class TestFireAndForget:
    """Testes para decorator fire_and_forget."""

    def setup_method(self):
        reset_task_failure_counts()

    @pytest.mark.asyncio
    async def test_decorator_cria_task(self):
        """Decorator deve criar task automaticamente."""
        executed = False

        @fire_and_forget(name="decorated_task")
        async def minha_task():
            nonlocal executed
            executed = True

        task = minha_task()
        await task

        assert executed

    @pytest.mark.asyncio
    async def test_decorator_com_erro(self):
        """Decorator deve capturar erros."""
        @fire_and_forget(name="decorated_erro")
        async def task_erro():
            raise RuntimeError("Erro decorado")

        task = task_erro()
        await task

        assert get_task_failure_counts()["decorated_erro"] == 1


class TestScheduleWithDelay:
    """Testes para schedule_with_delay."""

    def setup_method(self):
        reset_task_failure_counts()

    @pytest.mark.asyncio
    async def test_executa_apos_delay(self):
        """Deve executar apos delay especificado."""
        executed = False

        async def task_delayed():
            nonlocal executed
            executed = True

        task = schedule_with_delay(
            task_delayed(),
            delay_seconds=0.05,  # 50ms para teste rapido
            name="delayed_test"
        )

        # Ainda nao executou
        await asyncio.sleep(0.01)
        assert not executed

        await task

        # Agora executou
        assert executed


class TestSafeGather:
    """Testes para safe_gather."""

    def setup_method(self):
        reset_task_failure_counts()

    @pytest.mark.asyncio
    async def test_executa_multiplas_tasks(self):
        """Deve executar multiplas tasks."""
        async def task1():
            return 1

        async def task2():
            return 2

        results = await safe_gather(task1(), task2())

        assert 1 in results
        assert 2 in results

    @pytest.mark.asyncio
    async def test_continua_mesmo_com_erro(self):
        """Erro em uma task nao deve afetar outras."""
        async def task_ok():
            return "ok"

        async def task_erro():
            raise ValueError("Erro")

        results = await safe_gather(task_ok(), task_erro(), task_ok())

        # Deve ter executado as tasks OK
        assert results.count("ok") == 2
        # Task com erro retorna None
        assert None in results


class TestIntegracaoComPipeline:
    """Testes de integracao simulando uso no pipeline."""

    def setup_method(self):
        reset_task_failure_counts()

    @pytest.mark.asyncio
    async def test_multiplas_tasks_em_paralelo(self):
        """Multiplas tasks devem executar em paralelo."""
        results = []

        async def task_paralela(n):
            await asyncio.sleep(0.01)
            results.append(n)

        tasks = [
            safe_create_task(task_paralela(i), name=f"paralela_{i}")
            for i in range(5)
        ]

        await asyncio.gather(*tasks)

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_erro_em_uma_nao_afeta_outras(self):
        """Erro em uma task nao deve afetar as outras."""
        results = []

        async def task_ok(n):
            results.append(n)

        async def task_erro():
            raise ValueError("Erro")

        tasks = [
            safe_create_task(task_ok(1), name="ok_1"),
            safe_create_task(task_erro(), name="erro"),
            safe_create_task(task_ok(2), name="ok_2"),
        ]

        await asyncio.gather(*tasks)

        # Tasks OK devem ter executado
        assert 1 in results
        assert 2 in results
        # Contador de erro incrementado
        assert get_task_failure_counts()["erro"] == 1
