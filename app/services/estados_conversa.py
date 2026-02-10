"""
Serviço de Estados de Conversa.

Sprint 32 E15 - Gerenciamento de estados de conversa.

Estados possíveis:
- active: Fluxo normal, Julia responde
- aguardando_gestor: Julia pediu ajuda, esperando resposta
- aguardando_medico: Julia perguntou algo, esperando médico
- paused: Conversa pausada manualmente
- handoff: Transferida para humano
- completed: Conversa encerrada
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES - ESTADOS
# =============================================================================

ESTADO_ATIVO = "active"
ESTADO_AGUARDANDO_GESTOR = "aguardando_gestor"
ESTADO_AGUARDANDO_MEDICO = "aguardando_medico"
ESTADO_PAUSADO = "paused"
ESTADO_HANDOFF = "handoff"
ESTADO_CONCLUIDO = "completed"

# Estados que impedem Julia de responder
ESTADOS_BLOQUEANTES = [
    ESTADO_AGUARDANDO_GESTOR,
    ESTADO_PAUSADO,
    ESTADO_HANDOFF,
]

# Motivos de pausa
MOTIVO_AGUARDANDO_GESTOR = "aguardando_gestor"
MOTIVO_AGUARDANDO_INFO = "aguardando_info"
MOTIVO_PAUSADO_MANUAL = "pausado_manual"
MOTIVO_HANDOFF = "handoff"


# =============================================================================
# FUNÇÕES DE VERIFICAÇÃO
# =============================================================================


async def pode_julia_responder(conversa_id: str) -> bool:
    """
    Verifica se Julia pode responder na conversa.

    Args:
        conversa_id: ID da conversa

    Returns:
        True se Julia pode responder
    """
    try:
        response = (
            supabase.table("conversations")
            .select("status, controlled_by")
            .eq("id", conversa_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return False

        conversa = response.data[0]
        status = conversa.get("status")
        controlled_by = conversa.get("controlled_by")

        # Se está em handoff, não pode
        if controlled_by == "human":
            return False

        # Se está em estado bloqueante, não pode
        if status in ESTADOS_BLOQUEANTES:
            return False

        return True

    except Exception as e:
        logger.error(f"Erro ao verificar se Julia pode responder: {e}")
        return False


async def obter_estado_conversa(conversa_id: str) -> Optional[dict]:
    """
    Obtém estado atual da conversa.

    Args:
        conversa_id: ID da conversa

    Returns:
        Dict com estado ou None
    """
    try:
        response = (
            supabase.table("conversations")
            .select(
                "id, status, controlled_by, pausada_em, retomada_em, motivo_pausa, pedido_ajuda_id"
            )
            .eq("id", conversa_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        conversa = response.data[0]

        return {
            "conversa_id": conversa_id,
            "status": conversa.get("status"),
            "controlled_by": conversa.get("controlled_by"),
            "pausada_em": conversa.get("pausada_em"),
            "retomada_em": conversa.get("retomada_em"),
            "motivo_pausa": conversa.get("motivo_pausa"),
            "pedido_ajuda_id": conversa.get("pedido_ajuda_id"),
            "julia_pode_responder": await pode_julia_responder(conversa_id),
        }

    except Exception as e:
        logger.error(f"Erro ao obter estado: {e}")
        return None


# =============================================================================
# FUNÇÕES DE TRANSIÇÃO
# =============================================================================


async def pausar_para_gestor(
    conversa_id: str,
    pedido_ajuda_id: str,
    motivo: str = MOTIVO_AGUARDANDO_GESTOR,
) -> dict:
    """
    Pausa conversa aguardando resposta do gestor.

    Args:
        conversa_id: ID da conversa
        pedido_ajuda_id: ID do pedido de ajuda
        motivo: Motivo da pausa

    Returns:
        Dict com resultado
    """
    try:
        response = (
            supabase.table("conversations")
            .update(
                {
                    "status": ESTADO_AGUARDANDO_GESTOR,
                    "pausada_em": datetime.now(timezone.utc).isoformat(),
                    "motivo_pausa": motivo,
                    "pedido_ajuda_id": pedido_ajuda_id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", conversa_id)
            .execute()
        )

        if response.data:
            logger.info(f"Conversa {conversa_id} pausada aguardando gestor")
            return {"success": True, "status": ESTADO_AGUARDANDO_GESTOR}

        return {"success": False, "error": "Conversa não encontrada"}

    except Exception as e:
        logger.error(f"Erro ao pausar conversa: {e}")
        return {"success": False, "error": str(e)}


async def retomar_conversa(
    conversa_id: str,
    motivo: str = "resposta_recebida",
) -> dict:
    """
    Retoma conversa que estava pausada.

    Args:
        conversa_id: ID da conversa
        motivo: Motivo da retomada

    Returns:
        Dict com resultado
    """
    try:
        response = (
            supabase.table("conversations")
            .update(
                {
                    "status": ESTADO_ATIVO,
                    "retomada_em": datetime.now(timezone.utc).isoformat(),
                    "motivo_pausa": None,
                    "pedido_ajuda_id": None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", conversa_id)
            .execute()
        )

        if response.data:
            logger.info(f"Conversa {conversa_id} retomada: {motivo}")
            return {"success": True, "status": ESTADO_ATIVO}

        return {"success": False, "error": "Conversa não encontrada"}

    except Exception as e:
        logger.error(f"Erro ao retomar conversa: {e}")
        return {"success": False, "error": str(e)}


async def marcar_handoff(
    conversa_id: str,
    motivo: str,
    controlado_por: str = "human",
) -> dict:
    """
    Marca conversa como handoff (transferida para humano).

    Args:
        conversa_id: ID da conversa
        motivo: Motivo do handoff
        controlado_por: Quem está controlando

    Returns:
        Dict com resultado
    """
    try:
        response = (
            supabase.table("conversations")
            .update(
                {
                    "status": ESTADO_HANDOFF,
                    "controlled_by": controlado_por,
                    "pausada_em": datetime.now(timezone.utc).isoformat(),
                    "motivo_pausa": MOTIVO_HANDOFF,
                    "escalation_reason": motivo,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", conversa_id)
            .execute()
        )

        if response.data:
            logger.info(f"Conversa {conversa_id} em handoff: {motivo}")
            return {"success": True, "status": ESTADO_HANDOFF}

        return {"success": False, "error": "Conversa não encontrada"}

    except Exception as e:
        logger.error(f"Erro ao marcar handoff: {e}")
        return {"success": False, "error": str(e)}


async def resolver_handoff(
    conversa_id: str,
    retornar_para_julia: bool = True,
) -> dict:
    """
    Resolve handoff, opcionalmente retornando para Julia.

    Args:
        conversa_id: ID da conversa
        retornar_para_julia: Se deve retornar controle para Julia

    Returns:
        Dict com resultado
    """
    try:
        update_data = {
            "retomada_em": datetime.now(timezone.utc).isoformat(),
            "motivo_pausa": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if retornar_para_julia:
            update_data["status"] = ESTADO_ATIVO
            update_data["controlled_by"] = "ai"
        else:
            update_data["status"] = ESTADO_CONCLUIDO

        response = (
            supabase.table("conversations").update(update_data).eq("id", conversa_id).execute()
        )

        if response.data:
            novo_status = update_data.get("status", ESTADO_ATIVO)
            logger.info(f"Handoff resolvido para conversa {conversa_id}: {novo_status}")
            return {"success": True, "status": novo_status}

        return {"success": False, "error": "Conversa não encontrada"}

    except Exception as e:
        logger.error(f"Erro ao resolver handoff: {e}")
        return {"success": False, "error": str(e)}


async def pausar_manual(
    conversa_id: str,
    motivo: str = "pausa_manual",
) -> dict:
    """
    Pausa conversa manualmente.

    Args:
        conversa_id: ID da conversa
        motivo: Motivo da pausa

    Returns:
        Dict com resultado
    """
    try:
        response = (
            supabase.table("conversations")
            .update(
                {
                    "status": ESTADO_PAUSADO,
                    "pausada_em": datetime.now(timezone.utc).isoformat(),
                    "motivo_pausa": MOTIVO_PAUSADO_MANUAL,
                    "escalation_reason": motivo,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", conversa_id)
            .execute()
        )

        if response.data:
            logger.info(f"Conversa {conversa_id} pausada manualmente: {motivo}")
            return {"success": True, "status": ESTADO_PAUSADO}

        return {"success": False, "error": "Conversa não encontrada"}

    except Exception as e:
        logger.error(f"Erro ao pausar conversa: {e}")
        return {"success": False, "error": str(e)}


async def concluir_conversa(
    conversa_id: str,
    motivo: str = "conversa_encerrada",
) -> dict:
    """
    Marca conversa como concluída.

    Args:
        conversa_id: ID da conversa
        motivo: Motivo do encerramento

    Returns:
        Dict com resultado
    """
    try:
        response = (
            supabase.table("conversations")
            .update(
                {
                    "status": ESTADO_CONCLUIDO,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "escalation_reason": motivo,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", conversa_id)
            .execute()
        )

        if response.data:
            logger.info(f"Conversa {conversa_id} concluída: {motivo}")
            return {"success": True, "status": ESTADO_CONCLUIDO}

        return {"success": False, "error": "Conversa não encontrada"}

    except Exception as e:
        logger.error(f"Erro ao concluir conversa: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# FUNÇÕES DE LISTAGEM
# =============================================================================


async def listar_conversas_pausadas() -> list[dict]:
    """
    Lista todas as conversas pausadas aguardando ação.

    Returns:
        Lista de conversas pausadas
    """
    try:
        response = (
            supabase.table("conversations")
            .select(
                "id, cliente_id, status, pausada_em, motivo_pausa, pedido_ajuda_id, clientes:cliente_id(primeiro_nome, telefone)"
            )
            .in_("status", [ESTADO_AGUARDANDO_GESTOR, ESTADO_PAUSADO])
            .order("pausada_em", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar conversas pausadas: {e}")
        return []


async def listar_conversas_handoff() -> list[dict]:
    """
    Lista conversas em handoff.

    Returns:
        Lista de conversas em handoff
    """
    try:
        response = (
            supabase.table("conversations")
            .select(
                "id, cliente_id, status, pausada_em, escalation_reason, clientes:cliente_id(primeiro_nome, telefone)"
            )
            .eq("status", ESTADO_HANDOFF)
            .order("pausada_em", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar conversas em handoff: {e}")
        return []


async def contar_conversas_por_estado() -> dict:
    """
    Conta conversas por estado.

    Returns:
        Dict com contagem por estado
    """
    try:
        estados = [ESTADO_ATIVO, ESTADO_AGUARDANDO_GESTOR, ESTADO_PAUSADO, ESTADO_HANDOFF]
        resultado = {}

        for estado in estados:
            response = (
                supabase.table("conversations")
                .select("id", count="exact")
                .eq("status", estado)
                .execute()
            )
            resultado[estado] = response.count or 0

        return resultado

    except Exception as e:
        logger.error(f"Erro ao contar conversas: {e}")
        return {}
