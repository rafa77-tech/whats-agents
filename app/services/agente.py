"""
Servico principal do agente Julia.

Sprint 15: Integração com Policy Engine para decisões determinísticas.
"""
import asyncio
import random
import logging
from typing import Optional

from app.core.prompts import montar_prompt_julia
from app.services.llm import gerar_resposta, gerar_resposta_com_tools, continuar_apos_tool
from app.services.interacao import converter_historico_para_messages
from app.services.mensagem import quebrar_mensagem
from app.services.whatsapp import enviar_com_digitacao
from app.tools.vagas import (
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
    TOOL_BUSCAR_INFO_HOSPITAL,
    handle_buscar_vagas,
    handle_reservar_plantao,
    handle_buscar_info_hospital,
)
from app.tools.lembrete import TOOL_AGENDAR_LEMBRETE, handle_agendar_lembrete
from app.tools.memoria import TOOL_SALVAR_MEMORIA, handle_salvar_memoria
from app.services.conhecimento import OrquestradorConhecimento
from app.services.policy import (
    PolicyDecide,
    StateUpdate,
    load_doctor_state,
    save_doctor_state_updates,
    PrimaryAction,
    PolicyDecision,
    log_policy_decision,
    log_policy_effect,
)

logger = logging.getLogger(__name__)

# Tools disponiveis para o agente
JULIA_TOOLS = [
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
    TOOL_BUSCAR_INFO_HOSPITAL,
    TOOL_AGENDAR_LEMBRETE,
    TOOL_SALVAR_MEMORIA,
]


async def processar_tool_call(
    tool_name: str,
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict:
    """
    Processa chamada de tool.

    Args:
        tool_name: Nome da tool
        tool_input: Input da tool
        medico: Dados do medico
        conversa: Dados da conversa

    Returns:
        Resultado da tool
    """
    logger.info(f"Processando tool: {tool_name}")

    if tool_name == "buscar_vagas":
        return await handle_buscar_vagas(tool_input, medico, conversa)

    if tool_name == "reservar_plantao":
        return await handle_reservar_plantao(tool_input, medico, conversa)

    if tool_name == "agendar_lembrete":
        return await handle_agendar_lembrete(tool_input, medico, conversa)

    if tool_name == "buscar_info_hospital":
        return await handle_buscar_info_hospital(tool_input, medico, conversa)

    if tool_name == "salvar_memoria":
        return await handle_salvar_memoria(tool_input, medico, conversa)

    return {"success": False, "error": f"Tool desconhecida: {tool_name}"}


async def gerar_resposta_julia(
    mensagem: str,
    contexto: dict,
    medico: dict,
    conversa: dict,
    incluir_historico: bool = True,
    usar_tools: bool = True,
    policy_decision: PolicyDecision = None,
) -> str:
    """
    Gera resposta da Julia para uma mensagem.

    Args:
        mensagem: Mensagem do medico
        contexto: Contexto montado (medico, historico, vagas, etc)
        medico: Dados do medico
        conversa: Dados da conversa
        incluir_historico: Se deve passar historico como messages
        usar_tools: Se deve usar tools
        policy_decision: Decisão da Policy Engine (Sprint 15)

    Returns:
        Texto da resposta gerada
    """
    # E03: Detectar situação e buscar conhecimento relevante
    conhecimento_dinamico = ""
    try:
        orquestrador = OrquestradorConhecimento()
        historico_msgs = []
        if contexto.get("historico_raw"):
            historico_msgs = [
                m.get("conteudo", "") for m in contexto["historico_raw"]
                if m.get("tipo") == "recebida"
            ][-5:]  # Últimas 5 mensagens recebidas

        situacao = await orquestrador.analisar_situacao(
            mensagem=mensagem,
            historico=historico_msgs,
            dados_cliente=medico,
            stage=medico.get("stage_jornada", "novo"),
        )
        conhecimento_dinamico = situacao.resumo
        logger.debug(f"Situação detectada: objecao={situacao.objecao.tipo}, perfil={situacao.perfil.perfil}, objetivo={situacao.objetivo.objetivo}")
    except Exception as e:
        logger.warning(f"Erro ao buscar conhecimento dinâmico: {e}")
        # Continua sem conhecimento dinâmico

    # Extrair constraints da policy (Sprint 15)
    policy_constraints = ""
    if policy_decision and policy_decision.constraints_text:
        policy_constraints = policy_decision.constraints_text

    # Montar system prompt (async - carrega do banco)
    system_prompt = await montar_prompt_julia(
        contexto_medico=contexto.get("medico", ""),
        contexto_vagas=contexto.get("vagas", ""),
        historico=contexto.get("historico", ""),
        primeira_msg=contexto.get("primeira_msg", False),
        data_hora_atual=contexto.get("data_hora_atual", ""),
        dia_semana=contexto.get("dia_semana", ""),
        contexto_especialidade=contexto.get("especialidade", ""),
        contexto_handoff=contexto.get("handoff_recente", ""),
        contexto_memorias=contexto.get("memorias", ""),
        especialidade_id=medico.get("especialidade_id"),
        diretrizes=contexto.get("diretrizes", ""),
        conhecimento=conhecimento_dinamico,
        policy_constraints=policy_constraints,
    )

    # Montar historico como messages (para o Claude ter contexto da conversa)
    historico_messages = []
    if incluir_historico and contexto.get("historico_raw"):
        historico_messages = converter_historico_para_messages(
            contexto["historico_raw"]
        )

    logger.info(f"Gerando resposta para: {mensagem[:50]}...")

    # Gerar resposta com tools
    if usar_tools:
        resultado = await gerar_resposta_com_tools(
            mensagem=mensagem,
            historico=historico_messages,
            system_prompt=system_prompt,
            tools=JULIA_TOOLS,
            max_tokens=300,
        )

        # Processar tool calls se houver
        if resultado["tool_use"]:
            logger.info(f"Tool call detectada: {resultado['tool_use']}")

            # Processar cada tool
            tool_results = []
            for tool_call in resultado["tool_use"]:
                tool_result = await processar_tool_call(
                    tool_name=tool_call["name"],
                    tool_input=tool_call["input"],
                    medico=medico,
                    conversa=conversa
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call["id"],
                    "content": str(tool_result)
                })

            # Continuar conversa apos tool
            # Montar historico com a mensagem do assistant que chamou tool
            assistant_content = []
            if resultado["text"]:
                assistant_content.append({"type": "text", "text": resultado["text"]})
            for tool_call in resultado["tool_use"]:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "input": tool_call["input"]
                })

            historico_com_tool = historico_messages + [
                {"role": "user", "content": mensagem},
                {"role": "assistant", "content": assistant_content}
            ]

            resultado_final = await continuar_apos_tool(
                historico=historico_com_tool,
                tool_results=tool_results,
                system_prompt=system_prompt,
                tools=JULIA_TOOLS,
                max_tokens=300,
            )

            resposta = resultado_final["text"] or ""

            # Failsafe: se chamou tool mas não gerou resposta, forçar
            if not resposta and tool_results:
                logger.warning("Tool executada mas sem resposta, forçando geração")
                # Adicionar tool_result e pedir resposta
                historico_forcar = historico_com_tool + [
                    {"role": "user", "content": tool_results},
                    {"role": "user", "content": "Agora responda ao médico de forma natural e curta."}
                ]
                resultado_forcado = await gerar_resposta(
                    mensagem="",
                    historico=historico_forcar,
                    system_prompt=system_prompt,
                    max_tokens=150,
                )
                resposta = resultado_forcado or ""
        else:
            resposta = resultado["text"] or ""
    else:
        # Gerar sem tools
        resposta = await gerar_resposta(
            mensagem=mensagem,
            historico=historico_messages,
            system_prompt=system_prompt,
            max_tokens=300,
        )

    logger.info(f"Resposta gerada: {resposta[:50]}...")

    return resposta


