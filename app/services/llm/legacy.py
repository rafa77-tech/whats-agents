"""
Cliente Anthropic para geracao de respostas via Claude.
"""
import anthropic
import asyncio
from functools import lru_cache
import logging
from typing import Any

from app.core.config import settings
from app.services.circuit_breaker import circuit_claude, CircuitOpenError

logger = logging.getLogger(__name__)


@lru_cache()
def get_anthropic_client() -> anthropic.Anthropic:
    """
    Retorna cliente Anthropic cacheado.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY e obrigatorio")

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# Instancia global
client = get_anthropic_client()


async def gerar_resposta(
    mensagem: str,
    historico: list[dict] | None = None,
    system_prompt: str | None = None,
    modelo: str | None = None,
    max_tokens: int = 500,
) -> str:
    """
    Gera resposta usando Claude.

    Args:
        mensagem: Mensagem do usuario
        historico: Lista de mensagens anteriores [{"role": "user/assistant", "content": "..."}]
        system_prompt: Prompt de sistema (persona)
        modelo: Modelo a usar (default: Haiku)
        max_tokens: Maximo de tokens na resposta

    Returns:
        Texto da resposta gerada

    Raises:
        CircuitOpenError: Se Claude API está indisponível
    """
    modelo = modelo or settings.LLM_MODEL

    # Montar mensagens
    messages = []
    if historico:
        messages.extend(historico)
    messages.append({"role": "user", "content": mensagem})

    # Função para chamar API (síncrona, será executada via run_in_executor)
    def _chamar_api():
        return client.messages.create(
            model=modelo,
            max_tokens=max_tokens,
            system=system_prompt or "",
            messages=messages,
        )

    # Wrapper async para o circuit breaker
    async def _chamar_api_async():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _chamar_api)

    # Chamar API com circuit breaker
    response = await circuit_claude.executar(_chamar_api_async)

    # Extrair texto
    return response.content[0].text


async def gerar_resposta_com_tools(
    mensagem: str,
    historico: list[dict] | None = None,
    system_prompt: str | None = None,
    tools: list[dict] | None = None,
    modelo: str | None = None,
    max_tokens: int = 500,
) -> dict[str, Any]:
    """
    Gera resposta usando Claude com suporte a tools.

    Args:
        mensagem: Mensagem do usuario
        historico: Lista de mensagens anteriores
        system_prompt: Prompt de sistema
        tools: Lista de tools disponiveis
        modelo: Modelo a usar
        max_tokens: Maximo de tokens

    Returns:
        Dict com:
        - text: Texto da resposta (se houver)
        - tool_use: Lista de tool calls (se houver)
        - stop_reason: Motivo de parada (end_turn, tool_use)

    Raises:
        CircuitOpenError: Se Claude API está indisponível
    """
    modelo = modelo or settings.LLM_MODEL

    # Montar mensagens
    messages = []
    if historico:
        messages.extend(historico)
    messages.append({"role": "user", "content": mensagem})

    # Preparar kwargs
    kwargs = {
        "model": modelo,
        "max_tokens": max_tokens,
        "system": system_prompt or "",
        "messages": messages,
    }

    if tools:
        kwargs["tools"] = tools

    # Função para chamar API
    def _chamar_api():
        return client.messages.create(**kwargs)

    # Wrapper async para o circuit breaker
    async def _chamar_api_async():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _chamar_api)

    # Chamar API com circuit breaker
    response = await circuit_claude.executar(_chamar_api_async)

    # Processar resposta
    result = {
        "text": None,
        "tool_use": [],
        "stop_reason": response.stop_reason
    }

    for block in response.content:
        if block.type == "text":
            result["text"] = block.text
        elif block.type == "tool_use":
            result["tool_use"].append({
                "id": block.id,
                "name": block.name,
                "input": block.input
            })

    return result


async def continuar_apos_tool(
    historico: list[dict],
    tool_results: list[dict],
    system_prompt: str | None = None,
    tools: list[dict] | None = None,
    modelo: str | None = None,
    max_tokens: int = 500,
) -> dict[str, Any]:
    """
    Continua conversa apos execucao de tool.

    Args:
        historico: Historico incluindo a mensagem do assistant com tool_use
        tool_results: Lista de resultados das tools
        system_prompt: Prompt de sistema
        tools: Lista de tools
        modelo: Modelo a usar
        max_tokens: Maximo de tokens

    Returns:
        Dict igual ao gerar_resposta_com_tools

    Raises:
        CircuitOpenError: Se Claude API está indisponível
    """
    modelo = modelo or settings.LLM_MODEL

    # Adicionar resultados das tools
    messages = historico.copy()
    messages.append({
        "role": "user",
        "content": tool_results
    })

    kwargs = {
        "model": modelo,
        "max_tokens": max_tokens,
        "system": system_prompt or "",
        "messages": messages,
    }

    if tools:
        kwargs["tools"] = tools

    # Função para chamar API
    def _chamar_api():
        return client.messages.create(**kwargs)

    # Wrapper async para o circuit breaker
    async def _chamar_api_async():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _chamar_api)

    # Chamar API com circuit breaker
    response = await circuit_claude.executar(_chamar_api_async)

    # Processar resposta
    result = {
        "text": None,
        "tool_use": [],
        "stop_reason": response.stop_reason
    }

    for block in response.content:
        if block.type == "text":
            result["text"] = block.text
        elif block.type == "tool_use":
            result["tool_use"].append({
                "id": block.id,
                "name": block.name,
                "input": block.input
            })

    return result


async def gerar_resposta_complexa(
    mensagem: str,
    historico: list[dict] | None = None,
    system_prompt: str | None = None,
) -> str:
    """
    Gera resposta usando modelo mais capaz (Sonnet).
    Usar para situacoes que exigem mais raciocinio.
    """
    return await gerar_resposta(
        mensagem=mensagem,
        historico=historico,
        system_prompt=system_prompt,
        modelo=settings.LLM_MODEL_COMPLEX,
        max_tokens=1000,
    )
