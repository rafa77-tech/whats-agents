"""
Servico principal do agente Julia.
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
from app.tools.vagas import TOOL_RESERVAR_PLANTAO, handle_reservar_plantao
from app.tools.lembrete import TOOL_AGENDAR_LEMBRETE, handle_agendar_lembrete

logger = logging.getLogger(__name__)

# Tools disponiveis para o agente
JULIA_TOOLS = [
    TOOL_RESERVAR_PLANTAO,
    TOOL_AGENDAR_LEMBRETE,
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

    if tool_name == "reservar_plantao":
        return await handle_reservar_plantao(tool_input, medico, conversa)

    if tool_name == "agendar_lembrete":
        return await handle_agendar_lembrete(tool_input, medico, conversa)

    return {"success": False, "error": f"Tool desconhecida: {tool_name}"}


async def gerar_resposta_julia(
    mensagem: str,
    contexto: dict,
    medico: dict,
    conversa: dict,
    incluir_historico: bool = True,
    usar_tools: bool = True
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

    Returns:
        Texto da resposta gerada
    """
    # Montar system prompt
    system_prompt = montar_prompt_julia(
        contexto_medico=contexto.get("medico", ""),
        contexto_vagas=contexto.get("vagas", ""),
        historico=contexto.get("historico", ""),
        primeira_msg=contexto.get("primeira_msg", False),
        data_hora_atual=contexto.get("data_hora_atual", ""),
        dia_semana=contexto.get("dia_semana", ""),
        contexto_especialidade=contexto.get("especialidade", "")
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
    Processa mensagem completa: monta contexto e gera resposta.

    Args:
        mensagem_texto: Texto da mensagem do medico
        medico: Dados do medico
        conversa: Dados da conversa
        vagas: Vagas disponiveis (opcional)

    Returns:
        Texto da resposta ou None se erro
    """
    from app.services.contexto import montar_contexto_completo

    try:
        # Verificar se conversa esta sob controle da IA
        if conversa.get("controlled_by") != "ai":
            logger.info("Conversa sob controle humano, nao processando")
            return None

        # Montar contexto
        contexto = await montar_contexto_completo(medico, conversa, vagas)

        # Gerar resposta
        resposta = await gerar_resposta_julia(
            mensagem_texto,
            contexto,
            medico=medico,
            conversa=conversa
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
