"""
Geração de respostas da Julia (LLM + tool calling).

Sprint 58 - Epic 2: Extraido de app/services/agente.py

NOTA: Usa late-binding via _pkg() para nomes que os testes patcham em
``app.services.agente.<name>``.  Isso garante que ``patch("app.services.agente.gerar_resposta")``
afeta as chamadas feitas aqui, sem imports circulares.
"""

import asyncio
import sys
import logging
from typing import Optional

from app.services.policy import PolicyDecision
from app.services.conversation_mode import CapabilitiesGate, ModeInfo
from app.services.conversation_mode.prompts import get_micro_confirmation_prompt
from app.services.llm import LLMProvider

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

from .types import _resposta_parece_incompleta

logger = logging.getLogger(__name__)


def _pkg():
    """Acessa o pacote pai para usar nomes que os testes patcham."""
    return sys.modules["app.services.agente"]


# Tools disponíveis para o agente
JULIA_TOOLS = [
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
    TOOL_BUSCAR_INFO_HOSPITAL,
    TOOL_AGENDAR_LEMBRETE,
    TOOL_SALVAR_MEMORIA,
    TOOL_CRIAR_HANDOFF_EXTERNO,
    TOOL_REGISTRAR_STATUS_INTERMEDIACAO,
]


async def processar_tool_call(
    tool_name: str, tool_input: dict, medico: dict, conversa: dict
) -> dict:
    """Processa chamada de tool e retorna resultado."""
    logger.info(f"Processando tool: {tool_name}")

    handlers = {
        "buscar_vagas": handle_buscar_vagas,
        "reservar_plantao": handle_reservar_plantao,
        "agendar_lembrete": handle_agendar_lembrete,
        "buscar_info_hospital": handle_buscar_info_hospital,
        "salvar_memoria": handle_salvar_memoria,
        "criar_handoff_externo": handle_criar_handoff_externo,
        "registrar_status_intermediacao": handle_registrar_status_intermediacao,
    }

    handler = handlers.get(tool_name)
    if handler:
        return await handler(tool_input, medico, conversa)
    return {"success": False, "error": f"Tool desconhecida: {tool_name}"}


async def _executar_tool_calls(tool_calls: list, medico: dict, conversa: dict) -> list[dict]:
    """Executa lista de tool calls e retorna tool_results formatados."""
    tool_results = []
    for tc in tool_calls:
        result = await processar_tool_call(tc["name"], tc["input"], medico, conversa)
        tool_results.append(
            {
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": str(result),
            }
        )
    return tool_results


