"""
Orquestrador principal: processar_mensagem_completo e emissão de eventos.

Sprint 58 - Epic 2: Extraido de app/services/agente.py

Usa _pkg() para late-binding de nomes que os testes patcham via
``app.services.agente.<name>``.
"""

import sys
import logging
from typing import Optional, List

from app.core.tasks import safe_create_task
from app.services.policy import (
    PrimaryAction,
)

from .types import ProcessamentoResult

logger = logging.getLogger(__name__)


def _pkg():
    """Acessa o pacote pai para usar nomes que os testes patcham."""
    return sys.modules["app.services.agente"]


async def _emitir_offer_events(
    cliente_id: str,
    conversa_id: str,
    resposta: str,
    vagas_oferecidas: List[str] = None,
    policy_decision_id: Optional[str] = None,
) -> None:
    """
    Emite eventos de oferta (Sprint 17 - E04).

    Args:
        cliente_id: ID do cliente
        conversa_id: ID da conversa
        resposta: Texto da resposta gerada
        vagas_oferecidas: Lista de vaga_ids oferecidos (se houver)
        policy_decision_id: ID da decisão de policy
    """
    from app.services.business_events import (
        emit_event,
        should_emit_event,
        BusinessEvent,
        EventType,
        EventSource,
    )
    from app.services.business_events.context import tem_mencao_oportunidade
    from app.services.business_events.validators import vaga_pode_receber_oferta

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
                    emit_event(
                        BusinessEvent(
                            event_type=EventType.OFFER_MADE,
                            source=EventSource.BACKEND,
                            cliente_id=cliente_id,
                            conversation_id=conversa_id,
                            vaga_id=vaga_id,
                            policy_decision_id=policy_decision_id,
                            event_props={},
                        )
                    ),
                    name="emit_offer_made",
                )
                logger.debug(f"offer_made emitido para vaga {vaga_id[:8]}")

    # Se não tem vaga específica mas menciona oportunidades, emitir teaser
    elif resposta and tem_mencao_oportunidade(resposta):
        safe_create_task(
            emit_event(
                BusinessEvent(
                    event_type=EventType.OFFER_TEASER_SENT,
                    source=EventSource.BACKEND,
                    cliente_id=cliente_id,
                    conversation_id=conversa_id,
                    policy_decision_id=policy_decision_id,
                    event_props={
                        "resposta_length": len(resposta),
                    },
                )
            ),
            name="emit_offer_teaser_sent",
        )
        logger.debug(f"offer_teaser_sent emitido para cliente {cliente_id[:8]}")

    # Se resposta contém links do app, emitir app_download_sent
    from app.services.business_events.context import tem_link_app_revoluna

    if resposta and tem_link_app_revoluna(resposta):
        safe_create_task(
            emit_event(
                BusinessEvent(
                    event_type=EventType.APP_DOWNLOAD_SENT,
                    source=EventSource.BACKEND,
                    cliente_id=cliente_id,
                    conversation_id=conversa_id,
                    event_props={},
                    dedupe_key=f"app_download:{cliente_id}",  # 1 por médico
                )
            ),
            name="emit_app_download_sent",
        )
        logger.info(f"app_download_sent emitido para cliente {cliente_id[:8]}")