async def processar_mensagem_completo(
    mensagem_texto: str,
    medico: dict,
    conversa: dict,
    vagas: list[dict] = None
) -> Optional[str]:
    """
    Processa mensagem completa com Policy Engine.

    Fluxo Sprint 15:
    1. Verificar controle (IA vs humano)
    2. Carregar contexto e doctor_state
    3. Detectar objeção (reutilizar detector existente)
    4. StateUpdate: atualizar estado
    5. PolicyDecide: decidir ação
    6. Se handoff → transferir
    7. Se wait → não responder
    8. Gerar resposta com constraints
    9. StateUpdate pós-envio

    Args:
        mensagem_texto: Texto da mensagem do medico
        medico: Dados do medico
        conversa: Dados da conversa
        vagas: Vagas disponiveis (opcional)

    Returns:
        Texto da resposta ou None se erro/não deve responder
    """
    from app.services.contexto import montar_contexto_completo
    from app.services.handoff import criar_handoff

    try:
        # 1. Verificar se conversa esta sob controle da IA
        if conversa.get("controlled_by") != "ai":
            logger.info("Conversa sob controle humano, nao processando")
            return None

        # 2. Montar contexto (passa mensagem para busca RAG de memorias)
        contexto = await montar_contexto_completo(
            medico, conversa, vagas, mensagem_atual=mensagem_texto
        )

        # 2b. Carregar doctor_state
        state = await load_doctor_state(medico["id"])
        logger.debug(f"doctor_state carregado: {state.permission_state.value}, temp={state.temperature}")

        # 3. Detectar objeção (REUTILIZAR detector do orquestrador)
        objecao_dict = None
        try:
            orquestrador = OrquestradorConhecimento()
            historico_msgs = []
            if contexto.get("historico_raw"):
                historico_msgs = [
                    m.get("conteudo", "") for m in contexto["historico_raw"]
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
        state_updater = StateUpdate()
        inbound_updates = state_updater.on_inbound_message(
            state, mensagem_texto, objecao_dict
        )
        if inbound_updates:
            await save_doctor_state_updates(medico["id"], inbound_updates)
            logger.debug(f"doctor_state atualizado: {list(inbound_updates.keys())}")

        # Recarregar state atualizado
        state = await load_doctor_state(medico["id"])

        # 5. PolicyDecide: decidir ação
        policy = PolicyDecide()
        is_first_msg = contexto.get("primeira_msg", False)
        conversa_status = conversa.get("status", "active")
        decision = policy.decide(
            state,
            is_first_message=is_first_msg,
            conversa_status=conversa_status,
            conversa_last_message_at=conversa.get("last_message_at"),
        )

        # 5b. Log estruturado da decisão (Sprint 15)
        # Retorna policy_decision_id para propagar ao handoff e effects
        policy_decision_id = log_policy_decision(
            state=state,
            decision=decision,
            conversation_id=conversa.get("id"),
            interaction_id=None,  # Será preenchido quando existir
            is_first_message=is_first_msg,
            conversa_status=conversa_status,
        )

        # 6. Se requer humano → handoff
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
                log_policy_effect(
                    cliente_id=medico["id"],
                    conversation_id=conversa.get("id"),
                    policy_decision_id=policy_decision_id,
                    rule_matched=decision.rule_id,
                    effect="handoff_triggered",
                    details={"motivo": decision.reasoning},
                )
            except Exception as e:
                logger.error(f"Erro ao criar handoff: {e}")
                log_policy_effect(
                    cliente_id=medico["id"],
                    conversation_id=conversa.get("id"),
                    policy_decision_id=policy_decision_id,
                    rule_matched=decision.rule_id,
                    effect="error",
                    details={"error": str(e), "action": "handoff"},
                )
            # Resposta padrão de transferência
            return "Entendi. Vou pedir pra minha supervisora te ajudar aqui, um momento."

        # 7. Se ação é WAIT → não responder
        if decision.primary_action == PrimaryAction.WAIT:
            logger.info(f"PolicyDecide: WAIT - {decision.reasoning}")
            # Log effect: wait applied
            log_policy_effect(
                cliente_id=medico["id"],
                conversation_id=conversa.get("id"),
                policy_decision_id=policy_decision_id,
                rule_matched=decision.rule_id,
                effect="wait_applied",
                details={"reasoning": decision.reasoning},
            )
            return None

        # 8. Gerar resposta com constraints
        resposta = await gerar_resposta_julia(
            mensagem_texto,
            contexto,
            medico=medico,
            conversa=conversa,
            policy_decision=decision,
        )

        # 9. StateUpdate pós-envio + log effect
        if resposta:
            outbound_updates = state_updater.on_outbound_message(state, actor="julia")
            if outbound_updates:
                await save_doctor_state_updates(medico["id"], outbound_updates)
                logger.debug(f"doctor_state pós-envio: {list(outbound_updates.keys())}")

            # Log effect: message sent
            log_policy_effect(
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

        return resposta

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        return None


async def enviar_mensagens_sequencia(
    telefone: str,
    mensagens: list[str]
) -> list[dict]:
    """
    Envia sequência de mensagens com timing natural.

    Entre mensagens:
    - Delay curto (1-3s) para continuação
    - Delay médio (3-5s) para novo pensamento

    Args:
        telefone: Número do destinatário
        mensagens: Lista de mensagens a enviar

    Returns:
        Lista de resultados do envio
    """
    resultados = []

    for i, msg in enumerate(mensagens):
        # Calcular delay entre mensagens
        if i > 0:
            # Se começa com minúscula, é continuação (delay curto)
            if msg and msg[0].islower():
                delay = random.uniform(1, 3)
            else:
                delay = random.uniform(3, 5)

            await asyncio.sleep(delay)

        # Enviar com digitação
        resultado = await enviar_com_digitacao(
            telefone=telefone,
            texto=msg
        )
        resultados.append(resultado)

    return resultados


async def enviar_resposta(
    telefone: str,
    resposta: str
) -> dict:
    """
    Envia resposta com timing humanizado.
    Quebra mensagens longas em sequência se necessário.

    Args:
        telefone: Número do destinatário
        resposta: Texto da resposta

    Returns:
        Resultado do envio (ou primeiro resultado se múltiplas mensagens)
    """
    # Quebrar resposta se necessário
    mensagens = quebrar_mensagem(resposta)

    if len(mensagens) == 1:
        return await enviar_com_digitacao(telefone, resposta)
    else:
        resultados = await enviar_mensagens_sequencia(telefone, mensagens)
        return resultados[0] if resultados else {}
