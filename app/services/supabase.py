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
    """Retorna instancia do cliente Supabase."""
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


# Funcoes auxiliares para operacoes comuns
async def get_medico_by_telefone(telefone: str) -> dict | None:
    """Busca medico pelo telefone."""
    def _query():
        return supabase.table("clientes").select("*").eq("telefone", telefone).execute()

    response = await _executar_com_circuit_breaker(_query)
    return response.data[0] if response.data else None


async def get_medico_by_id(medico_id: str) -> dict | None:
    """Busca medico pelo ID."""
    def _query():
        return supabase.table("clientes").select("*").eq("id", medico_id).execute()

    response = await _executar_com_circuit_breaker(_query)
    return response.data[0] if response.data else None


async def get_or_create_medico(telefone: str, primeiro_nome: Optional[str] = None) -> dict:
    """Busca ou cria medico."""
    medico = await get_medico_by_telefone(telefone)
    if not medico:
        data = {
            "telefone": telefone,
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


async def get_vagas_disponiveis(especialidade_id: str = None, limit: int = 10) -> list:
    """Busca vagas abertas para uma especialidade."""
    def _query():
        query = (
            supabase.table("vagas")
            .select("*, hospitais(*), periodos(*), setores(*), especialidades(*)")
            .eq("status", "aberta")
            .gte("data", datetime.now(timezone.utc).date().isoformat())
            .order("data")
            .limit(limit)
        )

        if especialidade_id:
            query = query.eq("especialidade_id", especialidade_id)

        return query.execute()

    response = await _executar_com_circuit_breaker(_query)
    return response.data


async def get_conversa_ativa(cliente_id: str) -> dict | None:
    """Busca conversa ativa do cliente."""
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
            })
            .execute()
        )

    response = await _executar_com_circuit_breaker(_insert)
    return response.data[0] if response.data else None


async def get_historico(conversa_id: str, limit: int = 20) -> list:
    """Busca historico de mensagens da conversa."""
    def _query():
        return (
            supabase.table("interacoes")
            .select("*")
            .eq("conversation_id", conversa_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    response = await _executar_com_circuit_breaker(_query)
    return list(reversed(response.data)) if response.data else []


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
