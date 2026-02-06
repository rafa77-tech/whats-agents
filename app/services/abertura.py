"""
Servico de selecao de aberturas.

Seleciona variacoes de mensagens de abertura evitando repeticao.
"""
import json
import logging
import random
from datetime import datetime
from typing import Optional

from app.core.timezone import agora_brasilia, agora_utc
from app.fragmentos.aberturas import (
    SAUDACOES,
    SAUDACOES_SEM_NOME,
    APRESENTACOES,
    CONTEXTOS,
    CONTEXTOS_SOFT,
    GANCHOS,
    GANCHOS_SOFT,
    montar_abertura_completa
)
from app.services.redis import cache_get, cache_set
from app.services.supabase import supabase
from app.core.config import DatabaseConfig

logger = logging.getLogger(__name__)


async def obter_abertura(
    cliente_id: str,
    nome: str,
    hora_atual: datetime = None,
    soft: bool = False
) -> list[str]:
    """
    Obtem abertura personalizada para medico.

    Evita repetir a mesma abertura para o mesmo medico.
    Considera horario do dia para saudacao.

    Args:
        cliente_id: ID do medico
        nome: Nome do medico
        hora_atual: Hora atual (para saudacao contextual)
        soft: Se True, usa fragmentos soft (sem mencionar plantao)

    Returns:
        Lista de mensagens de abertura
    """
    hora_atual = hora_atual or agora_brasilia()

    # Buscar ultima abertura usada
    ultima_abertura = await _get_ultima_abertura(cliente_id)

    # Selecionar saudacao baseada no horario
    saudacao = _selecionar_saudacao(hora_atual, ultima_abertura)

    # Selecionar demais componentes evitando repeticao
    apresentacao = _selecionar_sem_repetir(
        APRESENTACOES,
        ultima_abertura.get("apresentacao") if ultima_abertura else None
    )

    # Usar listas soft ou normais
    lista_contextos = CONTEXTOS_SOFT if soft else CONTEXTOS
    lista_ganchos = GANCHOS_SOFT if soft else GANCHOS

    contexto = _selecionar_sem_repetir(
        lista_contextos,
        ultima_abertura.get("contexto") if ultima_abertura else None
    )

    gancho = _selecionar_sem_repetir(
        lista_ganchos,
        ultima_abertura.get("gancho") if ultima_abertura else None
    )

    # Decidir se inclui contexto (70% das vezes)
    incluir_contexto = random.random() < 0.7

    # Montar abertura
    mensagens = montar_abertura_completa(
        nome=nome,
        saudacao_id=saudacao[0],
        apresentacao_id=apresentacao[0],
        contexto_id=contexto[0] if incluir_contexto else None,
        gancho_id=gancho[0],
        incluir_contexto=incluir_contexto,
        soft=soft
    )

    # Salvar para evitar repeticao
    await _salvar_abertura_usada(
        cliente_id,
        saudacao[0],
        apresentacao[0],
        contexto[0] if incluir_contexto else None,
        gancho[0]
    )

    logger.info(
        f"Abertura gerada para {cliente_id} (soft={soft}): "
        f"saudacao={saudacao[0]}, apresentacao={apresentacao[0]}, "
        f"contexto={contexto[0] if incluir_contexto else 'nenhum'}, gancho={gancho[0]}"
    )

    return mensagens


async def obter_abertura_texto(
    cliente_id: str,
    nome: str,
    hora_atual: datetime = None,
    soft: bool = False
) -> str:
    """
    Obtem abertura como texto unico.

    Args:
        cliente_id: ID do medico
        nome: Nome do medico
        hora_atual: Hora atual
        soft: Se True, usa fragmentos soft (sem mencionar plantao)

    Returns:
        String com abertura completa
    """
    mensagens = await obter_abertura(cliente_id, nome, hora_atual, soft=soft)
    return "\n\n".join(mensagens)