def _montar_assistant_content(text: Optional[str], tool_calls: list) -> list[dict]:
    """Monta bloco de content do assistant com texto e tool_use."""
    content = []
    if text:
        content.append({"type": "text", "text": text})
    for tc in tool_calls:
        content.append(
            {
                "type": "tool_use",
                "id": tc["id"],
                "name": tc["name"],
                "input": tc["input"],
            }
        )
    return content


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
    llm_provider: LLMProvider = None,
    situacao=None,
) -> str:
    """
    Gera resposta da Julia para uma mensagem.

    Sprint 44 T02.1: Wrapper com timeout global.
    Sprint 44 T02.2: Validação de resposta com guardrails.
    Sprint 44 T06.4: Cache de respostas LLM.
    """
    from app.services.conversation_mode.response_validator import (
        validar_resposta_julia as validar_resposta,
        get_fallback_response,
    )
    from app.services.llm.cache import get_cached_response, cache_response

    if not usar_tools:
        cached = await get_cached_response(mensagem, contexto)
        if cached:
            logger.debug(f"[Cache] Usando resposta cacheada para: {mensagem[:50]}...")
            return cached

    pkg = _pkg()

    try:
        resposta = await asyncio.wait_for(
            pkg._gerar_resposta_julia_impl(
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
                situacao=situacao,
            ),
            timeout=pkg.TIMEOUT_GERACAO_RESPOSTA,
        )

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

        if not usar_tools:
            await cache_response(mensagem, contexto, resposta)

        return resposta

    except asyncio.TimeoutError:
        logger.error(
            f"Timeout ao gerar resposta ({pkg.TIMEOUT_GERACAO_RESPOSTA}s) "
            f"para mensagem: {mensagem[:50]}..."
        )
        return pkg.RESPOSTA_TIMEOUT_FALLBACK


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
    situacao=None,
) -> str:
    """Implementação interna da geração de resposta (sem timeout wrapper)."""
    pkg = _pkg()

    # E03: Detectar situação e buscar conhecimento relevante
    # Sprint 59 Epic 2.1: Reutilizar situacao do orchestrator se já disponível
    conhecimento_dinamico = ""
    if situacao is not None:
        conhecimento_dinamico = situacao.resumo
        logger.debug(
            f"Situação reutilizada do orchestrator: objecao={situacao.objecao.tipo}, "
            f"perfil={situacao.perfil.perfil}, objetivo={situacao.objetivo.objetivo}"
        )
    else:
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
                mensagem=mensagem,
                historico=historico_msgs,
                dados_cliente=medico,
                stage=medico.get("stage_jornada", "novo"),
            )
            conhecimento_dinamico = situacao.resumo
            logger.debug(
                f"Situação detectada: objecao={situacao.objecao.tipo}, "
                f"perfil={situacao.perfil.perfil}, objetivo={situacao.objetivo.objetivo}"
            )
        except Exception as e:
            logger.warning(f"Erro ao buscar conhecimento dinâmico: {e}")

    # Montar constraints combinados (Policy Engine + Conversation Mode)
    constraints_parts = []
    if policy_decision and policy_decision.constraints_text:
        constraints_parts.append(policy_decision.constraints_text)

    if capabilities_gate:
        mode_constraints = capabilities_gate.get_constraints_text()
        if mode_constraints:
            constraints_parts.append(mode_constraints)
        logger.debug(
            f"Capabilities Gate aplicado: modo={capabilities_gate.mode.value}, "
            f"claims_proibidos={len(capabilities_gate.get_forbidden_claims())}"
        )

    if mode_info and mode_info.pending_transition:
        micro_prompt = get_micro_confirmation_prompt(mode_info.mode, mode_info.pending_transition)
        if micro_prompt:
            constraints_parts.append(micro_prompt)
            logger.debug(
                f"Micro-confirmação injetada: {mode_info.mode.value} -> {mode_info.pending_transition.value}"
            )

    campanha = contexto.get("campanha")
    if campanha and campanha.get("pode_ofertar") is False:
        constraints_parts.append(
            "RESTRIÇÃO DE CAMPANHA (PRIORIDADE MÁXIMA): Esta conversa NÃO permite ofertar vagas. "
            "Se o médico perguntar sobre vagas, diga que vai verificar o que tem disponível e retorna. "
            "NÃO mencione vagas específicas, valores, datas ou hospitais."
        )

    policy_constraints = "\n\n---\n\n".join(constraints_parts) if constraints_parts else ""

    system_prompt = await pkg.montar_prompt_julia(
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
        campaign_type=campanha.get("campaign_type") if campanha else None,
        campaign_objective=campanha.get("campaign_objective") if campanha else None,
        campaign_rules=campanha.get("campaign_rules") if campanha else None,
        offer_scope=campanha.get("offer_scope") if campanha else None,
        negotiation_margin=campanha.get("negotiation_margin") if campanha else None,
    )

    historico_messages = []
    if incluir_historico and contexto.get("historico_raw"):
        historico_messages = pkg.converter_historico_para_messages(contexto["historico_raw"])

    logger.info(f"Gerando resposta para: {mensagem[:50]}...")

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

    if usar_tools:
        resposta = await _gerar_com_tools(
            pkg,
            mensagem,
            historico_messages,
            system_prompt,
            tools_to_use,
            medico,
            conversa,
        )
    else:
        resposta = await pkg.gerar_resposta(
            mensagem=mensagem,
            historico=historico_messages,
            system_prompt=system_prompt,
            max_tokens=300,
        )

    logger.info(f"Resposta gerada: {resposta[:50]}...")

    # Detectar resposta incompleta e forçar uso de tool
    houve_tool_use = usar_tools and "resultado_inicial" not in locals()
    stop_reason = None
    if usar_tools and not houve_tool_use and _resposta_parece_incompleta(resposta, stop_reason):
        resposta = await _retry_com_tool(
            pkg,
            resposta,
            mensagem,
            historico_messages,
            system_prompt,
            tools_to_use,
            medico,
            conversa,
        )

    return resposta


