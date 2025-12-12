"""
Service para processamento de campanhas agendadas.

Sprint 10 - S10.E3.1
"""
import logging
from dataclasses import dataclass
from datetime import datetime

from app.services.supabase import supabase
from app.services.campanha import criar_envios_campanha

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
    agora = datetime.utcnow().isoformat()

    # Buscar campanhas prontas
    campanhas_resp = (
        supabase.table("campanhas")
        .select("id")
        .eq("status", "agendada")
        .lte("agendar_para", agora)
        .execute()
    )

    campanhas = campanhas_resp.data or []
    resultado = ResultadoCampanhas(campanhas_encontradas=len(campanhas))

    for campanha in campanhas:
        sucesso = await _iniciar_campanha(campanha["id"], agora)
        if sucesso:
            resultado.campanhas_iniciadas += 1

    return resultado


async def _iniciar_campanha(campanha_id: str, agora: str) -> bool:
    """
    Inicia uma campanha individual.

    Args:
        campanha_id: ID da campanha
        agora: Timestamp atual

    Returns:
        True se iniciada com sucesso
    """
    try:
        await criar_envios_campanha(campanha_id)

        supabase.table("campanhas").update({
            "status": "ativa",
            "iniciada_em": agora
        }).eq("id", campanha_id).execute()

        logger.info(f"Campanha {campanha_id} iniciada")
        return True

    except Exception as e:
        logger.error(f"Erro ao iniciar campanha {campanha_id}: {e}")
        return False
