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
from app.services.circuit_breaker import circuit_supabase

logger = logging.getLogger(__name__)

# =============================================================================
# GUARDRAIL: Proteção contra conexão errada DEV <-> PROD
# =============================================================================
# IDs dos projetos Supabase (extraídos da URL)
SUPABASE_PROJECT_PROD = "jyqgbzhqavgpxqacduoi"
SUPABASE_PROJECT_DEV = "ofpnronthwcsybfxnxgj"


def _validar_ambiente_supabase() -> None:
    """
    Valida consistência entre APP_ENV e projeto Supabase.

    Regras:
    - APP_ENV=production DEVE usar projeto PROD
    - APP_ENV=dev DEVE usar projeto DEV
    - Violação em PROD: ERRO FATAL (bloqueia inicialização)
    - Violação em DEV: WARNING severo (permite continuar com risco)

    Raises:
        RuntimeError: Se APP_ENV=production mas conectado a DEV
    """
    if not settings.SUPABASE_URL:
        return  # Será tratado depois

    # Extrair project_id da URL (formato: https://<project_id>.supabase.co)
    try:
        project_id = settings.SUPABASE_URL.split("//")[1].split(".")[0]
    except (IndexError, AttributeError):
        logger.warning("Não foi possível extrair project_id de SUPABASE_URL")
        return

    is_prod_env = settings.is_production  # APP_ENV == "production"
    is_prod_db = project_id == SUPABASE_PROJECT_PROD
    is_dev_db = project_id == SUPABASE_PROJECT_DEV

    # CASO CRÍTICO: Produção apontando para DEV
    if is_prod_env and is_dev_db:
        raise RuntimeError(
            f"🚨 ERRO FATAL: APP_ENV=production mas SUPABASE_URL aponta para DEV!\n"
            f"   Project ID: {project_id}\n"
            f"   Esperado: {SUPABASE_PROJECT_PROD}\n"
            f"   Corrija SUPABASE_URL antes de iniciar em produção."
        )

    # CASO DE RISCO: DEV apontando para PROD
    if not is_prod_env and is_prod_db:
        logger.critical(
            f"⚠️  ATENÇÃO: APP_ENV={settings.APP_ENV} mas SUPABASE_URL aponta para PROD!\n"
            f"   Project ID: {project_id}\n"
            f"   Isso pode causar modificações acidentais em produção!\n"
            f"   Considere usar SUPABASE_URL do ambiente DEV: {SUPABASE_PROJECT_DEV}"
        )
        # Não bloqueia, mas loga severamente para alertar

    # Caso normal: ambiente e banco consistentes
    env_label = "PROD" if is_prod_env else "DEV"
    db_label = "PROD" if is_prod_db else "DEV" if is_dev_db else "UNKNOWN"
    logger.info(f"✅ Supabase: APP_ENV={env_label}, DB={db_label} (project={project_id})")


@lru_cache()
def get_supabase_client() -> Client:
    """
    Retorna cliente Supabase cacheado.
    Usa service key para acesso completo.

    Inclui validação de ambiente para evitar conexão errada DEV <-> PROD.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY sao obrigatorios")

    # Validar consistência ambiente <-> banco
    _validar_ambiente_supabase()

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


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
    inicio: datetime, fim: datetime, direcao: Optional[str] = None, cliente_id: Optional[str] = None
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
