"""
Cliente LLM para classificação de mensagens de grupos.

Sprint 14 - E04 - S04.2
"""

import json
import re
import hashlib
from dataclasses import dataclass
from typing import Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings, GruposConfig
from app.core.logging import get_logger
from app.services.redis import cache_get, cache_set
from app.services.grupos.prompts import PROMPT_CLASSIFICACAO

logger = get_logger(__name__)


# =============================================================================
# S04.5 - Cache Redis
# =============================================================================

CACHE_TTL = GruposConfig.CACHE_TTL_CLASSIFICACAO
CACHE_PREFIX = "grupo:classificacao:"


def _hash_texto(texto: str) -> str:
    """Gera hash do texto para cache."""
    return hashlib.md5(texto.encode()).hexdigest()


async def buscar_classificacao_cache(texto: str) -> Optional["ResultadoClassificacaoLLM"]:
    """
    Busca classificação no cache.

    Args:
        texto: Texto da mensagem

    Returns:
        ResultadoClassificacaoLLM se encontrado, None caso contrário
    """
    try:
        chave = f"{CACHE_PREFIX}{_hash_texto(texto)}"

        dados = await cache_get(chave)
        if dados:
            dados = json.loads(dados)
            return ResultadoClassificacaoLLM(
                eh_oferta=dados["eh_oferta"],
                confianca=dados["confianca"],
                motivo=dados["motivo"],
                tokens_usados=0,  # Do cache
                do_cache=True,
            )
    except Exception as e:
        logger.warning(f"Erro ao buscar cache: {e}")

    return None


async def salvar_classificacao_cache(texto: str, resultado: "ResultadoClassificacaoLLM") -> None:
    """Salva classificação no cache."""
    try:
        chave = f"{CACHE_PREFIX}{_hash_texto(texto)}"

        dados = json.dumps(
            {
                "eh_oferta": resultado.eh_oferta,
                "confianca": resultado.confianca,
                "motivo": resultado.motivo,
            }
        )

        await cache_set(chave, dados, CACHE_TTL)
    except Exception as e:
        logger.warning(f"Erro ao salvar cache: {e}")


# =============================================================================
# S04.2 - Cliente LLM
# =============================================================================


@dataclass
class ResultadoClassificacaoLLM:
    """Resultado da classificação LLM."""

    eh_oferta: bool
    confianca: float
    motivo: str
    tokens_usados: int = 0
    erro: Optional[str] = None
    do_cache: bool = False


def _parsear_resposta_llm(texto: str) -> ResultadoClassificacaoLLM:
    """
    Parseia resposta do LLM para estrutura.

    Tenta extrair JSON mesmo se vier com texto adicional.
    """
    texto = texto.strip()

    # Se começa com {, tentar parsear direto
    if texto.startswith("{"):
        dados = json.loads(texto)
    else:
        # Tentar extrair JSON do meio do texto
        match = re.search(r"\{[^{}]+\}", texto)
        if match:
            dados = json.loads(match.group())
        else:
            raise json.JSONDecodeError("JSON não encontrado", texto, 0)

    return ResultadoClassificacaoLLM(
        eh_oferta=dados.get("eh_oferta", False),
        confianca=float(dados.get("confianca", 0.0)),
        motivo=dados.get("motivo", ""),
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
async def _chamar_llm(prompt: str) -> tuple:
    """Chama o LLM com retry (async)."""
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    resposta_texto = response.content[0].text.strip()
    tokens_usados = response.usage.input_tokens + response.usage.output_tokens

    return resposta_texto, tokens_usados


async def classificar_com_llm(
    texto: str, nome_grupo: str = "", nome_contato: str = "", usar_cache: bool = True
) -> ResultadoClassificacaoLLM:
    """
    Classifica mensagem usando LLM.

    Args:
        texto: Texto da mensagem
        nome_grupo: Nome do grupo (contexto)
        nome_contato: Nome de quem enviou (contexto)
        usar_cache: Se deve usar cache

    Returns:
        ResultadoClassificacaoLLM
    """
    # Verificar cache primeiro
    if usar_cache:
        cached = await buscar_classificacao_cache(texto)
        if cached:
            logger.debug(f"Classificação do cache: {cached.eh_oferta}")
            return cached

    prompt = PROMPT_CLASSIFICACAO.format(
        texto=texto,
        nome_grupo=nome_grupo or "Desconhecido",
        nome_contato=nome_contato or "Desconhecido",
    )

    try:
        resposta_texto, tokens_usados = await _chamar_llm(prompt)

        # Tentar parsear JSON
        resultado = _parsear_resposta_llm(resposta_texto)
        resultado.tokens_usados = tokens_usados

        # Salvar no cache
        if usar_cache:
            await salvar_classificacao_cache(texto, resultado)

        return resultado

    except json.JSONDecodeError as e:
        logger.warning(f"Erro ao parsear JSON do LLM: {e}")
        return ResultadoClassificacaoLLM(
            eh_oferta=False, confianca=0.0, motivo="erro_parse", erro=str(e)
        )
    except anthropic.APIError as e:
        logger.error(f"Erro API Anthropic: {e}")
        return ResultadoClassificacaoLLM(
            eh_oferta=False, confianca=0.0, motivo="erro_api", erro=str(e)
        )
    except Exception as e:
        logger.error(f"Erro inesperado na classificação: {e}")
        return ResultadoClassificacaoLLM(
            eh_oferta=False, confianca=0.0, motivo="erro_desconhecido", erro=str(e)
        )
