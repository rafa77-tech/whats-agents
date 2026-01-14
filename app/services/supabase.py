"""
Cliente Supabase para operacoes de banco de dados.

Sprint 30: Consolidado - funcoes de entidade movidas para services especificos.
Manter apenas: cliente, circuit breaker e helpers genericos.
"""
import asyncio
from supabase import create_client, Client
from functools import lru_cache
from datetime import datetime
from typing import Optional
import logging

from app.core.config import settings
from app.services.circuit_breaker import circuit_supabase, CircuitOpenError

logger = logging.getLogger(__name__)


@lru_cache()
def get_supabase_client() -> Client:
    """
    Retorna cliente Supabase cacheado.
    Usa service key para acesso completo.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY sao obrigatorios")

    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
    )


# Instancia global (use via dependency injection quando possivel)
supabase = get_supabase_client()


async def _executar_com_circuit_breaker(func):
    """
    Executa funcao sincrona do Supabase com circuit breaker.

    Args:
        func: Funcao sincrona a executar

    Returns:
        Resultado da funcao

    Raises:
        CircuitOpenError: Se Supabase esta indisponivel
    """
    async def _async_wrapper():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)

    return await circuit_supabase.executar(_async_wrapper)


# =============================================================================
# HELPERS GENERICOS (OK manter aqui - nao sao especificos de entidade)
# =============================================================================

async def contar_interacoes_periodo(
    inicio: datetime,
    fim: datetime,
    direcao: Optional[str] = None,
    cliente_id: Optional[str] = None
) -> int:
    """
    Conta interacoes em um periodo.

    Args:
        inicio: Data/hora inicial
        fim: Data/hora final
        direcao: 'entrada' ou 'saida' (opcional)
        cliente_id: Filtrar por cliente/medico (opcional)

    Returns:
        Numero de interacoes

    Example:
        >>> count = await contar_interacoes_periodo(
        ...     inicio=datetime(2024, 1, 1),
        ...     fim=datetime(2024, 1, 31),
        ...     direcao="saida"
        ... )
    """
    def _query():
        query = supabase.table("interacoes").select("id", count="exact")
        query = query.gte("created_at", inicio.isoformat())
        query = query.lte("created_at", fim.isoformat())

        if direcao:
            query = query.eq("direcao", direcao)
        if cliente_id:
            query = query.eq("cliente_id", cliente_id)

        return query.execute()

    response = await _executar_com_circuit_breaker(_query)
    return response.count or 0


# =============================================================================
# FUNCOES DE ENTIDADE REMOVIDAS - Sprint 30 Consolidacao
# =============================================================================
# As seguintes funcoes foram movidas para seus services especificos:
#
# MEDICO:
#   - buscar_medico_por_telefone -> app/services/medico.py
#   - buscar_medico_por_id -> app/services/medico.py
#   - buscar_ou_criar_medico -> app/services/medico.py
#
# CONVERSA:
#   - criar_conversa -> app/services/conversa.py
#   - buscar_conversa_ativa -> app/services/conversa.py
#   - atualizar_controle_conversa -> app/services/conversa.py
#
# INTERACAO:
#   - salvar_interacao -> app/services/interacao.py
#   - listar_historico -> app/services/interacao.py
#
# OPTOUT:
#   - marcar_optout -> app/services/optout.py
#
# HANDOFF:
#   - listar_handoffs_pendentes -> app/services/handoff/repository.py
#
# VAGAS:
#   - buscar_vagas_disponiveis -> app/services/vagas/repository.py
# =============================================================================