async def _gerar_com_tools(
    pkg,
    mensagem,
    historico_messages,
    system_prompt,
    tools_to_use,
    medico,
    conversa,
) -> str:
    """Gera resposta usando tools, com loop de tool calls sequenciais."""
    resultado = await pkg.gerar_resposta_com_tools(
        mensagem=mensagem,
        historico=historico_messages,
        system_prompt=system_prompt,
        tools=tools_to_use,
        max_tokens=300,
    )

    if not resultado["tool_use"]:
        return resultado["text"] or ""

    logger.info(f"Tool call detectada: {resultado['tool_use']}")
    tool_results = await _executar_tool_calls(resultado["tool_use"], medico, conversa)
    assistant_content = _montar_assistant_content(resultado["text"], resultado["tool_use"])

    current_historico = historico_messages + [
        {"role": "user", "content": mensagem},
        {"role": "assistant", "content": assistant_content},
    ]
    current_tool_results = tool_results

    resultado_final = await pkg.continuar_apos_tool(
        historico=current_historico,
        tool_results=tool_results,
        system_prompt=system_prompt,
        tools=tools_to_use,
        max_tokens=300,
    )

    # Loop de tool calls sequenciais (max 3 iterações)
    for iteration in range(3):
        if not resultado_final.get("tool_use"):
            break
        logger.info(f"Tool call sequencial {iteration + 1}: {resultado_final['tool_use']}")

        new_tool_results = await _executar_tool_calls(resultado_final["tool_use"], medico, conversa)
        new_content = _montar_assistant_content(
            resultado_final.get("text"), resultado_final["tool_use"]
        )

        current_historico = current_historico + [
            {"role": "user", "content": current_tool_results},
            {"role": "assistant", "content": new_content},
        ]
        current_tool_results = new_tool_results

        resultado_final = await pkg.continuar_apos_tool(
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
        historico_forcar = current_historico + [
            {"role": "user", "content": current_tool_results},
            {"role": "user", "content": "Agora responda ao médico de forma natural e curta."},
        ]
        resultado_forcado = await pkg.gerar_resposta(
            mensagem="",
            historico=historico_forcar,
            system_prompt=system_prompt,
            max_tokens=150,
        )
        resposta = resultado_forcado or ""

    return resposta


async def _retry_com_tool(
    pkg,
    resposta,
    mensagem,
    historico_messages,
    system_prompt,
    tools_to_use,
    medico,
    conversa,
) -> str:
    """Retry quando resposta parece incompleta - força uso de tool."""
    logger.warning(
        f"Resposta incompleta detectada, forçando uso de tool. Resposta: '{resposta[-50:]}'"
    )

    historico_retry = historico_messages + [
        {"role": "user", "content": mensagem},
        {"role": "assistant", "content": resposta},
        {
            "role": "user",
            "content": (
                "Use a ferramenta buscar_vagas para encontrar as vagas disponíveis "
                "e depois responda ao médico com as opções."
            ),
        },
    ]

    resultado_retry = await pkg.gerar_resposta_com_tools(
        mensagem="",
        historico=historico_retry,
        system_prompt=system_prompt,
        tools=tools_to_use,
        max_tokens=300,
    )

    if resultado_retry.get("tool_use"):
        logger.info(f"Retry com tool call: {resultado_retry['tool_use']}")
        tool_results_retry = await _executar_tool_calls(
            resultado_retry["tool_use"], medico, conversa
        )
        assistant_content_retry = _montar_assistant_content(
            resultado_retry["text"], resultado_retry["tool_use"]
        )

        historico_com_tool_retry = historico_retry + [
            {"role": "assistant", "content": assistant_content_retry}
        ]

        resultado_final_retry = await pkg.continuar_apos_tool(
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
        resposta = resultado_retry["text"]
        logger.info(f"Retry sem tool, texto: {resposta[:50]}...")

    return resposta
