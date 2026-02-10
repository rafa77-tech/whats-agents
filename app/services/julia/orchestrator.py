"""
Julia Orchestrator - Orquestra geração de resposta.

Sprint 31 - S31.E2.5
Sprint 44 - T02.3: Integração com Summarizer

Esta é a função principal refatorada, com < 100 linhas.
Delega para componentes especializados.
"""

import logging
from typing import Optional, Dict, Any, List

from app.services.llm import (
    LLMProvider,
    gerar_resposta,
    gerar_resposta_com_tools,
    continuar_apos_tool,
)
from app.services.policy import PolicyDecision
from app.services.conversation_mode import CapabilitiesGate, ModeInfo

from .context_builder import get_context_builder
from .tool_executor import get_tool_executor, get_julia_tools
from .response_handler import get_response_handler

logger = logging.getLogger(__name__)

# Limite de iterações para tool calls sequenciais
MAX_TOOL_ITERATIONS = 3


async def gerar_resposta_julia_v2(
    mensagem: str,
    contexto: Dict[str, Any],
    medico: Dict[str, Any],
    conversa: Dict[str, Any],
    incluir_historico: bool = True,
    usar_tools: bool = True,
    policy_decision: Optional[PolicyDecision] = None,
    capabilities_gate: Optional[CapabilitiesGate] = None,
    mode_info: Optional[ModeInfo] = None,
    llm_provider: Optional[LLMProvider] = None,
) -> str:
    """
    Gera resposta da Julia para uma mensagem (versão refatorada).

    Esta versão usa componentes decompostos para melhor testabilidade.

    Args:
        mensagem: Mensagem do médico
        contexto: Contexto montado
        medico: Dados do médico
        conversa: Dados da conversa
        incluir_historico: Se deve passar histórico
        usar_tools: Se deve usar tools
        policy_decision: Decisão da Policy Engine
        capabilities_gate: Gate de capabilities
        mode_info: Info do modo atual
        llm_provider: Provider de LLM (para testes)

    Returns:
        Texto da resposta gerada
    """
    context_builder = get_context_builder()
    tool_executor = get_tool_executor()
    response_handler = get_response_handler()

    # 1. Buscar conhecimento dinâmico
    conhecimento = await context_builder.buscar_conhecimento_dinamico(
        mensagem=mensagem,
        historico_raw=contexto.get("historico_raw", []),
        medico=medico,
    )

    # 2. Montar constraints
    constraints = context_builder.montar_constraints(policy_decision, capabilities_gate, mode_info)

    # 4. Montar histórico com summarization (Sprint 44 T02.3)
    historico_raw = contexto.get("historico_raw", [])
    history, resumo_conversa = await context_builder.converter_historico_com_summarization(
        historico_raw,
        conversa_id=conversa.get("id"),
        incluir=incluir_historico,
    )

    # 3. Montar system prompt (após summarization para incluir resumo)
    # Se houve summarization, adicionar resumo ao conhecimento
    conhecimento_com_resumo = conhecimento
    if resumo_conversa:
        conhecimento_com_resumo = (
            f"{conhecimento}\n\n### Contexto da conversa anterior:\n{resumo_conversa}"
            if conhecimento
            else f"### Contexto da conversa anterior:\n{resumo_conversa}"
        )

    system_prompt = await context_builder.montar_system_prompt(
        contexto=contexto,
        medico=medico,
        conhecimento_dinamico=conhecimento_com_resumo,
        policy_constraints=constraints,
    )

    # 5. Filtrar tools
    tools = context_builder.filtrar_tools(get_julia_tools(), capabilities_gate)

    logger.info(f"Gerando resposta para: {mensagem[:50]}...")

    # 6. Gerar sem tools (caminho simples)
    if not usar_tools:
        return await gerar_resposta(
            mensagem=mensagem,
            historico=history,
            system_prompt=system_prompt,
            max_tokens=300,
        )

    # 7. Gerar com tools
    resultado = await gerar_resposta_com_tools(
        mensagem=mensagem,
        historico=history,
        system_prompt=system_prompt,
        tools=tools,
        max_tokens=300,
    )

    # 8. Processar tool calls
    resposta = resultado.get("text", "")
    houve_tool_use = False

    if resultado.get("tool_use"):
        houve_tool_use = True
        resposta = await _processar_tool_loop(
            resultado=resultado,
            history=history,
            mensagem=mensagem,
            system_prompt=system_prompt,
            tools=tools,
            medico=medico,
            conversa=conversa,
            tool_executor=tool_executor,
        )

    # 9. Verificar resposta incompleta
    if (
        usar_tools
        and not houve_tool_use
        and response_handler.resposta_incompleta(resposta, resultado.get("stop_reason"))
    ):
        logger.warning(f"Resposta incompleta detectada: '{resposta[-50:]}'")
        resposta = await _tentar_retry_com_tool(
            resposta_original=resposta,
            history=history,
            mensagem=mensagem,
            system_prompt=system_prompt,
            tools=tools,
            medico=medico,
            conversa=conversa,
            tool_executor=tool_executor,
            response_handler=response_handler,
        )

    logger.info(f"Resposta gerada: {resposta[:50]}...")
    return resposta


