"""
Processamento de confirmacao de handoff.

Sprint 20 - E05 - Logica de confirmacao.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.services.external_handoff.repository import atualizar_status_handoff
from app.services.supabase import supabase
from app.services.business_events import emit_event, EventType, EventSource, BusinessEvent
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


async def processar_confirmacao(
    handoff: dict,
    action: str,
    confirmed_by: str,
    ip_address: str = None,
) -> dict[str, Any]:
    """
    Processa confirmacao de handoff (confirmed ou not_confirmed).

    Args:
        handoff: Dados do handoff
        action: 'confirmed' ou 'not_confirmed'
        confirmed_by: 'link' ou 'keyword'
        ip_address: IP de origem (para auditoria)

    Returns:
        Dict com resultado do processamento
    """
    handoff_id = handoff["id"]
    vaga_id = handoff["vaga_id"]
    cliente_id = handoff.get("cliente_id")

    logger.info(f"Processando confirmacao: handoff={handoff_id}, action={action}")

    # Determinar novo status
    if action == "confirmed":
        novo_status_handoff = "confirmed"
        novo_status_vaga = "fechada"
        event_type = EventType.HANDOFF_CONFIRMED
    else:
        novo_status_handoff = "not_confirmed"
        novo_status_vaga = "aberta"  # Libera a vaga
        event_type = EventType.HANDOFF_NOT_CONFIRMED

    # Atualizar handoff
    await atualizar_status_handoff(
        handoff_id=handoff_id,
        novo_status=novo_status_handoff,
        confirmed_at=datetime.now(timezone.utc) if action == "confirmed" else None,
        confirmed_by=confirmed_by,
        confirmation_source=ip_address,
    )

    # Atualizar vaga
    supabase.table("vagas").update({"status": novo_status_vaga}).eq("id", vaga_id).execute()

    logger.info(f"Vaga {vaga_id} atualizada para status={novo_status_vaga}")

    # Emitir evento
    event = BusinessEvent(
        event_type=event_type,
        source=EventSource.BACKEND,
        cliente_id=cliente_id,
        vaga_id=vaga_id,
        event_props={
            "handoff_id": handoff_id,
            "confirmed_by": confirmed_by,
            "ip_address": ip_address,
        },
        dedupe_key=f"{event_type.value}:{handoff_id}",
    )
    await emit_event(event)

    # Notificar Slack
    emoji = ":white_check_mark:" if action == "confirmed" else ":x:"
    cor = "#10B981" if action == "confirmed" else "#F59E0B"
    mensagem_slack = {
        "text": f"{emoji} Handoff {action.upper()}",
        "attachments": [
            {
                "color": cor,
                "title": f"Handoff {action.upper()}",
                "fields": [
                    {
                        "title": "Divulgador",
                        "value": handoff.get("divulgador_nome", "N/A"),
                        "short": True,
                    },
                    {"title": "Via", "value": confirmed_by, "short": True},
                    {"title": "Vaga", "value": vaga_id[:8], "short": True},
                ],
                "footer": "Agente Julia - Sprint 20",
            }
        ],
    }
    try:
        await enviar_slack(mensagem_slack)
    except Exception as e:
        logger.warning(f"Erro ao notificar Slack: {e}")

    # Enviar mensagem para medico via Julia
    if cliente_id:
        await _notificar_medico(cliente_id, action, handoff)

    return {
        "success": True,
        "handoff_status": novo_status_handoff,
        "vaga_status": novo_status_vaga,
    }


async def _notificar_medico(
    cliente_id: str,
    action: str,
    handoff: dict,
) -> None:
    """
    Envia mensagem para o medico sobre o resultado.

    Args:
        cliente_id: ID do medico
        action: 'confirmed' ou 'not_confirmed'
        handoff: Dados do handoff
    """
    from app.services.outbound import send_outbound_message

    divulgador_nome = handoff.get("divulgador_nome", "o divulgador")

    if action == "confirmed":
        mensagem = (
            f"Boa noticia! {divulgador_nome} confirmou seu plantao!\n\nQualquer coisa me avisa aqui"
        )
    else:
        mensagem = (
            f"Oi! {divulgador_nome} informou que o plantao nao foi fechado.\n\n"
            "Quer que eu procure outras opcoes pra voce?"
        )

    try:
        await send_outbound_message(
            cliente_id=cliente_id,
            mensagem=mensagem,
            campanha="handoff_resultado",
        )
    except Exception as e:
        logger.error(f"Erro ao notificar medico {cliente_id}: {e}")
