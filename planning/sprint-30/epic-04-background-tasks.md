# Epic 04: Background Tasks com Error Handling

## Severidade: ALTO

## Objetivo

Garantir que todas as tasks assincronas tenham tratamento de erro adequado, evitando falhas silenciosas.

## Problema Atual

### Fire-and-Forget Tasks

```python
# Problema: Tasks sem error handling
asyncio.create_task(
    self._registrar_chip_conversa(instance_name, conversa_id, context.telefone)
)
# Se der erro, ninguem fica sabendo!
```

### Locais Identificados (12 ocorrencias)

| Arquivo | Linha | Funcao |
|---------|-------|--------|
| `outbound_dedupe.py` | 145 | Processamento de dedupe |
| `agente.py` | 561 | Emissao de evento |
| `agente.py` | 576 | Emissao de evento |
| `agente.py` | 789 | `_emitir_offer_events` |
| `agente.py` | 894 | `_emitir_fallback_event` |
| `agente.py` | 963 | `_emitir_fallback_event` |
| `handoff/flow.py` | 109 | Notificacao de handoff |
| `post_processors.py` | 258 | Salvamento de metricas |
| `pre_processors.py` | 236 | Registro de chip/conversa |
| `pre_processors.py` | 326 | Emissao de evento |
| `pre_processors.py` | 342 | Emissao de evento |
| `pre_processors.py` | 599 | Processamento adicional |

### Consequencias

1. **Falhas silenciosas:** Erros nao sao logados
2. **Perda de dados:** Eventos importantes podem ser perdidos
3. **Dificuldade de debug:** Impossivel saber o que falhou
4. **Sem retry:** Operacoes falhas nao sao recuperadas

---

## Stories

### S30.E4.1: Criar Wrapper `safe_create_task`

**Objetivo:** Criar funcao wrapper que adiciona error handling automatico.

**Arquivo:** `app/core/tasks.py` (criar)

**Tarefas:**

1. Criar `app/core/tasks.py`:

