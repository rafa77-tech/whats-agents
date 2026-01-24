"""
Chip Affinity - Sistema de afinidade chip-médico.

Sprint 36 - T11.5: Registro de interações chip-médico.

Mantém histórico de interações para que o ChipSelector
priorize chips que já conversaram com o médico.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def registrar_interacao_chip_medico(
    chip_id: str,
    telefone_medico: str,
    tipo: str,  # "msg_enviada", "msg_recebida", "resposta_obtida"
) -> None:
    """
    Registra interação para cálculo de afinidade.

    Sprint 36 - T11.5

    Args:
        chip_id: ID do chip
        telefone_medico: Telefone do médico
        tipo: Tipo de interação (msg_enviada, msg_recebida, resposta_obtida)
    """
    try:
        # Registrar na tabela chip_interactions
        supabase.table("chip_interactions").insert({
            "chip_id": chip_id,
            "tipo": tipo,
            "destinatario": telefone_medico,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        logger.debug(
            f"[ChipAffinity] Interação registrada: "
            f"chip={chip_id[:8]}, telefone={telefone_medico[-4:]}, tipo={tipo}"
        )

    except Exception as e:
        logger.warning(f"[ChipAffinity] Erro ao registrar interação: {e}")


async def buscar_chip_com_afinidade(
    telefone_medico: str,
    chips_elegiveis: List[Dict],
) -> Optional[Dict]:
    """
    Busca chip com maior afinidade para o médico.

    Sprint 36 - T11.5

    Prioriza:
    1. Chip que já obteve resposta do médico
    2. Chip com mais interações recentes

    Args:
        telefone_medico: Telefone do médico
        chips_elegiveis: Lista de chips elegíveis para seleção

    Returns:
        Chip com afinidade ou None
    """
    if not chips_elegiveis:
        return None

    chip_ids = [c["id"] for c in chips_elegiveis]

    try:
        # Buscar interações com este telefone
        result = supabase.table("chip_interactions").select(
            "chip_id, tipo, created_at"
        ).eq(
            "destinatario", telefone_medico
        ).in_(
            "chip_id", chip_ids
        ).order(
            "created_at", desc=True
        ).limit(50).execute()

        if not result.data:
            return None

        # Calcular score de afinidade por chip
        afinidade_scores: Dict[str, Dict] = {}

        for interacao in result.data:
            cid = interacao["chip_id"]
            if cid not in afinidade_scores:
                afinidade_scores[cid] = {
                    "total": 0,
                    "respostas": 0,
                    "msgs_enviadas": 0,
                    "msgs_recebidas": 0,
                }

            afinidade_scores[cid]["total"] += 1

            if interacao["tipo"] == "msg_recebida":
                afinidade_scores[cid]["msgs_recebidas"] += 1
                # Recebeu resposta = alta afinidade
                afinidade_scores[cid]["respostas"] += 1
            elif interacao["tipo"] == "msg_enviada":
                afinidade_scores[cid]["msgs_enviadas"] += 1

        if not afinidade_scores:
            return None

        # Ordenar por: respostas (peso 3), total (peso 1)
        melhor_chip_id = max(
            afinidade_scores.keys(),
            key=lambda cid: (
                afinidade_scores[cid]["respostas"] * 3 +
                afinidade_scores[cid]["total"]
            )
        )

        # Retornar o chip correspondente
        for chip in chips_elegiveis:
            if chip["id"] == melhor_chip_id:
                logger.debug(
                    f"[ChipAffinity] Afinidade encontrada: "
                    f"chip={chip.get('telefone', 'N/A')[-4:]}, "
                    f"respostas={afinidade_scores[melhor_chip_id]['respostas']}, "
                    f"total={afinidade_scores[melhor_chip_id]['total']}"
                )
                return chip

        return None

    except Exception as e:
        logger.warning(f"[ChipAffinity] Erro ao buscar afinidade: {e}")
        return None


async def obter_afinidade_resumo(
    telefone_medico: str,
) -> Dict:
    """
    Obtém resumo de afinidade de um médico com todos os chips.

    Args:
        telefone_medico: Telefone do médico

    Returns:
        {
            "telefone": str,
            "chips": [
                {"chip_id": str, "interacoes": int, "respostas": int}
            ]
        }
    """
    try:
        result = supabase.table("chip_interactions").select(
            "chip_id, tipo"
        ).eq(
            "destinatario", telefone_medico
        ).execute()

        chips: Dict[str, Dict] = {}

        for interacao in result.data or []:
            cid = interacao["chip_id"]
            if cid not in chips:
                chips[cid] = {"chip_id": cid, "interacoes": 0, "respostas": 0}

            chips[cid]["interacoes"] += 1
            if interacao["tipo"] == "msg_recebida":
                chips[cid]["respostas"] += 1

        return {
            "telefone": telefone_medico,
            "chips": list(chips.values()),
        }

    except Exception as e:
        logger.warning(f"[ChipAffinity] Erro ao obter resumo: {e}")
        return {"telefone": telefone_medico, "chips": []}


async def registrar_conversa_bidirecional(
    chip_id: str,
    telefone_medico: str,
) -> bool:
    """
    Sprint 36 - T08.5: Marca interação como bidirecional.

    Chamado quando recebemos resposta de um número para qual enviamos.

    Args:
        chip_id: ID do chip
        telefone_medico: Telefone do médico que respondeu

    Returns:
        True se conversa foi marcada como bidirecional
    """
    try:
        # Verificar se enviamos para este número nas últimas 24h
        from datetime import timedelta

        ontem = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        result = supabase.table("chip_interactions").select(
            "id"
        ).eq(
            "chip_id", chip_id
        ).eq(
            "destinatario", telefone_medico
        ).eq(
            "tipo", "msg_enviada"
        ).gte(
            "created_at", ontem
        ).is_(
            "obteve_resposta", "null"
        ).order(
            "created_at", desc=True
        ).limit(1).execute()

        if result.data:
            # Marcar como bidirecional
            supabase.table("chip_interactions").update({
                "obteve_resposta": True,
                "resposta_em": datetime.now(timezone.utc).isoformat(),
            }).eq("id", result.data[0]["id"]).execute()

            logger.info(
                f"[ChipAffinity] Conversa bidirecional: "
                f"chip={chip_id[:8]}, médico={telefone_medico[-4:]}"
            )

            # Incrementar contador no chip
            await _incrementar_conversas_bidirecionais(chip_id)

            return True

        return False

    except Exception as e:
        logger.warning(f"[ChipAffinity] Erro ao registrar bidirecional: {e}")
        return False


async def _incrementar_conversas_bidirecionais(chip_id: str) -> None:
    """Incrementa contador de conversas bidirecionais do chip."""
    try:
        # Buscar valor atual
        result = supabase.table("chips").select(
            "conversas_bidirecionais"
        ).eq("id", chip_id).single().execute()

        atual = (result.data or {}).get("conversas_bidirecionais") or 0

        supabase.table("chips").update({
            "conversas_bidirecionais": atual + 1,
        }).eq("id", chip_id).execute()

    except Exception as e:
        logger.warning(f"[ChipAffinity] Erro ao incrementar bidirecionais: {e}")


async def calcular_taxa_resposta(chip_id: str, dias: int = 7) -> float:
    """
    Sprint 36 - T08.3: Calcula taxa de resposta do chip.

    Taxa = mensagens que obtiveram resposta / mensagens enviadas (período)

    Args:
        chip_id: ID do chip
        dias: Período para cálculo (default 7 dias)

    Returns:
        Taxa de resposta (0.0 a 1.0)
    """
    try:
        from datetime import timedelta

        periodo_inicio = (
            datetime.now(timezone.utc) - timedelta(days=dias)
        ).isoformat()

        # Total de mensagens enviadas no período
        enviadas = supabase.table("chip_interactions").select(
            "id", count="exact"
        ).eq(
            "chip_id", chip_id
        ).eq(
            "tipo", "msg_enviada"
        ).gte(
            "created_at", periodo_inicio
        ).execute()

        total_enviadas = enviadas.count or 0

        if total_enviadas == 0:
            return 0.0

        # Mensagens que obtiveram resposta
        com_resposta = supabase.table("chip_interactions").select(
            "id", count="exact"
        ).eq(
            "chip_id", chip_id
        ).eq(
            "tipo", "msg_enviada"
        ).eq(
            "obteve_resposta", True
        ).gte(
            "created_at", periodo_inicio
        ).execute()

        total_com_resposta = com_resposta.count or 0

        taxa = total_com_resposta / total_enviadas

        logger.debug(
            f"[ChipAffinity] Taxa resposta chip {chip_id[:8]}: "
            f"{total_com_resposta}/{total_enviadas} = {taxa:.2%}"
        )

        return taxa

    except Exception as e:
        logger.warning(f"[ChipAffinity] Erro ao calcular taxa resposta: {e}")
        return 0.0


async def calcular_taxa_delivery(chip_id: str, dias: int = 7) -> float:
    """
    Sprint 36 - T08.3: Calcula taxa de delivery do chip.

    Taxa = mensagens entregues com sucesso / total de tentativas de envio

    Args:
        chip_id: ID do chip
        dias: Período para cálculo (default 7 dias)

    Returns:
        Taxa de delivery (0.0 a 1.0)
    """
    try:
        from datetime import timedelta

        periodo_inicio = (
            datetime.now(timezone.utc) - timedelta(days=dias)
        ).isoformat()

        # Total de envios (sucessos + erros)
        total_result = supabase.table("chip_interactions").select(
            "id", count="exact"
        ).eq(
            "chip_id", chip_id
        ).in_(
            "tipo", ["msg_enviada", "msg_erro"]
        ).gte(
            "created_at", periodo_inicio
        ).execute()

        total_tentativas = total_result.count or 0

        if total_tentativas == 0:
            return 1.0  # Sem dados = 100% por default

        # Envios com sucesso
        sucessos = supabase.table("chip_interactions").select(
            "id", count="exact"
        ).eq(
            "chip_id", chip_id
        ).eq(
            "tipo", "msg_enviada"
        ).gte(
            "created_at", periodo_inicio
        ).execute()

        total_sucessos = sucessos.count or 0

        taxa = total_sucessos / total_tentativas

        logger.debug(
            f"[ChipAffinity] Taxa delivery chip {chip_id[:8]}: "
            f"{total_sucessos}/{total_tentativas} = {taxa:.2%}"
        )

        return taxa

    except Exception as e:
        logger.warning(f"[ChipAffinity] Erro ao calcular taxa delivery: {e}")
        return 1.0  # Default 100% se erro


async def atualizar_metricas_chip(chip_id: str) -> Dict:
    """
    Sprint 36 - T07.2/T07.3: Atualiza todas as métricas do chip.

    Args:
        chip_id: ID do chip

    Returns:
        {
            "taxa_resposta": float,
            "taxa_delivery": float,
            "conversas_bidirecionais": int,
        }
    """
    taxa_resposta = await calcular_taxa_resposta(chip_id)
    taxa_delivery = await calcular_taxa_delivery(chip_id)

    try:
        # Buscar contador de bidirecionais
        result = supabase.table("chips").select(
            "conversas_bidirecionais"
        ).eq("id", chip_id).single().execute()

        conversas_bi = (result.data or {}).get("conversas_bidirecionais") or 0

        # Atualizar chip
        supabase.table("chips").update({
            "taxa_resposta": taxa_resposta,
            "taxa_delivery": taxa_delivery,
        }).eq("id", chip_id).execute()

        logger.debug(
            f"[ChipAffinity] Métricas atualizadas chip {chip_id[:8]}: "
            f"resposta={taxa_resposta:.2%}, delivery={taxa_delivery:.2%}, "
            f"bidirecionais={conversas_bi}"
        )

        return {
            "taxa_resposta": taxa_resposta,
            "taxa_delivery": taxa_delivery,
            "conversas_bidirecionais": conversas_bi,
        }

    except Exception as e:
        logger.warning(f"[ChipAffinity] Erro ao atualizar métricas: {e}")
        return {
            "taxa_resposta": taxa_resposta,
            "taxa_delivery": taxa_delivery,
            "conversas_bidirecionais": 0,
        }