async def _processar_tool_loop(
    resultado: Dict,
    history: List[Dict],
    mensagem: str,
    system_prompt: str,
    tools: List[Dict],
    medico: Dict,
    conversa: Dict,
    tool_executor,
) -> str:
    """Processa loop de tool calls."""
    current_result = resultado
    current_history = history + [{"role": "user", "content": mensagem}]
    iteration = 0

    while current_result.get("tool_use") and iteration < MAX_TOOL_ITERATIONS:
        iteration += 1
        tool_calls = current_result["tool_use"]
        logger.info(f"Tool call iteração {iteration}: {[t['name'] for t in tool_calls]}")

        # Executar tools
        exec_results = await tool_executor.process_tool_calls(tool_calls, medico, conversa)
        tool_results = tool_executor.format_results_for_api(exec_results)

        # Montar conteúdo do assistant
        assistant_content = tool_executor.build_assistant_content(
            current_result.get("text"), tool_calls
        )

        # Atualizar histórico
        current_history = current_history + [
            {"role": "assistant", "content": assistant_content},
        ]

        # Continuar geração
        current_result = await continuar_apos_tool(
            historico=current_history,
            tool_results=tool_results,
            system_prompt=system_prompt,
            tools=tools,
            max_tokens=300,
        )

    return current_result.get("text", "")


async def _tentar_retry_com_tool(
    resposta_original: str,
    history: List[Dict],
    mensagem: str,
    system_prompt: str,
    tools: List[Dict],
    medico: Dict,
    conversa: Dict,
    tool_executor,
    response_handler,
) -> str:
    """Tenta retry forçando uso de tool."""
    historico_retry = history + [
        {"role": "user", "content": mensagem},
        {"role": "assistant", "content": resposta_original},
        {"role": "user", "content": response_handler.montar_prompt_retry()},
    ]

    resultado_retry = await gerar_resposta_com_tools(
        mensagem="",
        historico=historico_retry,
        system_prompt=system_prompt,
        tools=tools,
        max_tokens=300,
    )

    if resultado_retry.get("tool_use"):
        resposta = await _processar_tool_loop(
            resultado=resultado_retry,
            history=historico_retry,
            mensagem="",
            system_prompt=system_prompt,
            tools=tools,
            medico=medico,
            conversa=conversa,
            tool_executor=tool_executor,
        )
        if resposta:
            logger.info(f"Resposta recuperada após retry: {resposta[:50]}...")
            return resposta

    if resultado_retry.get("text"):
        return resultado_retry["text"]

    return resposta_original