```python
"""
Utilidades para tasks assincronas.

Sprint 30 - S30.E4.1

Este modulo fornece wrappers seguros para asyncio.create_task
com error handling, logging e metricas.
"""
import asyncio
import logging
from typing import Coroutine, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)

# Contador de falhas por tipo (para metricas)
_task_failures: dict[str, int] = {}


async def _safe_wrapper(
    coro: Coroutine,
    task_name: str,
    on_error: Optional[Callable[[Exception], None]] = None
) -> Any:
    """
    Wrapper que executa coroutine com error handling.

    Args:
        coro: Coroutine a executar
        task_name: Nome para logging/metricas
        on_error: Callback opcional para erros
    """
    try:
        return await coro
    except asyncio.CancelledError:
        logger.debug(f"Task cancelada: {task_name}")
        raise
    except Exception as e:
        # Incrementar contador de falhas
        _task_failures[task_name] = _task_failures.get(task_name, 0) + 1

        logger.error(
            f"Erro em background task '{task_name}': {e}",
            exc_info=True,
            extra={
                "task_name": task_name,
                "error_type": type(e).__name__,
                "total_failures": _task_failures[task_name]
            }
        )

        if on_error:
            try:
                on_error(e)
            except Exception as callback_error:
                logger.error(f"Erro no callback on_error: {callback_error}")

        # Nao re-raise para nao crashar outras tasks
        return None


def safe_create_task(
    coro: Coroutine,
    name: Optional[str] = None,
    on_error: Optional[Callable[[Exception], None]] = None
) -> asyncio.Task:
    """
    Cria task com error handling automatico.

    Uso:
        # Em vez de:
        asyncio.create_task(minha_funcao())

        # Use:
        safe_create_task(minha_funcao(), name="minha_funcao")

    Args:
        coro: Coroutine a executar
        name: Nome da task (para logging)
        on_error: Callback opcional para quando ocorrer erro

    Returns:
        asyncio.Task com wrapper de error handling

    Example:
        # Basico
        safe_create_task(
            emitir_evento(data),
            name="emitir_evento"
        )

        # Com callback de erro
        def log_falha(e):
            slack_notify(f"Falha em task: {e}")

        safe_create_task(
            processo_critico(data),
            name="processo_critico",
            on_error=log_falha
        )
    """
    task_name = name or coro.__qualname__ if hasattr(coro, '__qualname__') else "unknown"
    wrapped = _safe_wrapper(coro, task_name, on_error)
    return asyncio.create_task(wrapped, name=task_name)


def fire_and_forget(name: Optional[str] = None):
    """
    Decorator para funcoes que devem rodar em background.

    Uso:
        @fire_and_forget(name="processar_evento")
        async def processar_evento(data):
            # Esta funcao sera executada em background
            # com error handling automatico
            pass

        # Chamada cria task automaticamente
        processar_evento(data)

    Note:
        O retorno da funcao decorada eh a Task, nao o resultado.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            coro = func(*args, **kwargs)
            task_name = name or func.__name__
            return safe_create_task(coro, name=task_name)
        return wrapper
    return decorator


def get_task_failure_counts() -> dict[str, int]:
    """Retorna contagem de falhas por task (para metricas/alertas)."""
    return _task_failures.copy()


def reset_task_failure_counts():
    """Reseta contadores (para testes)."""
    global _task_failures
    _task_failures = {}


# Funcoes auxiliares para casos especificos

async def safe_gather(*coros, return_exceptions: bool = True) -> list:
    """
    Wrapper para asyncio.gather com error handling.

    Diferente de safe_create_task, este aguarda todas as tasks.
    """
    tasks = [
        _safe_wrapper(coro, f"gather_task_{i}")
        for i, coro in enumerate(coros)
    ]
    return await asyncio.gather(*tasks, return_exceptions=return_exceptions)


def schedule_with_delay(
    coro: Coroutine,
    delay_seconds: float,
    name: Optional[str] = None
) -> asyncio.Task:
    """
    Agenda task para executar apos delay.

    Uso:
        schedule_with_delay(
            enviar_followup(medico_id),
            delay_seconds=300,  # 5 minutos
            name="followup_agendado"
        )
    """
    async def delayed():
        await asyncio.sleep(delay_seconds)
        return await coro

    task_name = name or f"delayed_{coro.__qualname__ if hasattr(coro, '__qualname__') else 'task'}"
    return safe_create_task(delayed(), name=task_name)
```

2. Atualizar `app/core/__init__.py` (se existir) para exportar:

```python
from .tasks import safe_create_task, fire_and_forget, get_task_failure_counts
```

**Como Testar:**

```python
# Teste rapido
import asyncio
from app.core.tasks import safe_create_task, get_task_failure_counts

async def task_que_falha():
    raise ValueError("Erro simulado")

async def main():
    # Deve logar erro mas nao crashar
    task = safe_create_task(task_que_falha(), name="task_teste")
    await task

    # Verificar contadores
    print(get_task_failure_counts())  # {'task_teste': 1}

asyncio.run(main())
```

**DoD:**
- [ ] `app/core/tasks.py` criado
- [ ] `safe_create_task` implementado
- [ ] `fire_and_forget` decorator implementado
- [ ] Contadores de falha implementados
- [ ] Testes basicos passando
- [ ] Commit: `feat(core): adiciona safe_create_task com error handling`

---

### S30.E4.2: Auditar Todos os `create_task`

**Objetivo:** Listar e categorizar todos os usos de `asyncio.create_task`.

**Contexto:** Antes de substituir, precisamos entender o contexto de cada uso.

**Tarefas:**

1. Executar busca:
   ```bash
   grep -rn "asyncio.create_task" app/ --include="*.py" -A 2
   ```

2. Preencher tabela de analise:

