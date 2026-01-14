"""
Fluxo de transicao IA <-> Humano.

Sprint 10 - S10.E3.4
Sprint 17 - E04: handoff_created event
"""
from datetime import datetime
import logging
from typing import Optional

from app.core.tasks import safe_create_task
from app.services.supabase import supabase
from app.services.slack import notificar_handoff
from app.services.chatwoot import chatwoot_service
from app.services.interacao import salvar_interacao
from app.services.outbound import send_outbound_message
from app.services.guardrails import (
    OutboundContext,
    OutboundChannel,
    OutboundMethod,
    ActorType,
)
from .messages import obter_mensagem_transicao

logger = logging.getLogger(__name__)


async def iniciar_handoff(
    conversa_id: str,
    cliente_id: str,
    motivo: str,
    trigger_type: str = "manual",
    policy_decision_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Inicia processo de handoff (IA -> Humano).

    Args:
        conversa_id: ID da conversa
        cliente_id: ID do cliente
        motivo: Motivo do handoff
        trigger_type: Tipo do trigger (pedido_humano, juridico, etc)
        policy_decision_id: ID da decisão de policy que originou (Sprint 15)

    Returns:
        Dados do handoff criado ou None se erro
    """
    try:
        # Buscar conversa com dados do cliente
        conversa_response = (
            supabase.table("conversations")
            .select("*, clientes(*)")
            .eq("id", conversa_id)
            .single()
            .execute()
        )

        if not conversa_response.data:
            logger.error(f"Conversa {conversa_id} nao encontrada")
            return None

        conversa = conversa_response.data
        medico = conversa.get("clientes", {})
        telefone = medico.get("telefone")

        if not telefone:
            logger.error(f"Telefone nao encontrado para cliente {cliente_id}")
            return None

        # Calcular metadata
        metadata = await _calcular_metadata(conversa_id)

        # 1. Enviar mensagem de transicao
        await _enviar_mensagem_transicao(
            telefone, conversa_id, cliente_id, trigger_type, conversa
        )

        # 2. Atualizar conversa para controle humano
        supabase.table("conversations").update({
            "controlled_by": "human",
            "escalation_reason": motivo,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", conversa_id).execute()

        logger.info(f"Conversa {conversa_id} atualizada para controle humano")

        # 3. Criar registro de handoff
        handoff_data = {
            "conversa_id": conversa_id,
            "motivo": motivo,
            "trigger_type": trigger_type,
            "status": "pendente",
        }
        if metadata:
            handoff_data["metadata"] = metadata
        if policy_decision_id:
            handoff_data["policy_decision_id"] = policy_decision_id

        response = supabase.table("handoffs").insert(handoff_data).execute()

        if not response.data:
            logger.error("Erro ao criar registro de handoff")
            return None

        handoff = response.data[0]
        logger.info(f"Handoff criado: {handoff['id']}")

        # 4. Emitir evento handoff_created (Sprint 17 - E04)
        safe_create_task(
            _emitir_handoff_created(
                cliente_id=cliente_id,
                conversa_id=conversa_id,
                handoff_id=handoff["id"],
                motivo=motivo,
                trigger_type=trigger_type,
                policy_decision_id=policy_decision_id,
            ),
            name="emit_handoff_created"
        )

        # 5. Notificar gestor no Slack
        try:
            await notificar_handoff(conversa, handoff)
        except Exception as e:
            logger.error(f"Erro ao notificar Slack: {e}")

        return handoff

    except Exception as e:
        logger.error(f"Erro ao iniciar handoff: {e}", exc_info=True)
        return None


async def _calcular_metadata(conversa_id: str) -> dict:
    """Calcula metadata da conversa para o handoff."""
    interacoes_response = (
        supabase.table("interacoes")
        .select("*")
        .eq("conversation_id", conversa_id)
        .order("created_at", desc=False)
        .execute()
    )

    interacoes = interacoes_response.data or []
    metadata = {}

    if interacoes:
        metadata["ultima_mensagem"] = interacoes[-1].get("conteudo", "")[:200]
        metadata["total_interacoes"] = len(interacoes)

        primeira = datetime.fromisoformat(interacoes[0]["created_at"].replace("Z", "+00:00"))
        ultima = datetime.fromisoformat(interacoes[-1]["created_at"].replace("Z", "+00:00"))
        metadata["duracao_conversa_minutos"] = int((ultima - primeira).total_seconds() / 60)

    return metadata


async def _emitir_handoff_created(
    cliente_id: str,
    conversa_id: str,
    handoff_id: str,
    motivo: str,
    trigger_type: str,
    policy_decision_id: Optional[str] = None,
) -> None:
    """Emite evento handoff_created se no rollout (Sprint 17 - E04)."""
    try:
        from app.services.business_events import (
            emit_event,
            should_emit_event,
            BusinessEvent,
            EventType,
            EventSource,
        )

        # Verificar rollout
        should_emit = await should_emit_event(cliente_id, "handoff_created")
        if not should_emit:
            return

        await emit_event(BusinessEvent(
            event_type=EventType.HANDOFF_CREATED,
            source=EventSource.BACKEND,
            cliente_id=cliente_id,
            conversation_id=conversa_id,
            policy_decision_id=policy_decision_id,
            event_props={
                "handoff_id": handoff_id,
                "motivo": motivo,
                "trigger_type": trigger_type,
            },
        ))

        logger.debug(f"handoff_created emitido para cliente {cliente_id[:8]}")

    except Exception as e:
        logger.warning(f"Erro ao emitir handoff_created (nao critico): {e}")


async def _enviar_mensagem_transicao(
    telefone: str,
    conversa_id: str,
    cliente_id: str,
    trigger_type: str,
    conversa: dict
) -> None:
    """Envia mensagem de transicao e sincroniza com Chatwoot."""
    mensagem = obter_mensagem_transicao(trigger_type)

    try:
        # Sprint 18.1 P0: Usar wrapper com guardrails
        # Mensagem de handoff é resposta a conversa ativa, não proativa
        ctx = OutboundContext(
            cliente_id=cliente_id,
            actor_type=ActorType.BOT,
            channel=OutboundChannel.WHATSAPP,
            method=OutboundMethod.REPLY,  # É resposta a conversa ativa
            is_proactive=False,  # Médico está em conversa, não é proativo
            conversation_id=conversa_id,
        )
        result = await send_outbound_message(
            telefone=telefone,
            texto=mensagem,
            ctx=ctx,
            simular_digitacao=False,  # Handoff é urgente
        )

        if result.blocked:
            logger.warning(f"Mensagem de transicao bloqueada: {result.block_reason}")
            return

        if not result.success:
            logger.error(f"Erro ao enviar mensagem de transicao: {result.error}")
            return

        logger.info(f"Mensagem de transicao enviada para {telefone[:8]}...")

        await salvar_interacao(
            conversa_id=conversa_id,
            cliente_id=cliente_id,
            tipo="saida",
            conteudo=mensagem,
            autor_tipo="julia"
        )

        # Sincronizar com Chatwoot
        chatwoot_id = conversa.get("chatwoot_conversation_id")
        if chatwoot_id and chatwoot_service.configurado:
            await chatwoot_service.enviar_mensagem(
                conversation_id=int(chatwoot_id),
                content=mensagem,
                message_type="outgoing"
            )
            await chatwoot_service.adicionar_label(
                conversation_id=int(chatwoot_id),
                label="humano"
            )
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de transicao: {e}")


async def finalizar_handoff(
    conversa_id: str,
    notas: str = "Gestor removeu label 'humano' no Chatwoot",
    resolvido_por: str = "gestor"
) -> bool:
    """
    Finaliza handoff e retorna controle para IA.

    Args:
        conversa_id: ID da conversa
        notas: Observacoes sobre a resolucao
        resolvido_por: Quem resolveu

    Returns:
        True se sucesso
    """
    try:
        # 1. Buscar conversa
        conversa_response = (
            supabase.table("conversations")
            .select("*, clientes(*)")
            .eq("id", conversa_id)
            .single()
            .execute()
        )

        if not conversa_response.data:
            logger.error(f"Conversa {conversa_id} nao encontrada")
            return False

        conversa = conversa_response.data

        # 2. Atualizar conversa para controle IA
        supabase.table("conversations").update({
            "controlled_by": "ai",
            "escalation_reason": None,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", conversa_id).execute()

        logger.info(f"Conversa {conversa_id} retornada para controle IA")

        # 2.1 Remover label do Chatwoot
        chatwoot_id = conversa.get("chatwoot_conversation_id")
        if chatwoot_id and chatwoot_service.configurado:
            try:
                await chatwoot_service.remover_label(
                    conversation_id=int(chatwoot_id),
                    label="humano"
                )
            except Exception as e:
                logger.warning(f"Erro ao remover label do Chatwoot: {e}")

        # 3. Atualizar handoffs pendentes
        handoff_response = (
            supabase.table("handoffs")
            .update({
                "status": "resolvido",
                "resolvido_em": datetime.utcnow().isoformat(),
                "resolvido_por": resolvido_por,
                "notas": notas
            })
            .eq("conversa_id", conversa_id)
            .eq("status", "pendente")
            .execute()
        )

        # 4. Notificar Slack
        if handoff_response.data:
            handoff = handoff_response.data[0]
            logger.info(f"Handoff {handoff['id']} marcado como resolvido")

            try:
                from app.services.slack import notificar_handoff_resolvido
                await notificar_handoff_resolvido(conversa, handoff)
            except Exception as e:
                logger.error(f"Erro ao notificar Slack: {e}")

        return True

    except Exception as e:
        logger.error(f"Erro ao finalizar handoff: {e}", exc_info=True)
        return False


async def resolver_handoff(
    handoff_id: str,
    resolvido_por: Optional[str] = None,
    notas: Optional[str] = None
) -> Optional[dict]:
    """
    Marca handoff como resolvido.

    Args:
        handoff_id: ID do handoff
        resolvido_por: ID do usuario que resolveu
        notas: Notas sobre a resolucao

    Returns:
        Dados do handoff atualizado ou None
    """
    try:
        update_data = {
            "status": "resolvido",
            "resolvido_em": datetime.utcnow().isoformat()
        }

        if resolvido_por:
            update_data["resolvido_por"] = resolvido_por
        if notas:
            update_data["notas"] = notas

        response = (
            supabase.table("handoffs")
            .update(update_data)
            .eq("id", handoff_id)
            .execute()
        )

        if not response.data:
            logger.error(f"Handoff {handoff_id} nao encontrado")
            return None

        logger.info(f"Handoff {handoff_id} marcado como resolvido")
        return response.data[0]

    except Exception as e:
        logger.error(f"Erro ao resolver handoff: {e}", exc_info=True)
        return None
