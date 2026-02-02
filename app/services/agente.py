"""
Servico principal do agente Julia.

Sprint 15: Integração com Policy Engine para decisões determinísticas.
Sprint 16: Retorna policy_decision_id para fechamento do ciclo.
Sprint 17: Emissão de eventos offer_made, offer_teaser_sent (E04).
Sprint 29: Conversation Mode + Capabilities Gate (3 camadas de proteção).
Sprint 44: T02.1 - Global timeout para geração de resposta.

GUARDRAIL CRÍTICO: Julia é INTERMEDIÁRIA
- Não negocia valores
- Não confirma reservas
- Conecta médico com responsável da vaga
"""
import asyncio
import random
import logging
from dataclasses import dataclass, field
from typing import Optional, List

from app.core.tasks import safe_create_task
from app.core.prompts import montar_prompt_julia
# Sprint 31: LLM Provider abstraction
from app.services.llm import (
    # New interface
    LLMProvider,
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    ToolCall,
    ToolDefinition,
    ToolResult,
    get_llm_provider,
    # Legacy (backward compatibility)
    gerar_resposta,
    gerar_resposta_com_tools,
    continuar_apos_tool,
)
from app.services.interacao import converter_historico_para_messages
from app.services.mensagem import quebrar_mensagem
from app.services.outbound import send_outbound_message, OutboundResult
from app.services.guardrails import OutboundContext
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
from app.tools.intermediacao import (
    TOOL_CRIAR_HANDOFF_EXTERNO,
    TOOL_REGISTRAR_STATUS_INTERMEDIACAO,
    handle_criar_handoff_externo,
    handle_registrar_status_intermediacao,
)
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
# Sprint 29: Conversation Mode
from app.services.conversation_mode import (
    get_mode_router,
    CapabilitiesGate,
    ConversationMode,
    ModeInfo,
    get_conversation_mode,
)
from app.services.conversation_mode.prompts import get_micro_confirmation_prompt

logger = logging.getLogger(__name__)

# Sprint 44 T02.1: Timeout global para geração de resposta
# Evita loops infinitos no tool calling e garante resposta em tempo finito
# Sprint 44 T02.6: Usar configuração centralizada
from app.core.config import settings
TIMEOUT_GERACAO_RESPOSTA = settings.LLM_LOOP_TIMEOUT_SEGUNDOS
RESPOSTA_TIMEOUT_FALLBACK = "Desculpa, tive um probleminha aqui. Pode repetir?"

# Padrões que indicam resposta incompleta (mesma lógica do Slack)
PADROES_RESPOSTA_INCOMPLETA = [
    ":",           # "Vou verificar o que temos:"
    "...",         # Reticências no final
    "vou verificar",
    "deixa eu ver",
    "um momento",
    "vou buscar",
    "vou checar",
    "deixa eu buscar",
]
MAX_RETRIES_INCOMPLETO = 2


def _resposta_parece_incompleta(texto: str, stop_reason: str = None) -> bool:
    """
    Detecta se resposta parece incompleta e deveria ter chamado uma tool.

    Args:
        texto: Texto da resposta
        stop_reason: Motivo de parada do LLM (tool_use, end_turn, etc)

    Returns:
        True se resposta parece incompleta
    """
    if not texto:
        return False

    # Se parou por tool_use, não é incompleta (a tool vai ser executada)
    if stop_reason == "tool_use":
        return False

    texto_lower = texto.lower().strip()

    for padrao in PADROES_RESPOSTA_INCOMPLETA:
        if texto_lower.endswith(padrao):
            logger.warning(
                f"Resposta parece incompleta: termina com '{padrao}' "
                f"(stop_reason={stop_reason})"
            )
            return True

    return False


