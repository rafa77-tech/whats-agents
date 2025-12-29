"""
Job de processamento de handoffs (follow-up e expiracao).

Sprint 20 - E07 - Automacao de follow-up.
Sprint 21 - E01 - Verificar canary flag antes de follow-ups.
"""
import logging
from datetime import datetime, timezone
from typing import List

from app.services.external_handoff.repository import (
    listar_handoffs_pendentes,
    atualizar_status_handoff,
    atualizar_followup,
)
from app.services.external_handoff.messaging import enviar_followup_divulgador
from app.services.business_events import emit_event, EventType, EventSource, BusinessEvent
from app.services.supabase import supabase
from app.services.outbound import send_outbound_message
from app.services.slack import enviar_slack
from app.services.policy.flags import get_external_handoff_flags

logger = logging.getLogger(__name__)

# Configuracoes de tempo
FOLLOWUP_1_HORAS = 2   # Primeiro follow-up apos 2h
FOLLOWUP_2_HORAS = 24  # Segundo follow-up apos 24h
FOLLOWUP_3_HORAS = 36  # Terceiro follow-up apos 36h
MAX_FOLLOWUPS = 3      # Maximo de follow-ups


async def processar_handoffs_pendentes() -> dict:
    """
    Processa todos os handoffs pendentes.

    Fluxo:
    1. Verifica flag external_handoff (se desabilitado, apenas expira - não envia follow-ups)
    2. Busca handoffs com status 'pending' ou 'contacted'
    3. Para cada handoff:
       - Se expirou: expira
       - Se passou de 36h e followup_count < 3: envia follow-up 3
       - Se passou de 24h e followup_count < 2: envia follow-up 2
       - Se passou de 2h e followup_count == 0: envia follow-up 1

    Returns:
        Dict com estatisticas do processamento
    """
    logger.info("Iniciando processamento de handoffs pendentes")

    # Verificar flag para follow-ups (expiracoes sempre processam)
    flags = await get_external_handoff_flags()
    followups_pausados = not flags.enabled

    if followups_pausados:
        logger.info("Follow-ups pausados (external_handoff.enabled=false)")

    stats = {
        "total_processados": 0,
        "followups_enviados": 0,
        "followups_pausados": 0,
        "expirados": 0,
        "erros": 0,
    }

    try:
        handoffs = await listar_handoffs_pendentes()
        logger.info(f"Encontrados {len(handoffs)} handoffs pendentes")

        now = datetime.now(timezone.utc)

        for handoff in handoffs:
            try:
                resultado = await _processar_handoff(handoff, now, followups_pausados)
                stats["total_processados"] += 1

                if resultado == "followup":
                    stats["followups_enviados"] += 1
                elif resultado == "followup_paused":
                    stats["followups_pausados"] += 1
                elif resultado == "expired":
                    stats["expirados"] += 1

            except Exception as e:
                logger.error(f"Erro ao processar handoff {handoff['id']}: {e}")
                stats["erros"] += 1

        logger.info(f"Processamento concluido: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Erro no job de handoffs: {e}")
        raise


async def _processar_handoff(
    handoff: dict,
    now: datetime,
    followups_pausados: bool = False
) -> str:
    """
    Processa um handoff individual.

    Args:
        handoff: Dados do handoff
        now: Timestamp atual
        followups_pausados: Se True, não envia follow-ups (kill switch)

    Returns:
        'followup', 'followup_paused', 'expired', ou 'noop'
    """
    handoff_id = handoff["id"]
    reserved_until = handoff.get("reserved_until")
    followup_count = handoff.get("followup_count", 0) or 0
    created_at = handoff.get("created_at")

    # Converter timestamps
    if isinstance(reserved_until, str):
        reserved_until = datetime.fromisoformat(reserved_until.replace("Z", "+00:00"))
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

    # Verificar expiracao
    if now >= reserved_until:
        await _expirar_handoff(handoff)
        return "expired"

    # Calcular horas desde criacao
    horas_desde_criacao = (now - created_at).total_seconds() / 3600

    # Verificar se atingiu maximo de follow-ups
    if followup_count >= MAX_FOLLOWUPS:
        return "noop"

    # Follow-up 1: apos 2h
    if followup_count == 0 and horas_desde_criacao >= FOLLOWUP_1_HORAS:
        if followups_pausados:
            return "followup_paused"
        await _enviar_followup(handoff, 1)
        return "followup"

    # Follow-up 2: apos 24h
    if followup_count == 1 and horas_desde_criacao >= FOLLOWUP_2_HORAS:
        if followups_pausados:
            return "followup_paused"
        await _enviar_followup(handoff, 2)
        return "followup"

    # Follow-up 3: apos 36h
    if followup_count == 2 and horas_desde_criacao >= FOLLOWUP_3_HORAS:
        if followups_pausados:
            return "followup_paused"
        await _enviar_followup(handoff, 3)
        return "followup"

    return "noop"


