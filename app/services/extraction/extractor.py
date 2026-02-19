"""
Servico de extracao de dados de conversas.

Sprint 53: Discovery Intelligence Pipeline.

Usa Claude Haiku para custo minimo (~$0.0001 por extracao).
"""

import json
import hashlib
import time
import logging
from typing import Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.redis import cache_get, cache_set
from .schemas import (
    ExtractionContext,
    ExtractionResult,
    Interesse,
    ProximoPasso,
    Objecao,
    TipoObjecao,
    SeveridadeObjecao,
)
from .prompts import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

CACHE_TTL = 86400  # 24 horas
CACHE_PREFIX = "extraction:"


async def extrair_dados_conversa(context: ExtractionContext) -> ExtractionResult:
    """
    Extrai dados estruturados de um turno de conversa.

    Args:
        context: Contexto completo da extracao

    Returns:
        ExtractionResult com dados extraidos
    """
    start_time = time.time()

    # 1. Verificar cache
    cache_key = _gerar_cache_key(context)
    cached = await _get_from_cache(cache_key)
    if cached:
        logger.debug(f"[Extraction] Cache hit para {cache_key[:20]}...")
        return cached

    # 2. Validar input
    if not context.mensagem_medico or len(context.mensagem_medico.strip()) < 2:
        return _resultado_padrao(context, "mensagem_muito_curta")

    # 3. Montar prompt
    prompt = EXTRACTION_PROMPT.format(
        mensagem_medico=context.mensagem_medico,
        resposta_julia=context.resposta_julia or "[sem resposta]",
        nome=context.nome_medico or "Medico",
        especialidade=context.especialidade_cadastrada or "Nao informada",
        regiao=context.regiao_cadastrada or "Nao informada",
        tipo_campanha=context.tipo_campanha or "geral",
    )

    # 4. Chamar LLM
    try:
        resposta, tokens_input, tokens_output = await _chamar_llm(prompt)
    except Exception as e:
        logger.error(f"[Extraction] Erro ao chamar LLM: {e}")
        return _resultado_padrao(context, f"erro_llm: {e}")

    # 5. Parsear JSON
    result = _parsear_resposta(resposta, context)

    # 6. Adicionar metricas
    result.tokens_input = tokens_input
    result.tokens_output = tokens_output
    result.latencia_ms = int((time.time() - start_time) * 1000)

    # 7. Salvar no cache
    await _save_to_cache(cache_key, result)

    logger.info(
        f"[Extraction] interesse={result.interesse.value}, "
        f"score={result.interesse_score:.2f}, "
        f"confianca={result.confianca:.2f}, "
        f"latencia={result.latencia_ms}ms"
    )

    return result


def _gerar_cache_key(context: ExtractionContext) -> str:
    """Gera chave de cache baseada no conteudo."""
    content = f"{context.mensagem_medico}|{context.resposta_julia}"
    hash_value = hashlib.md5(content.encode()).hexdigest()
    return f"{CACHE_PREFIX}{hash_value}"


async def _get_from_cache(key: str) -> Optional[ExtractionResult]:
    """Busca resultado do cache."""
    try:
        data = await cache_get(key)
        if data:
            parsed = json.loads(data)
            return ExtractionResult.from_dict(parsed)
    except Exception as e:
        logger.warning(f"[Extraction] Erro ao ler cache: {e}")
    return None


async def _save_to_cache(key: str, result: ExtractionResult) -> None:
    """Salva resultado no cache."""
    try:
        data = json.dumps(result.to_dict(), ensure_ascii=False)
        await cache_set(key, data, CACHE_TTL)
    except Exception as e:
        logger.warning(f"[Extraction] Erro ao salvar cache: {e}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
async def _chamar_llm(prompt: str) -> tuple[str, int, int]:
    """Chama o LLM para extracao com retry."""
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        temperature=0.1,  # Baixa para consistencia
        messages=[{"role": "user", "content": prompt}],
    )

    resposta_texto = response.content[0].text.strip()
    tokens_input = response.usage.input_tokens
    tokens_output = response.usage.output_tokens

    return resposta_texto, tokens_input, tokens_output


def _parsear_resposta(resposta: str, context: ExtractionContext) -> ExtractionResult:
    """Parseia resposta do LLM em ExtractionResult."""
    try:
        # Tentar extrair JSON da resposta
        json_str = resposta

        # Remove markdown code blocks
        if "```json" in resposta:
            json_str = resposta.split("```json")[1].split("```")[0]
        elif "```" in resposta:
            parts = resposta.split("```")
            if len(parts) >= 2:
                json_str = parts[1]

        json_str = json_str.strip()

        # Se nao comecar com {, tenta encontrar
        if not json_str.startswith("{"):
            import re

            match = re.search(r"\{[\s\S]*\}", json_str)
            if match:
                json_str = match.group()
            else:
                raise json.JSONDecodeError("JSON nao encontrado", json_str, 0)

        data = json.loads(json_str)

        # Parsear objecao
        objecao = _parsear_objecao(data.get("objecao"))

        # Converter para ExtractionResult
        return ExtractionResult(
            interesse=Interesse(data.get("interesse", "incerto")),
            interesse_score=float(data.get("interesse_score", 0.5)),
            especialidade_mencionada=data.get("especialidade_mencionada"),
            regiao_mencionada=data.get("regiao_mencionada"),
            disponibilidade_mencionada=data.get("disponibilidade_mencionada"),
            objecao=objecao,
            preferencias=data.get("preferencias", []),
            restricoes=data.get("restricoes", []),
            dados_corrigidos=data.get("dados_corrigidos", {}),
            proximo_passo=ProximoPasso(data.get("proximo_passo", "sem_acao")),
            confianca=float(data.get("confianca", 0.5)),
            raw_json=data,
        )
    except Exception as e:
        logger.warning(f"[Extraction] Erro ao parsear JSON: {e}, resposta: {resposta[:100]}")
        return _resultado_padrao(context, f"parse_error: {e}")


def _parsear_objecao(data: Optional[dict]) -> Optional[Objecao]:
    """Parseia objecao do JSON."""
    if not data or not data.get("tipo"):
        return None

    try:
        return Objecao(
            tipo=TipoObjecao(data["tipo"]),
            descricao=data.get("descricao", ""),
            severidade=SeveridadeObjecao(data.get("severidade", "media")),
        )
    except ValueError:
        return None


def _resultado_padrao(context: ExtractionContext, motivo: str) -> ExtractionResult:
    """Retorna resultado padrao para casos de erro."""
    return ExtractionResult(
        interesse=Interesse.INCERTO,
        interesse_score=0.5,
        proximo_passo=ProximoPasso.SEM_ACAO,
        confianca=0.0,
        raw_json={"_fallback": True, "_motivo": motivo},
    )
