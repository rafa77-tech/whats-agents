"""
Validadores para emissao de eventos de negocio.

Sprint 17 - E04
"""
import logging

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Status validos para emitir offer_made
VALID_STATUS_FOR_OFFER = ("aberta", "anunciada")


async def vaga_pode_receber_oferta(vaga_id: str) -> bool:
    """
    Verifica se vaga pode receber offer_made.

    TRAVA DE SEGURANCA: Evita emitir offer_made duplicado
    em vaga ja reservada/cancelada.

    Args:
        vaga_id: UUID da vaga

    Returns:
        True se vaga esta aberta ou anunciada
    """
    try:
        response = (
            supabase.table("vagas")
            .select("status")
            .eq("id", vaga_id)
            .maybe_single()
            .execute()
        )

        if not response.data:
            logger.warning(f"Vaga nao encontrada para offer_made: {vaga_id}")
            return False

        status = response.data.get("status")
        if status not in VALID_STATUS_FOR_OFFER:
            logger.info(
                f"offer_made ignorado: vaga {vaga_id[:8]} "
                f"esta {status} (esperado: {VALID_STATUS_FOR_OFFER})"
            )
            return False

        return True

    except Exception as e:
        logger.error(f"Erro ao validar vaga para offer_made: {e}")
        return False  # Fail closed: na duvida, nao emite
