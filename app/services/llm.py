"""
Cliente Anthropic para geracao de respostas via Claude.
"""
import anthropic
from functools import lru_cache
import logging

from app.core.config import settings

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
    """
    modelo = modelo or settings.LLM_MODEL

    # Montar mensagens
    messages = []
    if historico:
        messages.extend(historico)
    messages.append({"role": "user", "content": mensagem})

    # Chamar API
    response = client.messages.create(
        model=modelo,
        max_tokens=max_tokens,
        system=system_prompt or "",
        messages=messages,
    )

    # Extrair texto
    return response.content[0].text


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