# Tools disponiveis para o agente
JULIA_TOOLS = [
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
    TOOL_BUSCAR_INFO_HOSPITAL,
    TOOL_AGENDAR_LEMBRETE,
    TOOL_SALVAR_MEMORIA,
    # Sprint 29: Tools de intermediacao
    TOOL_CRIAR_HANDOFF_EXTERNO,
    TOOL_REGISTRAR_STATUS_INTERMEDIACAO,
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

    # Sprint 29: Tools de intermediacao
    if tool_name == "criar_handoff_externo":
        return await handle_criar_handoff_externo(tool_input, medico, conversa)

    if tool_name == "registrar_status_intermediacao":
        return await handle_registrar_status_intermediacao(tool_input, medico, conversa)

    return {"success": False, "error": f"Tool desconhecida: {tool_name}"}


async def gerar_resposta_julia(
    mensagem: str,
    contexto: dict,
    medico: dict,
    conversa: dict,
    incluir_historico: bool = True,
    usar_tools: bool = True,
    policy_decision: PolicyDecision = None,
    capabilities_gate: CapabilitiesGate = None,
    mode_info: ModeInfo = None,
    llm_provider: LLMProvider = None,  # Sprint 31: Optional LLM provider
) -> str:
    """
    Gera resposta da Julia para uma mensagem.

    Sprint 44 T02.1: Wrapper com timeout global para evitar loops infinitos.
    Sprint 44 T02.2: Validação de resposta com guardrails.
    Sprint 44 T06.4: Cache de respostas LLM.

    Args:
        mensagem: Mensagem do medico
        contexto: Contexto montado (medico, historico, vagas, etc)
        medico: Dados do medico
        conversa: Dados da conversa
        incluir_historico: Se deve passar historico como messages
        usar_tools: Se deve usar tools
        policy_decision: Decisão da Policy Engine (Sprint 15)
        capabilities_gate: Gate de capabilities por modo (Sprint 29)
        mode_info: Info do modo atual (Sprint 29)
        llm_provider: LLM provider para geração (Sprint 31)
            Se None, usa funções legadas para backward compatibility.
            Passar provider para usar nova interface (recomendado em testes).

    Returns:
        Texto da resposta gerada
    """
    # Sprint 44 T02.2: Import do response validator
    from app.services.conversation_mode.response_validator import (
        validar_resposta_julia as validar_resposta,
        get_fallback_response,
    )
    # Sprint 44 T06.4: Import do cache LLM
    from app.services.llm.cache import get_cached_response, cache_response

    # Sprint 44 T06.4: Verificar cache antes de chamar LLM
    # Só usa cache se não estiver usando tools (respostas com tools são dinâmicas)
    if not usar_tools:
        cached = await get_cached_response(mensagem, contexto)
        if cached:
            logger.debug(f"[Cache] Usando resposta cacheada para: {mensagem[:50]}...")
            return cached

    try:
        resposta = await asyncio.wait_for(
            _gerar_resposta_julia_impl(
                mensagem=mensagem,
                contexto=contexto,
                medico=medico,
                conversa=conversa,
                incluir_historico=incluir_historico,
                usar_tools=usar_tools,
                policy_decision=policy_decision,
                capabilities_gate=capabilities_gate,
                mode_info=mode_info,
                llm_provider=llm_provider,
            ),
            timeout=TIMEOUT_GERACAO_RESPOSTA
        )

        # Sprint 44 T02.2: Validar resposta antes de retornar
        conversation_mode = mode_info.mode.value if mode_info else "unknown"
        conversa_id = conversa.get("id") if conversa else None

        valida, violacao = validar_resposta(
            resposta=resposta,
            mode=conversation_mode,
            conversa_id=conversa_id,
        )

        if not valida:
            logger.warning(
                f"Resposta violou guardrail '{violacao}' em modo {conversation_mode}, "
                f"usando fallback. Conversa: {conversa_id}"
            )
            return get_fallback_response(violacao)

        # Sprint 44 T06.4: Cachear resposta válida (se não usou tools)
        if not usar_tools:
            await cache_response(mensagem, contexto, resposta)

        return resposta

    except asyncio.TimeoutError:
        logger.error(
            f"Timeout ao gerar resposta ({TIMEOUT_GERACAO_RESPOSTA}s) "
            f"para mensagem: {mensagem[:50]}..."
        )
        return RESPOSTA_TIMEOUT_FALLBACK


async def _gerar_resposta_julia_impl(
    mensagem: str,
    contexto: dict,
    medico: dict,
    conversa: dict,
    incluir_historico: bool = True,
    usar_tools: bool = True,
    policy_decision: PolicyDecision = None,
    capabilities_gate: CapabilitiesGate = None,
    mode_info: ModeInfo = None,
    llm_provider: LLMProvider = None,
) -> str:
    """
    Implementação interna da geração de resposta.

    Sprint 44 T02.1: Separada para permitir timeout no wrapper.
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

    # Montar constraints combinados (Policy Engine + Conversation Mode)
    constraints_parts = []

    # Constraints da Policy Engine (Sprint 15)
    if policy_decision and policy_decision.constraints_text:
        constraints_parts.append(policy_decision.constraints_text)

    # Sprint 29: Constraints do Conversation Mode (3 CAMADAS)
    if capabilities_gate:
        mode_constraints = capabilities_gate.get_constraints_text()
        if mode_constraints:
            constraints_parts.append(mode_constraints)
        logger.debug(
            f"Capabilities Gate aplicado: modo={capabilities_gate.mode.value}, "
            f"claims_proibidos={len(capabilities_gate.get_forbidden_claims())}"
        )

    # Sprint 29: Prompt de micro-confirmação se há pending_transition
    if mode_info and mode_info.pending_transition:
        micro_prompt = get_micro_confirmation_prompt(
            mode_info.mode, mode_info.pending_transition
        )
        if micro_prompt:
            constraints_parts.append(micro_prompt)
            logger.debug(
                f"Micro-confirmação injetada: {mode_info.mode.value} → {mode_info.pending_transition.value}"
            )

    # Combinar todos os constraints
    policy_constraints = "\n\n---\n\n".join(constraints_parts) if constraints_parts else ""

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

    # Sprint 29: Filtrar tools pelo modo (CAMADA 1)
    if capabilities_gate:
        tools_to_use = capabilities_gate.filter_tools(JULIA_TOOLS)
        removed_count = len(JULIA_TOOLS) - len(tools_to_use)
        if removed_count > 0:
            logger.info(
                f"Tools filtradas pelo modo {capabilities_gate.mode.value}: "
                f"{removed_count} removidas de {len(JULIA_TOOLS)}"
            )
    else:
        tools_to_use = JULIA_TOOLS

    # Gerar resposta com tools
    if usar_tools:
        resultado = await gerar_resposta_com_tools(
            mensagem=mensagem,
            historico=historico_messages,
            system_prompt=system_prompt,
            tools=tools_to_use,
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
                tools=tools_to_use,  # Sprint 29: usar tools filtradas
                max_tokens=300,
            )

            # Sprint 29: Suporte a múltiplas tool calls sequenciais
            # Limite de 3 iterações para evitar loops infinitos
            max_tool_iterations = 3
            current_iteration = 0
            current_historico = historico_com_tool
            current_tool_results = tool_results

            while resultado_final.get("tool_use") and current_iteration < max_tool_iterations:
                current_iteration += 1
                logger.info(f"Tool call sequencial {current_iteration}: {resultado_final['tool_use']}")

                # Processar nova tool call
                new_tool_results = []
                for tool_call in resultado_final["tool_use"]:
                    tool_result = await processar_tool_call(
                        tool_name=tool_call["name"],
                        tool_input=tool_call["input"],
                        medico=medico,
                        conversa=conversa
                    )
                    new_tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call["id"],
                        "content": str(tool_result)
                    })

                # Montar novo histórico
                new_assistant_content = []
                if resultado_final.get("text"):
                    new_assistant_content.append({"type": "text", "text": resultado_final["text"]})
                for tool_call in resultado_final["tool_use"]:
                    new_assistant_content.append({
                        "type": "tool_use",
                        "id": tool_call["id"],
                        "name": tool_call["name"],
                        "input": tool_call["input"]
                    })

                current_historico = current_historico + [
                    {"role": "user", "content": current_tool_results},
                    {"role": "assistant", "content": new_assistant_content}
                ]
                current_tool_results = new_tool_results

                # Continuar após nova tool
                resultado_final = await continuar_apos_tool(
                    historico=current_historico,
                    tool_results=new_tool_results,
                    system_prompt=system_prompt,
                    tools=tools_to_use,
                    max_tokens=300,
                )

            resposta = resultado_final.get("text") or ""

            # Failsafe: se chamou tool mas não gerou resposta, forçar
            if not resposta and (tool_results or current_tool_results):
                logger.warning("Tool executada mas sem resposta, forçando geração")
                # Adicionar tool_result e pedir resposta
                historico_forcar = current_historico + [
                    {"role": "user", "content": current_tool_results},
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

    # Detectar resposta incompleta e forçar uso de tool
    # Só aplica quando usar_tools=True e não houve tool_use
    houve_tool_use = usar_tools and "resultado" in locals() and resultado.get("tool_use")
    stop_reason = resultado.get("stop_reason") if usar_tools and "resultado" in locals() else None
    if (
        usar_tools
        and not houve_tool_use
        and _resposta_parece_incompleta(resposta, stop_reason)
    ):
        logger.warning(
            f"Resposta incompleta detectada, forçando uso de tool. "
            f"Resposta: '{resposta[-50:]}'"
        )

        # Forçar continuação com prompt de uso de tool
        historico_retry = historico_messages + [
            {"role": "user", "content": mensagem},
            {"role": "assistant", "content": resposta},
            {
                "role": "user",
                "content": (
                    "Use a ferramenta buscar_vagas para encontrar as vagas disponíveis "
                    "e depois responda ao médico com as opções."
                )
            },
        ]

        resultado_retry = await gerar_resposta_com_tools(
            mensagem="",
            historico=historico_retry,
            system_prompt=system_prompt,
            tools=tools_to_use,
            max_tokens=300,
        )

        # Processar tool call do retry
        if resultado_retry.get("tool_use"):
            logger.info(f"Retry com tool call: {resultado_retry['tool_use']}")
            tool_results_retry = []
            for tool_call in resultado_retry["tool_use"]:
                tool_result = await processar_tool_call(
                    tool_name=tool_call["name"],
                    tool_input=tool_call["input"],
                    medico=medico,
                    conversa=conversa
                )
                tool_results_retry.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call["id"],
                    "content": str(tool_result)
                })

            # Montar histórico com tool call
            assistant_content_retry = []
            if resultado_retry["text"]:
                assistant_content_retry.append({
                    "type": "text", "text": resultado_retry["text"]
                })
            for tool_call in resultado_retry["tool_use"]:
                assistant_content_retry.append({
                    "type": "tool_use",
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "input": tool_call["input"]
                })

            historico_com_tool_retry = historico_retry + [
                {"role": "assistant", "content": assistant_content_retry}
            ]

            resultado_final_retry = await continuar_apos_tool(
                historico=historico_com_tool_retry,
                tool_results=tool_results_retry,
                system_prompt=system_prompt,
                tools=tools_to_use,
                max_tokens=300,
            )

            if resultado_final_retry.get("text"):
                resposta = resultado_final_retry["text"]
                logger.info(f"Resposta após retry: {resposta[:50]}...")
        elif resultado_retry.get("text"):
            # Retry gerou texto sem tool, usar mesmo assim
            resposta = resultado_retry["text"]
            logger.info(f"Retry sem tool, texto: {resposta[:50]}...")

    return resposta


@dataclass
class ProcessamentoResult:
    """Resultado do processamento de mensagem (Sprint 16)."""
    resposta: Optional[str] = None
    policy_decision_id: Optional[str] = None
    rule_matched: Optional[str] = None


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


async def processar_mensagem_completo(
    mensagem_texto: str,
    medico: dict,
    conversa: dict,
    vagas: list[dict] = None
) -> ProcessamentoResult:
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

        # 5. PolicyDecide: decidir ação (Sprint 16: agora é async)
        policy = PolicyDecide()
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
            return ProcessamentoResult(
                resposta="Entendi. Vou pedir pra minha supervisora te ajudar aqui, um momento.",
                policy_decision_id=policy_decision_id,
                rule_matched=decision.rule_id,
            )

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
            return ProcessamentoResult(
                policy_decision_id=policy_decision_id,
                rule_matched=decision.rule_id,
            )

        # 7b. Sprint 29: MODE ROUTER
        # Detecta intent, propõe transição, valida com micro-confirmação
        mode_router = get_mode_router()
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
        capabilities_gate = CapabilitiesGate(mode_info.mode)

        # 8. Gerar resposta com constraints
        resposta = await gerar_resposta_julia(
            mensagem_texto,
            contexto,
            medico=medico,
            conversa=conversa,
            policy_decision=decision,
            capabilities_gate=capabilities_gate,  # Sprint 29
            mode_info=mode_info,  # Sprint 29
        )

        # 8b. Emitir eventos de oferta se aplicável (Sprint 17 - E04)
        # Por ora, detectamos offers via menção no texto da resposta
        # TODO: Rastrear tool calls para offer_made com vaga_id específico
        if resposta:
            safe_create_task(
                _emitir_offer_events(
                    cliente_id=medico["id"],
                    conversa_id=conversa.get("id"),
                    resposta=resposta,
                    vagas_oferecidas=None,  # Será implementado quando rastrearmos tool calls
                    policy_decision_id=policy_decision_id,
                ),
                name="emitir_offer_events"
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

        return ProcessamentoResult(
            resposta=resposta,
            policy_decision_id=policy_decision_id,
            rule_matched=decision.rule_id,
        )

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        return ProcessamentoResult()


async def _emitir_fallback_event(telefone: str, function_name: str) -> None:
    """
    Emite evento quando fallback legado é usado.

    Sprint 18.1 P0: Fallback barulhento para auditoria.
    """
    try:
        from app.services.business_events import (
            emit_event,
            BusinessEvent,
            EventType,
            EventSource,
        )

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


async def enviar_mensagens_sequencia(
    telefone: str,
    mensagens: list[str],
    ctx: Optional[OutboundContext] = None,
) -> list[OutboundResult]:
    """
    Envia sequência de mensagens com timing natural.

    Entre mensagens:
    - Delay curto (1-3s) para continuação
    - Delay médio (3-5s) para novo pensamento

    Args:
        telefone: Número do destinatário
        mensagens: Lista de mensagens a enviar
        ctx: Contexto do guardrail (obrigatório para novos usos)

    Returns:
        Lista de resultados do envio (OutboundResult se ctx, dict se legado)

    Sprint 18.1 P0: Agora usa send_outbound_message quando ctx fornecido.
    """
    if ctx is None:
        # BARULHENTO: Log estruturado + evento
        logger.warning(
            "GUARDRAIL_BYPASS: enviar_mensagens_sequencia chamado sem ctx",
            extra={
                "event": "outbound_fallback_used",
                "telefone_prefix": telefone[:8] if telefone else "unknown",
                "mensagens_count": len(mensagens),
            }
        )
        # Emitir evento para auditoria
        safe_create_task(
            _emitir_fallback_event(telefone, "enviar_mensagens_sequencia"),
            name="fallback_event_sequencia"
        )

    resultados = []

    for i, msg in enumerate(mensagens):
        # Calcular delay entre mensagens (Sprint 29: reduzido para agilidade)
        if i > 0:
            # Se começa com minúscula, é continuação (delay curto)
            if msg and msg[0].islower():
                delay = random.uniform(0.5, 1.5)  # Reduzido de 1-3s
            else:
                delay = random.uniform(1, 2)  # Reduzido de 3-5s

            await asyncio.sleep(delay)

        # Enviar com guardrail (se ctx) ou legado
        if ctx:
            resultado = await send_outbound_message(
                telefone=telefone,
                texto=msg,
                ctx=ctx,
                simular_digitacao=True,
            )
            if resultado.blocked or not resultado.success:
                logger.warning(f"Mensagem bloqueada/falhou na sequência: {resultado}")
                resultados.append(resultado)
                break  # Para sequência se bloqueado
        else:
            # Fallback legado - TODO: remover quando todos call sites migrarem
            from app.services.whatsapp import enviar_com_digitacao
            resultado = await enviar_com_digitacao(
                telefone=telefone,
                texto=msg
            )
        resultados.append(resultado)

    return resultados


async def enviar_resposta(
    telefone: str,
    resposta: str,
    ctx: Optional[OutboundContext] = None,
) -> OutboundResult:
    """
    Envia resposta com timing humanizado.
    Quebra mensagens longas em sequência se necessário.

    Args:
        telefone: Número do destinatário
        resposta: Texto da resposta
        ctx: Contexto do guardrail (obrigatório para novos usos)

    Returns:
        Resultado do envio (OutboundResult se ctx, dict se legado)

    Sprint 18.1 P0: Agora usa send_outbound_message quando ctx fornecido.
    """
    if ctx is None:
        # BARULHENTO: Log estruturado + evento
        logger.warning(
            "GUARDRAIL_BYPASS: enviar_resposta chamado sem ctx",
            extra={
                "event": "outbound_fallback_used",
                "telefone_prefix": telefone[:8] if telefone else "unknown",
                "resposta_length": len(resposta) if resposta else 0,
            }
        )
        # Emitir evento para auditoria
        safe_create_task(
            _emitir_fallback_event(telefone, "enviar_resposta"),
            name="fallback_event_resposta"
        )

    # Quebrar resposta se necessário
    mensagens = quebrar_mensagem(resposta)

    if len(mensagens) == 1:
        if ctx:
            return await send_outbound_message(
                telefone=telefone,
                texto=resposta,
                ctx=ctx,
                simular_digitacao=True,
            )
        else:
            # Fallback legado
            from app.services.whatsapp import enviar_com_digitacao
            return await enviar_com_digitacao(telefone, resposta)
    else:
        resultados = await enviar_mensagens_sequencia(telefone, mensagens, ctx)
        return resultados[0] if resultados else OutboundResult(success=False, error="Sem resultado")
