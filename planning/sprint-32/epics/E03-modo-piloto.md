# E03: Modo Piloto

**Fase:** 1 - Foundation
**Estimativa:** 3h
**Prioridade:** Crítica ⭐
**Dependências:** Nenhuma

---

## Objetivo

Implementar flag `PILOT_MODE` que desabilita ações autônomas da Julia durante o período de testes, permitindo validar o sistema de forma segura.

## Por que é Crítico

O modo piloto é a **primeira linha de defesa** contra comportamentos indesejados:
- Evita que Julia envie mensagens automáticas antes de estar pronta
- Permite testar campanhas manuais sem disparos automáticos
- Dá controle total ao gestor durante validação

---

## O que FUNCIONA no Modo Piloto

| Funcionalidade | Status | Motivo |
|----------------|--------|--------|
| Campanhas manuais (gestor cria) | ✅ | Controle humano |
| Respostas a médicos (inbound) | ✅ | Médico iniciou |
| Canal de ajuda Julia → Gestor | ✅ | Segurança |
| Gestor comanda Julia (Slack) | ✅ | Controle humano |
| Guardrails (rate limit, horário) | ✅ | Segurança |
| checkNumberStatus (validação) | ✅ | Apenas leitura |

## O que NÃO FUNCIONA no Modo Piloto

| Funcionalidade | Status | Motivo |
|----------------|--------|--------|
| Discovery automático | ❌ | Envia mensagens sozinha |
| Oferta automática (furo escala) | ❌ | Envia mensagens sozinha |
| Reativação automática | ❌ | Envia mensagens sozinha |
| Feedback automático | ❌ | Envia mensagens sozinha |

---

## Tarefas

### T1: Adicionar flag PILOT_MODE ao config.py (20min)

**Arquivo:** `app/core/config.py`

**Modificação:**

```python
class Settings(BaseSettings):
    # ... existentes ...

    # Modo Piloto (Sprint 32 E03)
    # Quando True, desabilita ações autônomas (Discovery, Oferta, Reativação, Feedback automáticos)
    # Mantém funcionando: campanhas manuais, respostas inbound, canal de ajuda, comandos Slack
    # IMPORTANTE: Iniciar em True para testes seguros, mudar para False após validação
    PILOT_MODE: bool = True
```

**Regras:**
- Default = `True` (seguro por padrão)
- Configurável via env var `PILOT_MODE=false`

### T2: Adicionar properties helper (15min)

**Arquivo:** `app/core/config.py`

**Adicionar:**

```python
@property
def is_pilot_mode(self) -> bool:
    """Retorna True se está em modo piloto (ações autônomas desabilitadas)."""
    return self.PILOT_MODE

@property
def autonomous_features_status(self) -> dict[str, bool]:
    """
    Retorna status das funcionalidades autônomas.

    Em modo piloto, todas retornam False.
    Fora do piloto, todas retornam True.
    """
    enabled = not self.PILOT_MODE
    return {
        "discovery_automatico": enabled,
        "oferta_automatica": enabled,
        "reativacao_automatica": enabled,
        "feedback_automatico": enabled,
    }
```

### T3: Criar módulo pilot_mode.py com utilitários (45min)

**Arquivo:** `app/workers/pilot_mode.py`

**Conteúdo completo:**