async def _enviar_followup(handoff: dict, numero: int) -> None:
    """
    Envia mensagem de follow-up para o divulgador.

    Args:
        handoff: Dados do handoff
        numero: Numero do follow-up (1, 2, 3)
    """
    handoff_id = handoff["id"]
    divulgador_nome = handoff.get("divulgador_nome", "")
    divulgador_telefone = handoff.get("divulgador_telefone")

    logger.info(f"Enviando follow-up {numero} para handoff {handoff_id[:8]}")

    # Montar mensagem baseada no numero do follow-up
    if numero == 1:
        mensagem = (
            f"Oi {divulgador_nome}! Tudo bem?\n\n"
            "Conseguiu falar com o medico sobre aquele plantao?\n\n"
            "Me avisa aqui se fechou ou nao, pra eu atualizar"
        )
    elif numero == 2:
        mensagem = (
            f"Oi {divulgador_nome}!\n\n"
            "Ainda to aguardando retorno sobre o plantao.\n"
            "O medico ta interessado, me ajuda aqui?\n\n"
            "Responde CONFIRMADO se fechou ou NAO FECHOU se nao rolou"
        )
    else:
        mensagem = (
            f"Ultimo aviso {divulgador_nome}!\n\n"
            "Se eu nao tiver retorno, vou liberar o medico pra outras vagas.\n\n"
            "CONFIRMADO ou NAO FECHOU?"
        )

    try:
        await enviar_followup_divulgador(
            telefone=divulgador_telefone,
            mensagem=mensagem,
        )

        # Atualizar contador de follow-ups
        await atualizar_followup(handoff_id, numero)

        # Emitir evento
        event = BusinessEvent(
            event_type=EventType.HANDOFF_FOLLOWUP_SENT,
            source=EventSource.BACKEND,
            event_props={
                "handoff_id": handoff_id,
                "followup_number": numero,
                "divulgador_telefone": divulgador_telefone[-4:],
            },
            dedupe_key=f"handoff_followup:{handoff_id}:{numero}",
        )
        await emit_event(event)

        logger.info(f"Follow-up {numero} enviado para handoff {handoff_id[:8]}")

    except Exception as e:
        logger.error(f"Erro ao enviar follow-up: {e}")
        raise


async def _expirar_handoff(handoff: dict) -> None:
    """
    Expira um handoff e libera a vaga.

    Args:
        handoff: Dados do handoff
    """
    handoff_id = handoff["id"]
    vaga_id = handoff["vaga_id"]
    cliente_id = handoff.get("cliente_id")

    logger.info(f"Expirando handoff {handoff_id[:8]}")

    # Atualizar handoff
    await atualizar_status_handoff(
        handoff_id=handoff_id,
        novo_status="expired",
        expired_at=datetime.now(timezone.utc),
    )

    # Liberar vaga
    supabase.table("vagas") \
        .update({"status": "aberta"}) \
        .eq("id", vaga_id) \
        .execute()

    logger.info(f"Vaga {vaga_id} liberada")

    # Emitir evento
    event = BusinessEvent(
        event_type=EventType.HANDOFF_EXPIRED,
        source=EventSource.BACKEND,
        vaga_id=vaga_id,
        cliente_id=cliente_id,
        event_props={
            "handoff_id": handoff_id,
            "vaga_id": vaga_id,
            "followup_count": handoff.get("followup_count", 0),
        },
        dedupe_key=f"handoff_expired:{handoff_id}",
    )
    await emit_event(event)

    # Notificar Slack
    cor = "#9CA3AF"  # Cinza
    mensagem_slack = {
        "text": ":hourglass: Handoff Expirado",
        "attachments": [{
            "color": cor,
            "title": "Handoff Expirado",
            "fields": [
                {"title": "Divulgador", "value": handoff.get("divulgador_nome", "N/A"), "short": True},
                {"title": "Follow-ups", "value": str(handoff.get("followup_count", 0)), "short": True},
                {"title": "Vaga", "value": vaga_id[:8], "short": True},
            ],
            "footer": "Agente Julia - Sprint 20",
        }]
    }
    try:
        await enviar_slack(mensagem_slack)
    except Exception as e:
        logger.warning(f"Erro ao notificar Slack: {e}")

    # Notificar medico
    if cliente_id:
        try:
            await send_outbound_message(
                cliente_id=cliente_id,
                mensagem=(
                    "Oi! Infelizmente o divulgador nao retornou sobre o plantao.\n\n"
                    "Vou liberar a vaga. Quer que eu procure outras opcoes pra voce?"
                ),
                campanha="handoff_expired",
            )
        except Exception as e:
            logger.error(f"Erro ao notificar medico {cliente_id}: {e}")
