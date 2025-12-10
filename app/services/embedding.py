"""
Servico de geracao de embeddings para RAG.

Usa Voyage AI voyage-3.5-lite (recomendado pela Anthropic).
- Mesmo preco que OpenAI ($0.02/1M tokens)
- Qualidade 6% superior
- Contexto 32K tokens
- Dimensoes 1024 (menor = menos storage)
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Dimensao do embedding (voyage-3.5-lite = 1024)
EMBEDDING_DIMENSION = 1024

# Cliente Voyage (lazy load)
_voyage_client = None


def _get_voyage_client():
    """
    Retorna cliente Voyage (singleton com lazy loading).

    Importa voyageai apenas quando necessário para evitar
    erro se a lib não estiver instalada.
    """
    global _voyage_client

    if _voyage_client is None:
        if not settings.VOYAGE_API_KEY:
            logger.warning("VOYAGE_API_KEY nao configurada - embeddings desabilitados")
            return None

        try:
            import voyageai
            _voyage_client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
            logger.info("Cliente Voyage AI inicializado com sucesso")
        except ImportError:
            logger.error("Biblioteca voyageai nao instalada. Execute: uv add voyageai")
            return None
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente Voyage: {e}")
            return None

    return _voyage_client


async def gerar_embedding(
    texto: str,
    input_type: str = "document"
) -> Optional[list[float]]:
    """
    Gera embedding para um texto usando Voyage AI.

    Args:
        texto: Texto para gerar embedding
        input_type: "document" para memorias, "query" para buscas

    Returns:
        Lista de floats representando o embedding, ou None se erro
    """
    if not texto or not texto.strip():
        logger.debug("Texto vazio, retornando None")
        return None

    try:
        client = _get_voyage_client()
        if not client:
            return None

        # Limpar texto (Voyage suporta 32K, mas limitamos para economia)
        texto_limpo = texto.strip()[:16000]

        result = client.embed(
            [texto_limpo],
            model=settings.VOYAGE_MODEL,
            input_type=input_type
        )

        embedding = result.embeddings[0]
        logger.debug(f"Embedding gerado: {len(embedding)} dimensoes")

        return embedding

    except Exception as e:
        logger.error(f"Erro ao gerar embedding Voyage: {e}")
        return None


async def gerar_embeddings_batch(
    textos: list[str],
    input_type: str = "document"
) -> list[Optional[list[float]]]:
    """
    Gera embeddings para multiplos textos em batch.

    Mais eficiente que chamar um por um.

    Args:
        textos: Lista de textos
        input_type: "document" ou "query"

    Returns:
        Lista de embeddings (None para textos vazios/erros)
    """
    if not textos:
        return []

    try:
        client = _get_voyage_client()
        if not client:
            return [None] * len(textos)

        # Filtrar textos vazios e manter indices
        textos_validos = []
        indices_validos = []

        for i, t in enumerate(textos):
            if t and t.strip():
                textos_validos.append(t.strip()[:16000])
                indices_validos.append(i)

        if not textos_validos:
            return [None] * len(textos)

        result = client.embed(
            textos_validos,
            model=settings.VOYAGE_MODEL,
            input_type=input_type
        )

        # Reconstruir lista com None para indices que nao tinham texto
        embeddings = [None] * len(textos)
        for i, emb in zip(indices_validos, result.embeddings):
            embeddings[i] = emb

        logger.info(f"Batch de {len(textos_validos)} embeddings gerado")
        return embeddings

    except Exception as e:
        logger.error(f"Erro ao gerar embeddings batch Voyage: {e}")
        return [None] * len(textos)


def calcular_similaridade(
    embedding1: list[float],
    embedding2: list[float]
) -> float:
    """
    Calcula similaridade de cosseno entre dois embeddings.

    Voyage AI retorna embeddings normalizados, então
    dot product = cosine similarity.

    Args:
        embedding1: Primeiro embedding
        embedding2: Segundo embedding

    Returns:
        Score de similaridade entre 0 e 1
    """
    if not embedding1 or not embedding2:
        return 0.0

    if len(embedding1) != len(embedding2):
        logger.warning(
            f"Embeddings com dimensoes diferentes: {len(embedding1)} vs {len(embedding2)}"
        )
        return 0.0

    # Dot product (embeddings Voyage ja sao normalizados)
    dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

    return max(0.0, min(1.0, dot_product))