```python
"""
Utilitários para Modo Piloto (Sprint 32 E03).

Fornece guards e decorators para controlar execução de funcionalidades
autônomas durante o período de piloto.

USO:
    from app.workers.pilot_mode import (
        is_pilot_mode,
        require_pilot_disabled,
        skip_if_pilot,
        AutonomousFeature,
    )

    # Guard simples
    if is_pilot_mode():
        logger.info("Modo piloto ativo - pulando ação autônoma")
        return

    # Decorator para funções
    @skip_if_pilot(AutonomousFeature.DISCOVERY)
    async def executar_discovery_automatico():
        ...
"""
import logging
from enum import Enum
from functools import wraps
from typing import Callable, TypeVar, ParamSpec, Any
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class AutonomousFeature(str, Enum):
    """Tipos de funcionalidades autônomas controladas pelo modo piloto."""

    DISCOVERY = "discovery_automatico"
    OFERTA = "oferta_automatica"
    REATIVACAO = "reativacao_automatica"
    FEEDBACK = "feedback_automatico"


def is_pilot_mode() -> bool:
    """
    Verifica se está em modo piloto.

    Returns:
        True se PILOT_MODE está ativo (ações autônomas desabilitadas)

    Exemplo:
        if is_pilot_mode():
            logger.info("Pulando ação - modo piloto ativo")
            return
    """
    return settings.is_pilot_mode


def require_pilot_disabled(feature: AutonomousFeature) -> bool:
    """
    Verifica se a funcionalidade autônoma pode executar.

    Args:
        feature: Tipo da funcionalidade autônoma

    Returns:
        True se pode executar (piloto desabilitado)
        False se deve pular (piloto ativo)

    Exemplo:
        if not require_pilot_disabled(AutonomousFeature.DISCOVERY):
            logger.info("Discovery automático desabilitado em modo piloto")
            return
    """
    if settings.is_pilot_mode:
        logger.info(
            f"Modo piloto ativo - {feature.value} desabilitado",
            extra={"feature": feature.value, "pilot_mode": True},
        )
        return False
    return True


def skip_if_pilot(feature: AutonomousFeature):
    """
    Decorator que pula execução se estiver em modo piloto.

    Args:
        feature: Tipo da funcionalidade autônoma

    Exemplo:
        @skip_if_pilot(AutonomousFeature.OFERTA)
        async def enviar_ofertas_automaticas():
            # Só executa se PILOT_MODE=False
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
            if settings.is_pilot_mode:
                logger.info(
                    f"Modo piloto ativo - pulando {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "feature": feature.value,
                        "pilot_mode": True,
                    },
                )
                return None
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs):
            if settings.is_pilot_mode:
                logger.info(
                    f"Modo piloto ativo - pulando {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "feature": feature.value,
                        "pilot_mode": True,
                    },
                )
                return None
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_pilot_status() -> dict[str, Any]:
    """
    Retorna status completo do modo piloto.

    Útil para endpoints de health/status e dashboard.

    Returns:
        Dict com status do piloto e features
    """
    return {
        "pilot_mode": settings.is_pilot_mode,
        "features": settings.autonomous_features_status,
        "message": (
            "Modo piloto ATIVO - ações autônomas desabilitadas"
            if settings.is_pilot_mode
            else "Modo piloto INATIVO - todas as funcionalidades habilitadas"
        ),
    }


def log_pilot_status() -> None:
    """
    Loga status do modo piloto.

    Útil para chamar no startup de workers.
    """
    status = get_pilot_status()
    if status["pilot_mode"]:
        logger.warning(
            "🧪 MODO PILOTO ATIVO - Ações autônomas desabilitadas",
            extra=status,
        )
    else:
        logger.info(
            "🚀 Modo piloto INATIVO - Todas as funcionalidades habilitadas",
            extra=status,
        )
```

### T4: Adicionar status do piloto ao health endpoint (30min)

**Arquivo:** `app/api/routes/health.py`

**Adicionar novo endpoint:**

```python
from app.workers.pilot_mode import get_pilot_status

@router.get("/health/pilot")
async def pilot_status():
    """
    Retorna status do modo piloto.

    Útil para:
    - Dashboard verificar se piloto está ativo
    - Monitoramento confirmar estado
    - Debug de comportamento
    """
    status = get_pilot_status()
    return {
        **status,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

**Adicionar ao /health/deep:**

```python
# Dentro da função deep_health_check, adicionar:
checks["pilot_mode"] = {
    "status": "ok",
    "enabled": settings.is_pilot_mode,
    "features": settings.autonomous_features_status,
}
```

### T5: Criar testes unitários (30min)

**Arquivo:** `tests/unit/test_pilot_mode.py`

```python
import pytest
from unittest.mock import patch
from app.workers.pilot_mode import (
    is_pilot_mode,
    require_pilot_disabled,
    skip_if_pilot,
    get_pilot_status,
    AutonomousFeature,
)


