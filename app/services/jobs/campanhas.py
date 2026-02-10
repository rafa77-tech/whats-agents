"""
Service para processamento de campanhas agendadas.

Sprint 10 - S10.E3.1
Sprint 35 - E04: Atualizado para usar campanha_executor
"""

import logging
from dataclasses import dataclass

from app.core.timezone import agora_utc
from app.services.campanhas import campanha_executor, campanha_repository

logger = logging.getLogger(__name__)


@dataclass
class ResultadoCampanhas:
    """Resultado do processamento de campanhas."""

    campanhas_encontradas: int = 0
    campanhas_iniciadas: int = 0


async def processar_campanhas_agendadas() -> ResultadoCampanhas:
    """
    Processa campanhas que estao prontas para iniciar.

    Returns:
        ResultadoCampanhas com estatisticas
    """
    agora = agora_utc()

    # Buscar campanhas prontas usando o repository
    campanhas = await campanha_repository.listar_agendadas(agora)
    resultado = ResultadoCampanhas(campanhas_encontradas=len(campanhas))

    for campanha in campanhas:
        sucesso = await _iniciar_campanha(campanha.id)
        if sucesso:
            resultado.campanhas_iniciadas += 1

    return resultado


async def _iniciar_campanha(campanha_id: int) -> bool:
    """
    Inicia execucao de uma campanha.

    Args:
        campanha_id: ID da campanha

    Returns:
        True se iniciada com sucesso
    """
    try:
        sucesso = await campanha_executor.executar(campanha_id)

        if sucesso:
            logger.info(f"Campanha {campanha_id} executada com sucesso")
        else:
            logger.warning(f"Campanha {campanha_id} executada com problemas")

        return sucesso

    except Exception as e:
        logger.error(f"Erro ao executar campanha {campanha_id}: {e}")
        return False
