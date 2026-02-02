"""
Cache de respostas LLM.

Sprint 44 T06.4: Cache para reduzir chamadas redundantes ao LLM.
"""
import hashlib
import json
import logging
from typing import Optional

from app.services.redis import redis_client

logger = logging.getLogger(__name__)

# Configurações do cache
CACHE_TTL_SEGUNDOS = 3600  # 1 hora
CACHE_PREFIX = "llm:resp"

# Tipos de mensagens que NÃO devem ser cacheadas
# (contexto muito dinâmico ou respostas que precisam ser únicas)
TIPOS_NAO_CACHEAVEIS = {
    "negociacao",
    "reclamacao",
    "urgente",
    "handoff",
}


def _normalizar_mensagem(mensagem: str) -> str:
    """
    Normaliza mensagem para comparação.

    Remove variações que não afetam o significado:
    - Espaços extras
    - Capitalização
    - Pontuação final

    Args:
        mensagem: Texto original

    Returns:
        Texto normalizado
    """
    texto = mensagem.lower().strip()
    # Remove pontuação final que não muda significado
    while texto and texto[-1] in ".!?":
        texto = texto[:-1]
    # Normaliza espaços múltiplos
    texto = " ".join(texto.split())
    return texto


def _gerar_contexto_hash(contexto: dict) -> str:
    """
    Gera hash das partes relevantes do contexto.

    Inclui apenas dados que afetam a resposta:
    - ID do médico
    - Stage da jornada
    - Controlled_by (ai/human)

    Args:
        contexto: Dict de contexto completo

    Returns:
        Hash de 16 caracteres
    """
    partes_relevantes = {
        "medico_id": contexto.get("medico", {}).get("id") if isinstance(contexto.get("medico"), dict) else None,
        "stage": contexto.get("medico", {}).get("stage_jornada") if isinstance(contexto.get("medico"), dict) else None,
        "controlled_by": contexto.get("controlled_by"),
        "primeira_msg": contexto.get("primeira_msg"),
    }

    serializado = json.dumps(partes_relevantes, sort_keys=True)
    return hashlib.sha256(serializado.encode()).hexdigest()[:16]


def _gerar_cache_key(mensagem: str, contexto_hash: str) -> str:
    """
    Gera chave única para cache.

    Args:
        mensagem: Mensagem normalizada
        contexto_hash: Hash do contexto

    Returns:
        Chave Redis
    """
    msg_normalizada = _normalizar_mensagem(mensagem)
    combined = f"{msg_normalizada}:{contexto_hash}"
    msg_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]
    return f"{CACHE_PREFIX}:{msg_hash}"


def _deve_cachear(mensagem: str, contexto: dict) -> bool:
    """
    Verifica se a mensagem/contexto deve ser cacheada.

    Não cacheia:
    - Mensagens muito curtas (< 3 palavras)
    - Contextos de negociação/reclamação
    - Conversas em modo humano

    Args:
        mensagem: Texto da mensagem
        contexto: Dict de contexto

    Returns:
        True se deve cachear
    """
    # Mensagens muito curtas são muito específicas
    if len(mensagem.split()) < 3:
        return False

    # Conversas controladas por humano não devem cachear
    if contexto.get("controlled_by") == "human":
        return False

    # Verificar se tem indicadores de tipos não cacheáveis
    msg_lower = mensagem.lower()
    indicadores_nao_cacheaveis = [
        "preco", "valor", "pagar", "desconto",  # Negociação
        "reclamacao", "insatisfeito", "problema",  # Reclamação
        "urgente", "emergencia", "agora",  # Urgência
    ]

    for indicador in indicadores_nao_cacheaveis:
        if indicador in msg_lower:
            return False

    return True


async def get_cached_response(
    mensagem: str,
    contexto: dict,
) -> Optional[str]:
    """
    Busca resposta em cache para mensagem similar.

    Args:
        mensagem: Texto da mensagem
        contexto: Dict de contexto

    Returns:
        Resposta cacheada ou None se não encontrada
    """
    if not _deve_cachear(mensagem, contexto):
        return None

    try:
        contexto_hash = _gerar_contexto_hash(contexto)
        cache_key = _gerar_cache_key(mensagem, contexto_hash)

        cached = await redis_client.get(cache_key)

        if cached:
            logger.info(
                "[LLM Cache] Cache hit",
                extra={
                    "cache_key": cache_key,
                    "mensagem_preview": mensagem[:50],
                }
            )
            return cached.decode() if isinstance(cached, bytes) else cached

        return None

    except Exception as e:
        logger.warning(f"[LLM Cache] Erro ao buscar cache: {e}")
        return None


async def cache_response(
    mensagem: str,
    contexto: dict,
    resposta: str,
    ttl: int = None,
) -> bool:
    """
    Armazena resposta no cache.

    Args:
        mensagem: Texto da mensagem original
        contexto: Dict de contexto
        resposta: Resposta gerada pelo LLM
        ttl: TTL customizado em segundos (opcional)

    Returns:
        True se armazenou com sucesso
    """
    if not _deve_cachear(mensagem, contexto):
        return False

    # Não cachear respostas muito curtas (provavelmente erros ou fallbacks)
    if len(resposta) < 20:
        return False

    try:
        contexto_hash = _gerar_contexto_hash(contexto)
        cache_key = _gerar_cache_key(mensagem, contexto_hash)

        await redis_client.set(
            cache_key,
            resposta,
            ex=ttl or CACHE_TTL_SEGUNDOS
        )

        logger.debug(
            "[LLM Cache] Resposta cacheada",
            extra={
                "cache_key": cache_key,
                "mensagem_preview": mensagem[:50],
                "resposta_len": len(resposta),
            }
        )
        return True

    except Exception as e:
        logger.warning(f"[LLM Cache] Erro ao cachear resposta: {e}")
        return False


async def invalidar_cache_medico(medico_id: str) -> int:
    """
    Invalida cache de respostas para um médico específico.

    Útil quando dados do médico mudam significativamente.

    Args:
        medico_id: ID do médico

    Returns:
        Número de chaves deletadas
    """
    try:
        # Nota: Esta é uma operação simplificada
        # Em produção, considerar usar SCAN para evitar KEYS
        pattern = f"{CACHE_PREFIX}:*"
        logger.info(f"[LLM Cache] Invalidação solicitada para médico {medico_id}")

        # Por segurança, não fazemos invalidação em massa
        # A expiração natural do TTL resolve
        return 0

    except Exception as e:
        logger.warning(f"[LLM Cache] Erro ao invalidar cache: {e}")
        return 0


async def obter_metricas_cache() -> dict:
    """
    Obtém métricas do cache de LLM.

    Returns:
        {
            'hits': int,
            'misses': int,
            'hit_rate': float,
        }

    Nota: Implementação básica. Em produção, usar Redis INFO ou métricas customizadas.
    """
    # Placeholder para métricas futuras
    # Pode ser implementado com contadores Redis dedicados
    return {
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0,
        "cache_enabled": True,
    }