class TestPilotModeGuards:
    """Testes para guards do modo piloto."""

    def test_is_pilot_mode_quando_ativo(self):
        """is_pilot_mode deve retornar True quando PILOT_MODE=True."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            assert is_pilot_mode() is True

    def test_is_pilot_mode_quando_inativo(self):
        """is_pilot_mode deve retornar False quando PILOT_MODE=False."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False
            assert is_pilot_mode() is False

    def test_require_pilot_disabled_bloqueia_quando_ativo(self):
        """require_pilot_disabled deve retornar False quando piloto ativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            assert require_pilot_disabled(AutonomousFeature.DISCOVERY) is False

    def test_require_pilot_disabled_permite_quando_inativo(self):
        """require_pilot_disabled deve retornar True quando piloto inativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False
            assert require_pilot_disabled(AutonomousFeature.DISCOVERY) is True


class TestSkipIfPilotDecorator:
    """Testes para decorator skip_if_pilot."""

    @pytest.mark.asyncio
    async def test_decorator_pula_funcao_async_quando_piloto_ativo(self):
        """Decorator deve pular função async quando piloto ativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True

            chamado = False

            @skip_if_pilot(AutonomousFeature.OFERTA)
            async def funcao_teste():
                nonlocal chamado
                chamado = True
                return "executado"

            resultado = await funcao_teste()

            assert chamado is False
            assert resultado is None

    @pytest.mark.asyncio
    async def test_decorator_executa_funcao_async_quando_piloto_inativo(self):
        """Decorator deve executar função async quando piloto inativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False

            @skip_if_pilot(AutonomousFeature.OFERTA)
            async def funcao_teste():
                return "executado"

            resultado = await funcao_teste()

            assert resultado == "executado"

    def test_decorator_pula_funcao_sync_quando_piloto_ativo(self):
        """Decorator deve pular função sync quando piloto ativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True

            chamado = False

            @skip_if_pilot(AutonomousFeature.DISCOVERY)
            def funcao_teste():
                nonlocal chamado
                chamado = True
                return "executado"

            resultado = funcao_teste()

            assert chamado is False
            assert resultado is None


class TestGetPilotStatus:
    """Testes para get_pilot_status."""

    def test_status_quando_piloto_ativo(self):
        """Deve retornar status correto quando piloto ativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            mock_settings.autonomous_features_status = {
                "discovery_automatico": False,
                "oferta_automatica": False,
                "reativacao_automatica": False,
                "feedback_automatico": False,
            }

            status = get_pilot_status()

            assert status["pilot_mode"] is True
            assert status["features"]["discovery_automatico"] is False
            assert "ATIVO" in status["message"]

    def test_status_quando_piloto_inativo(self):
        """Deve retornar status correto quando piloto inativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False
            mock_settings.autonomous_features_status = {
                "discovery_automatico": True,
                "oferta_automatica": True,
                "reativacao_automatica": True,
                "feedback_automatico": True,
            }

            status = get_pilot_status()

            assert status["pilot_mode"] is False
            assert status["features"]["discovery_automatico"] is True
            assert "INATIVO" in status["message"]


class TestAutonomousFeatureEnum:
    """Testes para enum AutonomousFeature."""

    def test_todos_os_valores_existem(self):
        """Enum deve ter todos os 4 tipos de features."""
        assert AutonomousFeature.DISCOVERY.value == "discovery_automatico"
        assert AutonomousFeature.OFERTA.value == "oferta_automatica"
        assert AutonomousFeature.REATIVACAO.value == "reativacao_automatica"
        assert AutonomousFeature.FEEDBACK.value == "feedback_automatico"

    def test_enum_eh_string(self):
        """Enum deve ser string para facilitar logging."""
        assert isinstance(AutonomousFeature.DISCOVERY, str)
```

### T6: Atualizar .env.example (10min)

**Arquivo:** `.env.example`

**Adicionar:**

```bash
# === Modo Piloto (Sprint 32) ===
# Quando true, desabilita ações autônomas da Julia
# Manter true durante testes, mudar para false em produção estável
PILOT_MODE=true
```

### T7: Documentar uso no CLAUDE.md (15min)

**Arquivo:** `CLAUDE.md`

**Adicionar seção:**

```markdown
### Modo Piloto

O sistema possui um modo piloto (`PILOT_MODE=true`) que desabilita ações autônomas:

| Funcionalidade | Piloto ON | Piloto OFF |
|----------------|-----------|------------|
| Campanhas manuais | ✅ | ✅ |
| Respostas inbound | ✅ | ✅ |
| Discovery automático | ❌ | ✅ |
| Oferta automática | ❌ | ✅ |
| Reativação automática | ❌ | ✅ |
| Feedback automático | ❌ | ✅ |

**Verificar status:**
- Endpoint: `GET /health/pilot`
- Config: `settings.is_pilot_mode`

**Desativar piloto:**
```bash
# .env
PILOT_MODE=false
```
```

---

## Definition of Done (DoD)

### Critérios Obrigatórios

- [ ] **Flag PILOT_MODE no config**
  - [ ] `PILOT_MODE: bool = True` existe em Settings
  - [ ] Default é `True` (seguro)
  - [ ] Configurável via env var

- [ ] **Properties helper funcionam**
  - [ ] `settings.is_pilot_mode` retorna bool
  - [ ] `settings.autonomous_features_status` retorna dict com 4 features

- [ ] **Módulo pilot_mode.py criado**
  - [ ] `is_pilot_mode()` funciona
  - [ ] `require_pilot_disabled()` funciona
  - [ ] `skip_if_pilot()` decorator funciona (async e sync)
  - [ ] `get_pilot_status()` retorna dict completo
  - [ ] `log_pilot_status()` loga corretamente

- [ ] **Health endpoint atualizado**
  - [ ] `GET /health/pilot` retorna status
  - [ ] `/health/deep` inclui `pilot_mode` nos checks

- [ ] **Testes passando**
  - [ ] `uv run pytest tests/unit/test_pilot_mode.py -v` = OK

- [ ] **Documentação atualizada**
  - [ ] `.env.example` tem `PILOT_MODE`
  - [ ] `CLAUDE.md` tem seção sobre modo piloto

### Verificação Manual

```bash
# 1. Verificar default (deve ser True)
curl http://localhost:8000/health/pilot
# Deve retornar: {"pilot_mode": true, ...}

# 2. Verificar com env var False
PILOT_MODE=false uv run python -c "from app.core.config import settings; print(settings.is_pilot_mode)"
# Deve retornar: False

# 3. Testar decorator
uv run python -c "
import asyncio
from app.workers.pilot_mode import skip_if_pilot, AutonomousFeature

@skip_if_pilot(AutonomousFeature.DISCOVERY)
async def teste():
    print('EXECUTOU!')
    return True

resultado = asyncio.run(teste())
print(f'Resultado: {resultado}')
"
# Com PILOT_MODE=true: Resultado: None (não executou)
# Com PILOT_MODE=false: EXECUTOU! Resultado: True
```

---

## Notas para o Desenvolvedor

1. **Segurança primeiro:**
   - SEMPRE default `True` (piloto ativo)
   - Nunca inverter a lógica (True = seguro)

2. **Logging é importante:**
   - Toda vez que uma função for pulada, deve logar
   - Facilita debug ("por que não executou?")

3. **Não esquecer de usar:**
   - Os workers autônomos (E05-E07) devem usar esses guards
   - Sem os guards, o modo piloto não faz nada

4. **Enum vs string:**
   - Usar `AutonomousFeature` enum, não strings diretas
   - Evita typos e facilita refatoração
