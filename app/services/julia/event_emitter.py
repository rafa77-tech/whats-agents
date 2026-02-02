"""
Event Emitter - Emissão de business events do agente Julia.

Sprint 44 T02.4: Componente separado para emissão de eventos.

Responsabilidades:
- Emitir eventos de oferta (offer_made, offer_teaser_sent)
- Emitir eventos de fallback outbound
- Centralizar lógica de emissão de eventos do agente
"""
import logging
from typing import Optional, List

from app.core.tasks import safe_create_task
from app.services.business_events import (
    emit_event,
    should_emit_event,
    BusinessEvent,
    EventType,
    EventSource,
)
from app.services.business_events.context import tem_mencao_oportunidade
from app.services.business_events.validators import vaga_pode_receber_oferta

logger = logging.getLogger(__name__)


async def emitir_offer_events(
    cliente_id: str,
    conversa_id: str,
    resposta: str,
    vagas_oferecidas: Optional[List[str]] = None,
    policy_decision_id: Optional[str] = None,
) -> None:
    """
    Emite eventos de oferta (Sprint 17 - E04).

    Se tem vagas específicas oferecidas, emite offer_made para cada.
    Se não tem vaga mas menciona oportunidades, emite offer_teaser_sent.

    Args:
        cliente_id: ID do cliente
        conversa_id: ID da conversa
        resposta: Texto da resposta gerada
        vagas_oferecidas: Lista de vaga_ids oferecidos (se houver)
        policy_decision_id: ID da decisão de policy
    """
    # Verificar rollout
    should_emit = await should_emit_event(cliente_id, "offer_events")
    if not should_emit:
        return

    # Se tem vagas específicas oferecidas, emitir offer_made para cada
    if vagas_oferecidas:
        for vaga_id in vagas_oferecidas:
            # Trava de segurança: só emite se vaga estiver aberta/anunciada
            if await vaga_pode_receber_oferta(vaga_id):
                safe_create_task(
                    emit_event(BusinessEvent(
                        event_type=EventType.OFFER_MADE,
                        source=EventSource.BACKEND,
                        cliente_id=cliente_id,
                        conversation_id=conversa_id,
                        vaga_id=vaga_id,
                        policy_decision_id=policy_decision_id,
                        event_props={},
                    )),
                    name="emit_offer_made"
                )
                logger.debug(f"offer_made emitido para vaga {vaga_id[:8]}")

    # Se não tem vaga específica mas menciona oportunidades, emitir teaser
    elif resposta and tem_mencao_oportunidade(resposta):
        safe_create_task(
            emit_event(BusinessEvent(
                event_type=EventType.OFFER_TEASER_SENT,
                source=EventSource.BACKEND,
                cliente_id=cliente_id,
                conversation_id=conversa_id,
                policy_decision_id=policy_decision_id,
                event_props={
                    "resposta_length": len(resposta),
                },
            )),
            name="emit_offer_teaser_sent"
        )
        logger.debug(f"offer_teaser_sent emitido para cliente {cliente_id[:8]}")


async def emitir_fallback_event(telefone: str, function_name: str) -> None:
    """
    Emite evento quando fallback legado é usado.

    Sprint 18.1 P0: Fallback barulhento para auditoria.

    Args:
        telefone: Telefone do destinatário
        function_name: Nome da função que usou fallback
    """
    try:
        # Criar evento de fallback
        await emit_event(BusinessEvent(
            event_type=EventType.OUTBOUND_FALLBACK,
            source=EventSource.BACKEND,
            cliente_id=None,  # Não temos o ID no fallback legado
            event_props={
                "function": function_name,
                "telefone_prefix": telefone[:8] if telefone else "unknown",
                "warning": "Fallback legado usado - migrar para OutboundContext",
            },
        ))
        logger.debug(f"outbound_fallback emitido para {function_name}")
    except Exception as e:
        # Se EventType.OUTBOUND_FALLBACK não existir, apenas log
        logger.warning(f"Erro ao emitir outbound_fallback (não crítico): {e}")


async def emitir_policy_effect_event(
    cliente_id: str,
    conversa_id: Optional[str],
    policy_decision_id: str,
    effect: str,
    rule_matched: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """
    Emite evento de efeito de policy aplicado.

    Args:
        cliente_id: ID do cliente
        conversa_id: ID da conversa
        policy_decision_id: ID da decisão de policy
        effect: Tipo de efeito (message_sent, wait_applied, handoff_triggered)
        rule_matched: ID da regra que deu match
        details: Detalhes adicionais
    """
    from app.services.policy import log_policy_effect

    log_policy_effect(
        cliente_id=cliente_id,
        conversation_id=conversa_id,
        policy_decision_id=policy_decision_id,
        rule_matched=rule_matched,
        effect=effect,
        details=details or {},
    )