| Arquivo | Linha | Criticidade | Observacao |
|---------|-------|-------------|------------|
| `outbound_dedupe.py:145` | Media | Dedupe pode falhar silenciosamente |
| `agente.py:561` | Alta | Evento de negocio pode ser perdido |
| `agente.py:576` | Alta | Evento de negocio pode ser perdido |
| `agente.py:789` | Alta | Oferta pode nao ser registrada |
| `agente.py:894` | Media | Fallback event |
| `agente.py:963` | Media | Fallback event |
| `handoff/flow.py:109` | Alta | Notificacao pode ser perdida |
| `post_processors.py:258` | Media | Metricas podem ser perdidas |
| `pre_processors.py:236` | Media | Registro de chip |
| `pre_processors.py:326` | Alta | Evento pode ser perdido |
| `pre_processors.py:342` | Alta | Evento pode ser perdido |
| `pre_processors.py:599` | Media | Processamento adicional |

3. Priorizar substituicao:
   - **Alta criticidade primeiro:** Eventos de negocio, notificacoes
   - **Media depois:** Metricas, registros

**DoD:**
- [ ] Todos os 12 usos documentados
- [ ] Criticidade atribuida a cada um
- [ ] Ordem de substituicao definida
- [ ] Commit: `docs(sprint-30): auditoria de create_task`

---

### S30.E4.3: Substituir por Wrapper Seguro

**Objetivo:** Trocar todos os `asyncio.create_task` por `safe_create_task`.

**Contexto:** Substituicao gradual, arquivo por arquivo.

**Tarefas:**

1. Para cada arquivo, seguir este padrao:

   **Antes:**
   ```python
   import asyncio

   asyncio.create_task(
       self._registrar_chip_conversa(instance_name, conversa_id, telefone)
   )
   ```

   **Depois:**
   ```python
   from app.core.tasks import safe_create_task

   safe_create_task(
       self._registrar_chip_conversa(instance_name, conversa_id, telefone),
       name="registrar_chip_conversa"
   )
   ```

2. Ordem de substituicao (por criticidade):

   **Fase 1 - Alta Criticidade:**
   - [ ] `agente.py` (4 ocorrencias)
   - [ ] `handoff/flow.py` (1 ocorrencia)
   - [ ] `pre_processors.py` linhas 326, 342 (eventos)

   **Fase 2 - Media Criticidade:**
   - [ ] `pre_processors.py` linhas 236, 599
   - [ ] `post_processors.py`
   - [ ] `outbound_dedupe.py`

3. Para cada arquivo:
   ```bash
   # 1. Fazer substituicao
   # 2. Rodar testes do arquivo
   uv run pytest tests/services/test_agente.py -v

   # 3. Verificar que nao quebrou
   uv run pytest tests/ -v
   ```

**Exemplo Completo - agente.py:**

```python
# app/services/agente.py

# Adicionar import no topo
from app.core.tasks import safe_create_task

# Linha 561: Substituir
# DE:
asyncio.create_task(
    _emitir_offer_events(...)
)
# PARA:
safe_create_task(
    _emitir_offer_events(...),
    name="emitir_offer_events"
)

# Linha 789: Substituir
# DE:
asyncio.create_task(
    _emitir_offer_events(medico_id, vaga, "offer_made")
)
# PARA:
safe_create_task(
    _emitir_offer_events(medico_id, vaga, "offer_made"),
    name="emitir_offer_made"
)

# Linhas 894, 963: Substituir
# DE:
asyncio.create_task(_emitir_fallback_event(telefone, "enviar_mensagens_sequencia"))
# PARA:
safe_create_task(
    _emitir_fallback_event(telefone, "enviar_mensagens_sequencia"),
    name="emitir_fallback_event"
)
```

**Como Testar:**

```bash
# Apos cada arquivo
uv run pytest tests/ -v

# Verificar logs em ambiente local
uv run uvicorn app.main:app --reload
# Trigger um erro em background e verificar se eh logado
```

**DoD:**
- [ ] Todos os 12 `create_task` substituidos
- [ ] Cada task com nome descritivo
- [ ] Todos os testes passando
- [ ] Commit: `refactor: substitui create_task por safe_create_task`

---

### S30.E4.4: Adicionar Metricas de Falha

**Objetivo:** Expor metricas de falhas de tasks para monitoramento.

**Contexto:** Com os contadores em `tasks.py`, podemos expor via endpoint.

**Arquivo:** `app/api/routes/health.py` (modificar)

**Tarefas:**

1. Adicionar endpoint de metricas de tasks:

