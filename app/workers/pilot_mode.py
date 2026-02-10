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
        True se pode executar (feature habilitada)
        False se deve pular (piloto ativo ou feature desabilitada)

    Lógica (Sprint 35 - Controle Granular):
        1. Se PILOT_MODE=True → sempre False (master switch)
        2. Se PILOT_MODE=False → verifica flag individual da feature

    Exemplo:
        if not require_pilot_disabled(AutonomousFeature.DISCOVERY):
            logger.info("Discovery automático desabilitado")
            return
    """
    # Verificação granular usando o método is_feature_enabled
    if not settings.is_feature_enabled(feature.value):
        reason = "modo piloto ativo" if settings.is_pilot_mode else "feature desabilitada"
        logger.info(
            f"{feature.value} desabilitado ({reason})",
            extra={
                "feature": feature.value,
                "pilot_mode": settings.is_pilot_mode,
                "feature_enabled": False,
            },
        )
        return False
    return True


def skip_if_pilot(feature: AutonomousFeature) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator que pula execução se a feature estiver desabilitada.

    Args:
        feature: Tipo da funcionalidade autônoma

    Returns:
        Decorator que wraps a função

    Lógica (Sprint 35 - Controle Granular):
        1. Se PILOT_MODE=True → pula (master switch)
        2. Se PILOT_MODE=False e feature desabilitada → pula
        3. Se PILOT_MODE=False e feature habilitada → executa

    Exemplo:
        @skip_if_pilot(AutonomousFeature.OFERTA)
        async def enviar_ofertas_automaticas():
            # Só executa se feature está habilitada
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
            if not settings.is_feature_enabled(feature.value):
                reason = "modo piloto ativo" if settings.is_pilot_mode else "feature desabilitada"
                logger.info(
                    f"Pulando {func.__name__} ({reason})",
                    extra={
                        "function": func.__name__,
                        "feature": feature.value,
                        "pilot_mode": settings.is_pilot_mode,
                        "feature_enabled": False,
                    },
                )
                return None
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
            if not settings.is_feature_enabled(feature.value):
                reason = "modo piloto ativo" if settings.is_pilot_mode else "feature desabilitada"
                logger.info(
                    f"Pulando {func.__name__} ({reason})",
                    extra={
                        "function": func.__name__,
                        "feature": feature.value,
                        "pilot_mode": settings.is_pilot_mode,
                        "feature_enabled": False,
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
    Retorna status completo do modo piloto e features.

    Útil para endpoints de health/status e dashboard.

    Returns:
        Dict com status do piloto e features individuais

    Sprint 35: Atualizado para refletir controle granular.
    """
    features = settings.autonomous_features_status
    enabled_count = sum(1 for v in features.values() if v)
    total_count = len(features)

    if settings.is_pilot_mode:
        message = "Modo piloto ATIVO - todas as ações autônomas desabilitadas"
    elif enabled_count == total_count:
        message = "Todas as funcionalidades autônomas habilitadas"
    elif enabled_count == 0:
        message = "Todas as funcionalidades autônomas desabilitadas"
    else:
        enabled_names = [k for k, v in features.items() if v]
        message = (
            f"{enabled_count}/{total_count} funcionalidades habilitadas: {', '.join(enabled_names)}"
        )

    return {
        "pilot_mode": settings.is_pilot_mode,
        "features": features,
        "enabled_count": enabled_count,
        "total_count": total_count,
        "message": message,
    }


def log_pilot_status() -> None:
    """
    Loga status do modo piloto e features.

    Útil para chamar no startup de workers.

    Sprint 35: Atualizado para refletir controle granular.
    """
    status = get_pilot_status()
    if status["pilot_mode"]:
        logger.warning(
            "🧪 MODO PILOTO ATIVO - Todas as ações autônomas desabilitadas",
            extra=status,
        )
    elif status["enabled_count"] == status["total_count"]:
        logger.info(
            "🚀 Todas as funcionalidades autônomas habilitadas",
            extra=status,
        )
    elif status["enabled_count"] == 0:
        logger.warning(
            "⚠️ Todas as funcionalidades autônomas desabilitadas",
            extra=status,
        )
    else:
        logger.info(
            f"🔧 {status['enabled_count']}/{status['total_count']} funcionalidades autônomas habilitadas",
            extra=status,
        )