async def processar_mensagem_completo(
    mensagem_texto: str, medico: dict, conversa: dict, vagas: list[dict] = None
) -> ProcessamentoResult:
    """
    Processa mensagem completa com Policy Engine.

    Fluxo Sprint 15:
    1. Verificar controle (IA vs humano)
    2. Carregar contexto e doctor_state
    3. Detectar objeção (reutilizar detector existente)
    4. StateUpdate: atualizar estado
    5. PolicyDecide: decidir ação
    6. Se handoff -> transferir
    7. Se wait -> não responder
    8. Gerar resposta com constraints
    9. StateUpdate pós-envio

    Sprint 16 - E08: Retorna ProcessamentoResult com policy_decision_id.

    Args:
        mensagem_texto: Texto da mensagem do medico
        medico: Dados do medico
        conversa: Dados da conversa
        vagas: Vagas disponiveis (opcional)

    Returns:
        ProcessamentoResult com resposta e policy_decision_id
    """
    from app.services.contexto import montar_contexto_completo
    from app.services.handoff import criar_handoff

    pkg = _pkg()

    try:
        # 1. Verificar se conversa esta sob controle da IA
        if conversa.get("controlled_by") != "ai":
            logger.info("Conversa sob controle humano, nao processando")
            return ProcessamentoResult()

        # 2. Montar contexto (passa mensagem para busca RAG de memorias)
        contexto = await montar_contexto_completo(
            medico, conversa, vagas, mensagem_atual=mensagem_texto
        )

        # 2b. Carregar doctor_state
        state = await pkg.load_doctor_state(medico["id"])
        logger.debug(
            f"doctor_state carregado: {state.permission_state.value}, temp={state.temperature}"
        )

        # 3. Detectar objeção (REUTILIZAR detector do orquestrador)
        # Sprint 59 Epic 2.1: situacao será passado para gerar_resposta_julia
        objecao_dict = None
        situacao = None
        try:
            orquestrador = pkg.OrquestradorConhecimento()
            historico_msgs = []
            if contexto.get("historico_raw"):
                historico_msgs = [
                    m.get("conteudo", "")
                    for m in contexto["historico_raw"]
                    if m.get("tipo") == "recebida"
                ][-5:]

            situacao = await orquestrador.analisar_situacao(
                mensagem=mensagem_texto,
                historico=historico_msgs,
                dados_cliente=medico,
                stage=medico.get("stage_jornada", "novo"),
            )

            if situacao.objecao.tem_objecao:
                objecao_dict = {
                    "tem_objecao": True,
                    "tipo": situacao.objecao.tipo.value if situacao.objecao.tipo else "",
                    "subtipo": situacao.objecao.subtipo,
                    "confianca": situacao.objecao.confianca,
                }
                logger.debug(f"Objeção detectada: {objecao_dict}")
        except Exception as e:
            logger.warning(f"Erro ao detectar objeção: {e}")

        # 4. StateUpdate: atualizar estado
        # Sprint 59 Epic 2.2: Aplicar updates em memória ao invés de recarregar do DB
        state_updater = pkg.StateUpdate()
        inbound_updates = state_updater.on_inbound_message(state, mensagem_texto, objecao_dict)
        if inbound_updates:
            await pkg.save_doctor_state_updates(medico["id"], inbound_updates)
            # Aplicar updates no state em memória (evita 2o load_doctor_state)
            for key, value in inbound_updates.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            logger.debug(f"doctor_state atualizado in-memory: {list(inbound_updates.keys())}")

        # 5. PolicyDecide: decidir ação (Sprint 16: agora é async)
        policy = pkg.PolicyDecide()
        is_first_msg = contexto.get("primeira_msg", False)
        conversa_status = conversa.get("status", "active")
        decision = await policy.decide(
            state,
            is_first_message=is_first_msg,
            conversa_status=conversa_status,
            conversa_last_message_at=conversa.get("last_message_at"),
        )

        # 5b. Log estruturado da decisão (Sprint 15)
        # Retorna policy_decision_id para propagar ao handoff e effects
        policy_decision_id = pkg.log_policy_decision(
            state=state,
            decision=decision,
            conversation_id=conversa.get("id"),
            interaction_id=None,  # Será preenchido quando existir
            is_first_message=is_first_msg,
            conversa_status=conversa_status,
        )

        # 6. Se requer humano -> handoff
        if decision.requires_human:
            logger.warning(f"PolicyDecide: HANDOFF para {medico['id']} - {decision.reasoning}")
            try:
                await criar_handoff(
                    conversa_id=conversa["id"],
                    motivo=decision.reasoning,
                    trigger_type="policy_grave_objection",
                    policy_decision_id=policy_decision_id,
                )
                # Log effect: handoff triggered
                pkg.log_policy_effect(
                    cliente_id=medico["id"],
                    conversation_id=conversa.get("id"),
                    policy_decision_id=policy_decision_id,
                    rule_matched=decision.rule_id,
                    effect="handoff_triggered",
                    details={"motivo": decision.reasoning},
                )
            except Exception as e:
                logger.error(f"Erro ao criar handoff: {e}")
                pkg.log_policy_effect(
                    cliente_id=medico["id"],
                    conversation_id=conversa.get("id"),
                    policy_decision_id=policy_decision_id,
                    rule_matched=decision.rule_id,
                    effect="error",
                    details={"error": str(e), "action": "handoff"},
                )
            # Resposta padrão de transferência
            return ProcessamentoResult(
                resposta="Entendi. Vou pedir pra minha supervisora te ajudar aqui, um momento.",
                policy_decision_id=policy_decision_id,
                rule_matched=decision.rule_id,
            )

        # 7. Se ação é WAIT -> não responder
        if decision.primary_action == PrimaryAction.WAIT:
            logger.info(f"PolicyDecide: WAIT - {decision.reasoning}")
            # Log effect: wait applied
            pkg.log_policy_effect(
                cliente_id=medico["id"],
                conversation_id=conversa.get("id"),
                policy_decision_id=policy_decision_id,
                rule_matched=decision.rule_id,
                effect="wait_applied",
                details={"reasoning": decision.reasoning},
            )
            return ProcessamentoResult(
                policy_decision_id=policy_decision_id,
                rule_matched=decision.rule_id,
            )

        # 7b. Sprint 29: MODE ROUTER
        # Detecta intent, propõe transição, valida com micro-confirmação
        mode_router = pkg.get_mode_router()
        mode_info = await mode_router.process(
            conversa_id=conversa["id"],
            mensagem=mensagem_texto,
            last_message_at=conversa.get("last_message_at"),
            ponte_feita=False,  # TODO: detectar via tool call criar_handoff_externo
            objecao_resolvida=objecao_dict.get("resolvida", False) if objecao_dict else False,
        )
        logger.info(
            f"Mode Router: modo={mode_info.mode.value}, "
            f"pending={mode_info.pending_transition.value if mode_info.pending_transition else 'none'}"
        )

        # 7c. Sprint 29: CAPABILITIES GATE (3 camadas)
        capabilities_gate = pkg.CapabilitiesGate(mode_info.mode)

        # 8. Gerar resposta com constraints
        # Sprint 59 Epic 2.1: Passa situacao do orchestrator para evitar 2a chamada
        resposta = await pkg.gerar_resposta_julia(
            mensagem_texto,
            contexto,
            medico=medico,
            conversa=conversa,
            policy_decision=decision,
            capabilities_gate=capabilities_gate,  # Sprint 29
            mode_info=mode_info,  # Sprint 29
            situacao=situacao,  # Sprint 59: reutilizar analisar_situacao
        )

        # 8b. Emitir eventos de oferta se aplicável (Sprint 17 - E04)
        # Por ora, detectamos offers via menção no texto da resposta
        # TODO: Rastrear tool calls para offer_made com vaga_id específico
        if resposta:
            pkg.safe_create_task(
                _emitir_offer_events(
                    cliente_id=medico["id"],
                    conversa_id=conversa.get("id"),
                    resposta=resposta,
                    vagas_oferecidas=None,  # Será implementado quando rastrearmos tool calls
                    policy_decision_id=policy_decision_id,
                ),
                name="emitir_offer_events",
            )

        # 9. StateUpdate pós-envio + log effect
        if resposta:
            outbound_updates = state_updater.on_outbound_message(state, actor="julia")
            if outbound_updates:
                await pkg.save_doctor_state_updates(medico["id"], outbound_updates)
                logger.debug(f"doctor_state pós-envio: {list(outbound_updates.keys())}")

            # Log effect: message sent
            pkg.log_policy_effect(
                cliente_id=medico["id"],
                conversation_id=conversa.get("id"),
                policy_decision_id=policy_decision_id,
                rule_matched=decision.rule_id,
                effect="message_sent",
                details={
                    "primary_action": decision.primary_action.value,
                    "response_length": len(resposta),
                },
            )

        return ProcessamentoResult(
            resposta=resposta,
            policy_decision_id=policy_decision_id,
            rule_matched=decision.rule_id,
        )

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        return ProcessamentoResult()