```python
# app/api/routes/health.py

from app.core.tasks import get_task_failure_counts

@router.get("/health/tasks")
async def task_metrics():
    """Retorna metricas de tasks em background."""
    failures = get_task_failure_counts()

    return {
        "total_failures": sum(failures.values()),
        "failures_by_task": failures,
        "tasks_with_failures": len([k for k, v in failures.items() if v > 0])
    }
```

2. (Opcional) Adicionar ao health check principal:

```python
@router.get("/health")
async def health():
    task_failures = get_task_failure_counts()
    total_failures = sum(task_failures.values())

    return {
        "status": "healthy" if total_failures < 100 else "degraded",
        "background_task_failures": total_failures,
        # ... outros checks
    }
```

**Como Testar:**

```bash
curl http://localhost:8000/health/tasks | jq
```

**DoD:**
- [ ] Endpoint `/health/tasks` criado
- [ ] Retorna contagem de falhas por task
- [ ] Integrado ao health check principal
- [ ] Commit: `feat(health): adiciona metricas de background tasks`

---

### S30.E4.5: Criar Testes para Cenarios de Erro

**Objetivo:** Garantir que o error handling funciona corretamente.

**Arquivo:** `tests/core/test_tasks.py` (criar)

**Tarefas:**

1. Criar testes:

```python
# tests/core/test_tasks.py
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
            assert "Erro de teste" in call_args

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

    @pytest.mark.asyncio
    async def test_executa_apos_delay(self):
        """Deve executar apos delay especificado."""
        executed = False

        async def task_delayed():
            nonlocal executed
            executed = True

        task = schedule_with_delay(
            task_delayed(),
            delay_seconds=0.1,  # 100ms para teste rapido
            name="delayed_test"
        )

        # Ainda nao executou
        assert not executed

        await task

        # Agora executou
        assert executed


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
```

**Como Testar:**

```bash
uv run pytest tests/core/test_tasks.py -v
```

**DoD:**
- [ ] Arquivo de testes criado
- [ ] Testes para safe_create_task (5+)
- [ ] Testes para fire_and_forget
- [ ] Testes para schedule_with_delay
- [ ] Teste de integracao
- [ ] Todos os testes passando
- [ ] Commit: `test(core): testes para safe_create_task`

---

## Checklist do Epic

- [ ] **S30.E4.1** - Wrapper `safe_create_task` criado
- [ ] **S30.E4.2** - Auditoria completa
- [ ] **S30.E4.3** - Todos os 12 substituidos
- [ ] **S30.E4.4** - Metricas expostas
- [ ] **S30.E4.5** - Testes passando
- [ ] Zero `asyncio.create_task` direto no codigo
- [ ] Todos os testes da suite passando

---

## Verificacao Final

```bash
# Deve retornar 0 ocorrencias (exceto em tasks.py)
grep -rn "asyncio.create_task" app/ --include="*.py" | grep -v "core/tasks.py"

# Verificar que safe_create_task eh usado
grep -rn "safe_create_task" app/ --include="*.py" | wc -l
# Esperado: 12+
```

---

## Arquivos Modificados

| Arquivo | Acao | Linhas |
|---------|------|--------|
| `app/core/tasks.py` | Criar | ~120 |
| `app/services/agente.py` | Modificar | ~10 |
| `app/services/outbound_dedupe.py` | Modificar | ~2 |
| `app/services/handoff/flow.py` | Modificar | ~2 |
| `app/pipeline/pre_processors.py` | Modificar | ~8 |
| `app/pipeline/post_processors.py` | Modificar | ~2 |
| `app/api/routes/health.py` | Modificar | ~15 |
| `tests/core/test_tasks.py` | Criar | ~150 |

---

## Tempo Estimado

| Story | Complexidade | Estimativa |
|-------|--------------|------------|
| S30.E4.1 | Baixa | 1h |
| S30.E4.2 | Media | 30min |
| S30.E4.3 | Media | 1.5h |
| S30.E4.4 | Baixa | 30min |
| S30.E4.5 | Media | 1h |
| **Total** | | **~4.5h** |