async def _get_ultima_abertura(cliente_id: str) -> Optional[dict]:
    """Busca ultima abertura usada para este medico."""
    cache_key = f"abertura:ultima:{cliente_id}"

    cached = await cache_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            pass

    # Buscar no banco
    try:
        response = (
            supabase.table("clientes")
            .select("ultima_abertura")
            .eq("id", cliente_id)
            .limit(1)
            .execute()
        )

        if response.data and response.data[0].get("ultima_abertura"):
            abertura = response.data[0]["ultima_abertura"]
            # Cachear
            await cache_set(cache_key, json.dumps(abertura), DatabaseConfig.CACHE_TTL_ABERTURA)
            return abertura

    except Exception as e:
        logger.warning(f"Erro ao buscar ultima abertura: {e}")

    return None


async def _salvar_abertura_usada(
    cliente_id: str,
    saudacao_id: str,
    apresentacao_id: str,
    contexto_id: Optional[str],
    gancho_id: str
):
    """Salva abertura usada para evitar repeticao."""
    abertura = {
        "saudacao": saudacao_id,
        "apresentacao": apresentacao_id,
        "contexto": contexto_id,
        "gancho": gancho_id,
        "timestamp": agora_utc().isoformat()
    }

    # Cache
    cache_key = f"abertura:ultima:{cliente_id}"
    await cache_set(cache_key, json.dumps(abertura), DatabaseConfig.CACHE_TTL_ABERTURA)

    # Banco (async, nao bloqueia)
    try:
        supabase.table("clientes").update({
            "ultima_abertura": abertura
        }).eq("id", cliente_id).execute()
    except Exception as e:
        logger.warning(f"Erro ao salvar abertura no banco: {e}")


def _selecionar_saudacao(
    hora: datetime,
    ultima: dict = None
) -> tuple:
    """
    Seleciona saudacao baseada no horario.

    6-12h: bom dia
    12-18h: boa tarde
    18-24h/0-6h: boa noite
    """
    hora_int = hora.hour

    # Filtrar por periodo
    if 6 <= hora_int < 12:
        periodo = "manha"
    elif 12 <= hora_int < 18:
        periodo = "tarde"
    else:
        periodo = "noite"

    # Buscar saudacoes do periodo ou genericas
    candidatas = [
        s for s in SAUDACOES
        if s[2] == periodo or s[2] is None
    ]

    # Evitar repetir
    if ultima and ultima.get("saudacao"):
        candidatas_sem_repetir = [
            s for s in candidatas
            if s[0] != ultima["saudacao"]
        ]
        if candidatas_sem_repetir:
            candidatas = candidatas_sem_repetir

    # Se sobrou algo, escolher aleatorio
    if candidatas:
        return random.choice(candidatas)

    # Fallback
    return random.choice(SAUDACOES)


def _selecionar_sem_repetir(
    opcoes: list[tuple],
    ultimo_id: str = None
) -> tuple:
    """Seleciona opcao evitando a ultima usada."""
    if ultimo_id:
        candidatas = [o for o in opcoes if o[0] != ultimo_id]
        if candidatas:
            return random.choice(candidatas)

    return random.choice(opcoes)


async def resetar_abertura_cliente(cliente_id: str) -> bool:
    """
    Reseta historico de abertura para um cliente.

    Util para testes ou quando quiser permitir repeticao.

    Args:
        cliente_id: ID do cliente

    Returns:
        True se resetou com sucesso
    """
    try:
        # Limpar cache
        cache_key = f"abertura:ultima:{cliente_id}"
        from app.services.redis import cache_delete
        await cache_delete(cache_key)

        # Limpar banco
        supabase.table("clientes").update({
            "ultima_abertura": None
        }).eq("id", cliente_id).execute()

        logger.info(f"Abertura resetada para cliente {cliente_id}")
        return True

    except Exception as e:
        logger.error(f"Erro ao resetar abertura: {e}")
        return False


def obter_estatisticas_aberturas() -> dict:
    """
    Retorna estatisticas dos fragmentos de abertura.

    Returns:
        Dicionario com estatisticas
    """
    from app.fragmentos.aberturas import contar_variacoes
    return contar_variacoes()
