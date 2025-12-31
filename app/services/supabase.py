"""
Cliente Supabase para operacoes de banco de dados.
"""
import asyncio
from supabase import create_client, Client
from functools import lru_cache
from datetime import datetime, timezone
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


def get_supabase() -> Client:
    """
    DEPRECATED: Use `from app.services.supabase import supabase` diretamente.

    Esta funcao sera removida em versao futura.
    """
    import warnings
    warnings.warn(
        "get_supabase() is deprecated. Use 'from app.services.supabase import supabase' directly.",
        DeprecationWarning,
        stacklevel=2
    )
    return supabase


async def _executar_com_circuit_breaker(func):
    """
    Executa função síncrona do Supabase com circuit breaker.

    Args:
        func: Função síncrona a executar

    Returns:
        Resultado da função

    Raises:
        CircuitOpenError: Se Supabase está indisponível
    """
    async def _async_wrapper():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)

    return await circuit_supabase.executar(_async_wrapper)


# =============================================================================
# FUNCOES DEPRECATED (manter para retrocompatibilidade)
# =============================================================================

async def get_medico_by_telefone(telefone: str) -> dict | None:
    """DEPRECATED: Use buscar_medico_por_telefone()."""
    import warnings
    warnings.warn(
        "get_medico_by_telefone is deprecated. Use buscar_medico_por_telefone instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return await buscar_medico_por_telefone(telefone)


async def get_medico_by_id(medico_id: str) -> dict | None:
    """DEPRECATED: Use buscar_medico_por_id()."""
    import warnings
    warnings.warn(
        "get_medico_by_id is deprecated. Use buscar_medico_por_id instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return await buscar_medico_por_id(medico_id)


async def get_or_create_medico(telefone: str, primeiro_nome: Optional[str] = None) -> dict:
    """DEPRECATED: Use buscar_ou_criar_medico()."""
    import warnings
    warnings.warn(
        "get_or_create_medico is deprecated. Use buscar_ou_criar_medico instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return await buscar_ou_criar_medico(telefone, primeiro_nome)


async def get_vagas_disponiveis(especialidade_id: str = None, limit: int = 10) -> list:
    """DEPRECATED: Use buscar_vagas_disponiveis()."""
    import warnings
    warnings.warn(
        "get_vagas_disponiveis is deprecated. Use buscar_vagas_disponiveis instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return await buscar_vagas_disponiveis(especialidade_id=especialidade_id, limite=limit)


async def get_conversa_ativa(cliente_id: str) -> dict | None:
    """DEPRECATED: Use buscar_conversa_ativa()."""
    import warnings
    warnings.warn(
        "get_conversa_ativa is deprecated. Use buscar_conversa_ativa instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return await buscar_conversa_ativa(cliente_id)


async def criar_conversa(cliente_id: str, origem: str = "prospeccao") -> dict:
    """Cria nova conversa para um medico."""
    def _insert():
        return (
            supabase.table("conversations")
            .insert({
                "cliente_id": cliente_id,
                "status": "active",
                "controlled_by": "ai",
                "instance_id": settings.EVOLUTION_INSTANCE,
            })
            .execute()
        )

    response = await _executar_com_circuit_breaker(_insert)
    return response.data[0] if response.data else None


async def salvar_interacao(
    conversa_id: str,
    cliente_id: str,
    direcao: str,
    conteudo: str,
    tipo: str = "texto"
) -> dict:
    """Salva uma interacao (mensagem) na conversa."""
    origem = "medico" if direcao == "entrada" else "julia"
    autor_tipo = "medico" if direcao == "entrada" else "ai"

    def _insert():
        return (
            supabase.table("interacoes")
            .insert({
                "conversation_id": conversa_id,
                "cliente_id": cliente_id,
                "origem": origem,
                "tipo": tipo,
                "conteudo": conteudo,
                "canal": "whatsapp",
                "autor_tipo": autor_tipo,
                "direcao": direcao,
            })
            .execute()
        )

    response = await _executar_com_circuit_breaker(_insert)
    return response.data[0] if response.data else None


async def get_historico(conversa_id: str, limit: int = 20) -> list:
    """DEPRECATED: Use listar_historico()."""
    import warnings
    warnings.warn(
        "get_historico is deprecated. Use listar_historico instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return await listar_historico(conversa_id, limite=limit)


async def marcar_optout(cliente_id: str) -> dict | None:
    """Marca médico como opted-out."""
    def _update():
        return (
            supabase.table("clientes")
            .update({
                "status": "opted_out",
                "optout_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", cliente_id)
            .execute()
        )

    response = await _executar_com_circuit_breaker(_update)
    return response.data[0] if response.data else None


# =============================================================================
# HELPERS CENTRALIZADOS (Sprint 10 - S10.E1.2)
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


async def buscar_medico_por_telefone(telefone: str) -> Optional[dict]:
    """
    Busca medico pelo telefone.

    Args:
        telefone: Numero do telefone (com ou sem formatacao)

    Returns:
        Dict com dados do medico ou None

    Example:
        >>> medico = await buscar_medico_por_telefone("11999887766")
    """
    telefone_limpo = "".join(filter(str.isdigit, telefone))

    def _query():
        return supabase.table("clientes").select("*").eq("telefone", telefone_limpo).execute()

    response = await _executar_com_circuit_breaker(_query)
    return response.data[0] if response.data else None


async def buscar_conversa_ativa(cliente_id: str) -> Optional[dict]:
    """
    Busca conversa ativa de um cliente/medico.

    Args:
        cliente_id: ID do cliente

    Returns:
        Dict com dados da conversa ou None

    Example:
        >>> conversa = await buscar_conversa_ativa("uuid-do-cliente")
    """
    def _query():
        return (
            supabase.table("conversations")
            .select("*")
            .eq("cliente_id", cliente_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

    response = await _executar_com_circuit_breaker(_query)
    return response.data[0] if response.data else None


async def listar_handoffs_pendentes() -> list[dict]:
    """
    Lista todos os handoffs pendentes de resolucao.

    Returns:
        Lista de handoffs com dados do cliente

    Example:
        >>> pendentes = await listar_handoffs_pendentes()
        >>> print(f"{len(pendentes)} handoffs aguardando")
    """
    def _query():
        return (
            supabase.table("handoffs")
            .select("*, conversations(*, clientes(*))")
            .eq("status", "pendente")
            .order("created_at", desc=True)
            .execute()
        )

    response = await _executar_com_circuit_breaker(_query)
    return response.data or []


async def buscar_vagas_disponiveis(
    especialidade_id: Optional[str] = None,
    regiao: Optional[str] = None,
    limite: int = 10
) -> list[dict]:
    """
    Busca vagas disponiveis com filtros.

    Args:
        especialidade_id: Filtrar por especialidade (opcional)
        regiao: Filtrar por regiao (opcional)
        limite: Maximo de resultados (default: 10)

    Returns:
        Lista de vagas com dados do hospital e especialidade

    Example:
        >>> vagas = await buscar_vagas_disponiveis(limite=5)
    """
    def _query():
        query = (
            supabase.table("vagas")
            .select("*, hospitais(nome, endereco), especialidades(nome)")
            .eq("status", "aberta")
            .gte("data", datetime.now(timezone.utc).date().isoformat())
        )

        if especialidade_id:
            query = query.eq("especialidade_id", especialidade_id)
        if regiao:
            query = query.eq("regiao", regiao)

        return query.order("data").limit(limite).execute()

    response = await _executar_com_circuit_breaker(_query)
    return response.data or []


async def atualizar_controle_conversa(
    conversa_id: str,
    controlled_by: str,
    motivo: Optional[str] = None
) -> bool:
    """
    Atualiza quem controla a conversa (ai ou human).

    Args:
        conversa_id: ID da conversa
        controlled_by: 'ai' ou 'human'
        motivo: Motivo da mudanca (opcional)

    Returns:
        True se atualizou com sucesso

    Example:
        >>> await atualizar_controle_conversa("uuid", "human", "pedido do medico")
    """
    def _update():
        data = {
            "controlled_by": controlled_by,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if motivo:
            data["escalation_reason"] = motivo

        return (
            supabase.table("conversations")
            .update(data)
            .eq("id", conversa_id)
            .execute()
        )

    response = await _executar_com_circuit_breaker(_update)
    return len(response.data) > 0 if response.data else False


async def buscar_medico_por_id(medico_id: str) -> Optional[dict]:
    """
    Busca medico pelo ID.

    Args:
        medico_id: UUID do medico

    Returns:
        Dict com dados do medico ou None
    """
    def _query():
        return supabase.table("clientes").select("*").eq("id", medico_id).execute()

    response = await _executar_com_circuit_breaker(_query)
    return response.data[0] if response.data else None


async def buscar_ou_criar_medico(
    telefone: str,
    primeiro_nome: Optional[str] = None
) -> dict:
    """
    Busca medico ou cria se nao existir.

    Args:
        telefone: Numero do telefone
        primeiro_nome: Nome do medico (opcional)

    Returns:
        Dict com dados do medico
    """
    medico = await buscar_medico_por_telefone(telefone)
    if not medico:
        telefone_limpo = "".join(filter(str.isdigit, telefone))
        data = {
            "telefone": telefone_limpo,
            "primeiro_nome": primeiro_nome,
            "stage_jornada": "novo",
            "status": "novo"
        }

        def _insert():
            return supabase.table("clientes").insert(data).execute()

        response = await _executar_com_circuit_breaker(_insert)
        logger.info(f"Novo medico criado: {telefone[:8]}...")
        return response.data[0]
    return medico


async def listar_historico(conversa_id: str, limite: int = 20) -> list:
    """
    Lista historico de mensagens de uma conversa.

    Args:
        conversa_id: ID da conversa
        limite: Maximo de mensagens (default: 20)

    Returns:
        Lista de mensagens em ordem cronologica
    """
    def _query():
        return (
            supabase.table("interacoes")
            .select("*")
            .eq("conversation_id", conversa_id)
            .order("created_at", desc=True)
            .limit(limite)
            .execute()
        )

    response = await _executar_com_circuit_breaker(_query)
    return list(reversed(response.data)) if response.data else []
