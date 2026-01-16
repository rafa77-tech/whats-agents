"""
Utilitários para Modo Piloto (Sprint 32 E03).

Fornece guards e decorators para controlar execução de funcionalidades
autônomas durante o período de piloto.

MODO PILOTO (PILOT_MODE=True):
    FUNCIONA:
    - Campanhas manuais (gestor cria)
    - Respostas a médicos (inbound)
    - Canal de ajuda Julia → Gestor
    - Gestor comanda Julia (Slack)
    - Guardrails (rate limit, horário, etc.)
    - checkNumberStatus (validação de telefones)

    NÃO FUNCIONA:
    - Discovery automático
    - Oferta automática (furo de escala)
    - Reativação automática
    - Feedback automático

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

    # Guard com tipo específico
    if not require_pilot_disabled(AutonomousFeature.OFERTA):
        return
"""
import logging
from enum import Enum
from functools import wraps
from typing import Callable, Any, TypeVar, ParamSpec

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


def skip_if_pilot(feature: AutonomousFeature) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator que pula execução se estiver em modo piloto.

    Args:
        feature: Tipo da funcionalidade autônoma

    Returns:
        Decorator que wraps a função

    Exemplo:
        @skip_if_pilot(AutonomousFeature.OFERTA)
        async def enviar_ofertas_automaticas():
            # Só executa se PILOT_MODE=False
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
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
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
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

        # Detecta se é async ou sync
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

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
